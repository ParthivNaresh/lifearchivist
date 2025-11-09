from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from starlette.responses import JSONResponse

from ..shared.exceptions import ValidationError


def parse_datetime_range(
    start_time: Optional[str],
    end_time: Optional[str],
) -> Tuple[datetime, datetime]:
    """
    Parse and validate ISO 8601 datetime strings for time range queries.

    Args:
        start_time: Start time in ISO 8601 format
        end_time: End time in ISO 8601 format

    Returns:
        Tuple of (start_datetime, end_datetime)

    Raises:
        ValidationError: If times are missing or invalid format
    """
    if not start_time or not end_time:
        raise ValidationError("start_time and end_time required for usage/cost reports")

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        return start_dt, end_dt
    except ValueError as e:
        raise ValidationError(f"Invalid datetime format: {e}") from e


def fetch_provider_capabilities(
    llm_manager: Any,
    provider_id: str,
    response: Dict[str, Any],
) -> None:
    """
    Fetch and add provider capabilities to response.

    Args:
        llm_manager: LLM manager instance
        provider_id: Provider identifier
        response: Response dictionary to update
    """
    caps_result = llm_manager.get_metadata_capabilities(provider_id)
    if caps_result.is_success():
        response["capabilities"] = caps_result.unwrap()
    else:
        response["capabilities"] = []


async def fetch_provider_workspaces(
    llm_manager: Any,
    provider: Any,
    provider_id: str,
    response: Dict[str, Any],
) -> Optional[JSONResponse]:
    """
    Fetch and add provider workspaces to response.

    Args:
        llm_manager: LLM manager instance
        provider: Provider instance
        provider_id: Provider identifier
        response: Response dictionary to update

    Returns:
        JSONResponse if metadata not supported (501), None otherwise
    """
    if provider.metadata is None:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Provider {provider_id} does not support metadata",
                "error_type": "MetadataNotSupported",
            },
            status_code=501,
        )

    workspaces_result = await llm_manager.get_workspaces(provider_id)
    if workspaces_result.is_success():
        workspaces = workspaces_result.unwrap()
        response["workspaces"] = [
            {
                "id": ws.id,
                "name": ws.name,
                "is_default": ws.is_default,
                "metadata": ws.metadata,
            }
            for ws in workspaces
        ]
    elif workspaces_result.status_code == 501:
        return JSONResponse(
            content=workspaces_result.to_dict(),
            status_code=501,
        )
    else:
        response["workspaces"] = []
        response["workspaces_error"] = workspaces_result.error

    return None


async def fetch_provider_usage(
    llm_manager: Any,
    provider_id: str,
    start_dt: datetime,
    end_dt: datetime,
    response: Dict[str, Any],
) -> Optional[JSONResponse]:
    """
    Fetch and add provider usage data to response.

    Args:
        llm_manager: LLM manager instance
        provider_id: Provider identifier
        start_dt: Start datetime
        end_dt: End datetime
        response: Response dictionary to update

    Returns:
        JSONResponse if not supported (501), None otherwise
    """
    usage_result = await llm_manager.get_usage(provider_id, start_dt, end_dt)
    if usage_result.is_success():
        usage = usage_result.unwrap()
        response["usage"] = {
            "start_time": usage.start_time.isoformat(),
            "end_time": usage.end_time.isoformat(),
            "total_tokens": usage.total_tokens,
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cached_tokens": usage.cached_tokens,
            "requests_count": usage.requests_count,
            "metadata": usage.metadata,
        }
    elif usage_result.status_code == 501:
        return JSONResponse(
            content=usage_result.to_dict(),
            status_code=501,
        )
    else:
        response["usage"] = None
        response["usage_error"] = usage_result.error

    return None


async def fetch_provider_costs(
    llm_manager: Any,
    provider_id: str,
    start_dt: datetime,
    end_dt: datetime,
    response: Dict[str, Any],
) -> Optional[JSONResponse]:
    """
    Fetch and add provider cost data to response.

    Args:
        llm_manager: LLM manager instance
        provider_id: Provider identifier
        start_dt: Start datetime
        end_dt: End datetime
        response: Response dictionary to update

    Returns:
        JSONResponse if not supported (501), None otherwise
    """
    costs_result = await llm_manager.get_costs(provider_id, start_dt, end_dt)
    if costs_result.is_success():
        costs = costs_result.unwrap()
        response["costs"] = {
            "start_time": costs.start_time.isoformat(),
            "end_time": costs.end_time.isoformat(),
            "total_cost_usd": costs.total_cost_usd,
            "currency": costs.currency,
            "breakdown": costs.breakdown,
            "metadata": costs.metadata,
        }
    elif costs_result.status_code == 501:
        return JSONResponse(
            content=costs_result.to_dict(),
            status_code=501,
        )
    else:
        response["costs"] = None
        response["costs_error"] = costs_result.error

    return None


async def get_fallback_model_for_provider(
    llm_manager: Any,
    provider_id: str,
) -> Optional[str]:
    """
    Get first available model for a provider.

    Args:
        llm_manager: LLM manager instance
        provider_id: Provider identifier

    Returns:
        Model ID if available, None otherwise
    """
    try:
        models_result = await llm_manager.list_models(provider_id=provider_id)
        if models_result.is_success():
            models = models_result.unwrap()
            if models:
                model_id: str = models[0].id
                return model_id
    except Exception as e:
        import logging

        logging.warning(f"Failed to fetch models for provider {provider_id}: {e}")

    return None


async def determine_fallback_provider(
    llm_manager: Any,
    provider_id_to_delete: str,
) -> Tuple[str, str]:
    """
    Determine fallback provider and model when deleting a provider.

    Args:
        llm_manager: LLM manager instance
        provider_id_to_delete: Provider being deleted

    Returns:
        Tuple of (fallback_provider_id, fallback_model)
    """
    current_default = llm_manager.get_provider(None)
    is_deleting_default = (
        current_default and current_default.provider_id == provider_id_to_delete
    )

    if is_deleting_default:
        return await _get_ollama_fallback(llm_manager)

    if current_default:
        fallback_provider_id = current_default.provider_id
        fallback_model = await get_fallback_model_for_provider(
            llm_manager, current_default.provider_id
        )

        if not fallback_model:
            import logging

            logging.warning(
                f"No models available for provider {current_default.provider_id}, falling back to ollama-default"
            )
            return await _get_ollama_fallback(llm_manager)

        return fallback_provider_id, fallback_model

    return await _get_ollama_fallback(llm_manager)


async def _get_ollama_fallback(llm_manager: Any) -> Tuple[str, str]:
    """
    Get Ollama fallback provider and model.

    Args:
        llm_manager: LLM manager instance

    Returns:
        Tuple of (provider_id, model_id)
    """
    fallback_provider_id = "ollama-default"
    fallback_model = "llama3.2:1b"

    ollama_provider = llm_manager.get_provider("ollama-default")
    if ollama_provider:
        model = await get_fallback_model_for_provider(llm_manager, "ollama-default")
        if model:
            fallback_model = model

    return fallback_provider_id, fallback_model


async def update_conversations_provider(
    db_pool: Any,
    old_provider_id: str,
    new_provider_id: str,
    new_model: str,
) -> int:
    """
    Update conversations to use a new provider and model.

    Args:
        db_pool: Database connection pool
        old_provider_id: Provider being replaced
        new_provider_id: New provider to use
        new_model: New model to use

    Returns:
        Number of conversations updated
    """
    async with db_pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE conversations 
            SET provider_id = $1, model = $2, updated_at = NOW()
            WHERE provider_id = $3 AND archived_at IS NULL
            """,
            new_provider_id if new_provider_id != "ollama-default" else None,
            new_model,
            old_provider_id,
        )
        return int(result.split()[-1]) if result else 0


async def reload_provider_with_new_config(
    credential_service: Any,
    provider_loader: Any,
    llm_manager: Any,
    provider_id: str,
    new_config: Any,
    set_as_default: Optional[bool],
) -> Optional[JSONResponse]:
    """
    Reload provider with new configuration.

    Args:
        credential_service: Credential service instance
        provider_loader: Provider loader instance
        llm_manager: LLM manager instance
        provider_id: Provider identifier
        new_config: New provider configuration
        set_as_default: Whether to set as default

    Returns:
        JSONResponse if error occurred, None if successful
    """
    update_result = await credential_service.update_provider(
        provider_id=provider_id,
        config=new_config,
        is_default=set_as_default,
    )

    if update_result.is_failure():
        return JSONResponse(
            content=update_result.to_dict(),
            status_code=update_result.status_code,
        )

    load_result = await provider_loader.load_provider(provider_id)

    if load_result.is_failure():
        return JSONResponse(
            content=load_result.to_dict(),
            status_code=load_result.status_code,
        )

    new_provider = load_result.unwrap()

    await llm_manager.remove_provider(provider_id)

    add_result = await llm_manager.add_provider(
        new_provider, set_as_default=set_as_default or False
    )

    if add_result.is_failure():
        return JSONResponse(
            content=add_result.to_dict(),
            status_code=add_result.status_code,
        )

    return None


async def update_provider_default_status(
    credential_service: Any,
    llm_manager: Any,
    provider_id: str,
    set_as_default: bool,
) -> Optional[JSONResponse]:
    """
    Update provider default status only.

    Args:
        credential_service: Credential service instance
        llm_manager: LLM manager instance
        provider_id: Provider identifier
        set_as_default: Whether to set as default

    Returns:
        JSONResponse if error occurred, None if successful
    """
    update_result = await credential_service.update_provider(
        provider_id=provider_id,
        config=None,
        is_default=set_as_default,
    )

    if update_result.is_failure():
        return JSONResponse(
            content=update_result.to_dict(),
            status_code=update_result.status_code,
        )

    if set_as_default is True:
        default_result = llm_manager.set_default_provider(provider_id)
        if default_result.is_failure():
            return JSONResponse(
                content=default_result.to_dict(),
                status_code=default_result.status_code,
            )

    return None


async def fetch_time_based_metadata(
    llm_manager: Any,
    provider_id: str,
    requested: set,
    start_time: Optional[str],
    end_time: Optional[str],
    response: Dict[str, Any],
) -> Optional[JSONResponse]:
    """
    Fetch time-based metadata (usage and costs) for a provider.

    Args:
        llm_manager: LLM manager instance
        provider_id: Provider identifier
        requested: Set of requested metadata types
        start_time: Start time in ISO 8601 format
        end_time: End time in ISO 8601 format
        response: Response dictionary to update

    Returns:
        JSONResponse if error occurred, None if successful
    """
    needs_time_range = "usage" in requested or "costs" in requested
    if not needs_time_range:
        return None

    start_dt, end_dt = parse_datetime_range(start_time, end_time)

    if "usage" in requested:
        error_response = await fetch_provider_usage(
            llm_manager, provider_id, start_dt, end_dt, response
        )
        if error_response:
            return error_response

    if "costs" in requested:
        error_response = await fetch_provider_costs(
            llm_manager, provider_id, start_dt, end_dt, response
        )
        if error_response:
            return error_response

    return None
