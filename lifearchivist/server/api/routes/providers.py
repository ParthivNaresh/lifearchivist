"""
LLM Provider management endpoints.

Provides CRUD operations for LLM providers including:
- Adding and configuring providers (OpenAI, Ollama, Anthropic, etc.)
- Listing and filtering providers
- Testing provider credentials
- Managing default provider
- Listing available models per provider
- Generating text with specific providers

Security Note:
    This API is designed for local-first, single-user desktop applications.
    No authentication is required as the API runs on localhost and is only
    accessible to the local user. The "credentials" managed here are API keys
    for external LLM providers (OpenAI, Anthropic, etc.), not authentication
    credentials for this API.

    For multi-tenant deployments, add authentication middleware and user isolation.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from lifearchivist.llm import (
    LLMMessage,
    ProviderType,
)

from ..dependencies import get_server
from .constants import ErrorMessages
from .utils import (
    determine_fallback_provider,
    fetch_provider_capabilities,
    fetch_provider_workspaces,
    fetch_time_based_metadata,
    reload_provider_with_new_config,
    update_conversations_provider,
    update_provider_default_status,
)

router = APIRouter(prefix="/api/providers", tags=["providers"])


# Request/Response Models
class AddProviderRequest(BaseModel):
    """Request to add a new provider."""

    provider_id: str = Field(..., description="Unique identifier for the provider")
    provider_type: str = Field(
        ..., description="Type of provider (ollama, openai, anthropic, google)"
    )
    config: Dict[str, Any] = Field(..., description="Provider configuration")
    set_as_default: bool = Field(default=False, description="Set as default provider")


class UpdateProviderRequest(BaseModel):
    """Request to update provider configuration."""

    config: Optional[Dict[str, Any]] = Field(None, description="New configuration")
    set_as_default: Optional[bool] = Field(None, description="Set as default provider")


class GenerateRequest(BaseModel):
    """Request to generate text."""

    messages: List[Dict[str, str]] = Field(
        ..., min_length=1, description="Conversation messages"
    )
    model: str = Field(..., min_length=1, description="Model identifier")
    provider_id: Optional[str] = Field(
        None, description="Provider ID (uses default if None)"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=2000, ge=1, le=100000, description="Maximum tokens to generate"
    )


class SetDefaultRequest(BaseModel):
    """Request to set default provider."""

    provider_id: str = Field(
        ..., min_length=1, description="Provider ID to set as default"
    )
    default_model: Optional[str] = Field(
        None, description="Default model to use with this provider"
    )


# Helper Functions
def _parse_provider_type(provider_type_str: str) -> ProviderType:
    """Parse provider type string to enum."""
    try:
        return ProviderType(provider_type_str.lower())
    except ValueError:
        valid_types = [t.value for t in ProviderType]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider type '{provider_type_str}'. Valid types: {valid_types}",
        ) from None


def _create_provider_config(provider_type: ProviderType, config_dict: Dict[str, Any]):
    """Create typed provider config from dict."""
    try:
        from lifearchivist.llm.provider_config import create_provider_config

        return create_provider_config(provider_type, **config_dict)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid configuration: {str(e)}",
        ) from e


# Endpoints
@router.post("")
async def add_provider(request: AddProviderRequest):
    """
    Add a new LLM provider.

    Validates configuration, stores encrypted credentials, and initializes the provider.

    Example:
        ```json
        {
            "provider_id": "my-openai",
            "provider_type": "openai",
            "config": {
                "api_key": "sk-...",
                "organization": "org-..."
            },
            "set_as_default": true
        }
        ```
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    if not server.credential_service:
        raise HTTPException(status_code=503, detail="Credential service not available")

    try:
        # Parse and validate provider type
        provider_type = _parse_provider_type(request.provider_type)

        # Create typed config
        config = _create_provider_config(provider_type, request.config)

        # Store credentials
        store_result = await server.credential_service.add_provider(
            provider_id=request.provider_id,
            provider_type=provider_type,
            config=config,
            is_default=request.set_as_default,
        )

        if store_result.is_failure():
            return JSONResponse(
                content=store_result.to_dict(),
                status_code=store_result.status_code,
            )

        # Load and add provider to manager
        if server.provider_loader:
            load_result = await server.provider_loader.load_provider(
                request.provider_id
            )

            if load_result.is_failure():
                # Rollback: delete from storage
                await server.credential_service.delete_provider(request.provider_id)
                return JSONResponse(
                    content=load_result.to_dict(),
                    status_code=load_result.status_code,
                )

            provider = load_result.unwrap()

            # Add to manager (initializes provider)
            add_result = await server.llm_manager.add_provider(
                provider, set_as_default=request.set_as_default
            )

            if add_result.is_failure():
                # Rollback: delete from storage
                await server.credential_service.delete_provider(request.provider_id)
                return JSONResponse(
                    content=add_result.to_dict(),
                    status_code=add_result.status_code,
                )

        return {
            "success": True,
            "provider_id": request.provider_id,
            "provider_type": provider_type.value,
            "is_default": request.set_as_default,
            "message": "Provider added successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("")
async def list_providers():
    """
    List all registered LLM providers.

    Returns provider metadata including type, default status, and health.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        providers = server.llm_manager.list_providers()

        return {
            "success": True,
            "providers": providers,
            "total": len(providers),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{provider_id}")
async def get_provider(provider_id: str):
    """
    Get details for a specific provider.

    Returns provider metadata without exposing credentials.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    if not server.credential_service:
        raise HTTPException(status_code=503, detail="Credential service not available")

    try:
        # Get provider from manager
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found",
            )

        # Get metadata from storage (without credentials)
        metadata_result = await server.credential_service.get_provider_metadata(
            provider_id
        )

        if metadata_result.is_failure():
            return JSONResponse(
                content=metadata_result.to_dict(),
                status_code=metadata_result.status_code,
            )

        metadata = metadata_result.unwrap()

        # Get health status
        is_healthy = True
        if server.llm_manager.health_monitor:
            is_healthy = server.llm_manager.health_monitor.is_healthy(provider_id)

        return {
            "success": True,
            "provider_id": provider_id,
            "provider_type": provider.provider_type.value,
            "is_default": metadata.get("is_default", False),
            "is_initialized": provider.is_initialized,
            "is_healthy": is_healthy,
            "user_id": metadata.get("user_id", "default"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{provider_id}/usage-check")
async def check_provider_usage(provider_id: str):
    """
    Check if a provider is being used by any conversations.

    Returns the count of conversations using this provider.
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503, detail=ErrorMessages.CONVERSATION_SERVICE_NOT_AVAILABLE
        )

    try:
        db_pool = server.service_container.conversation_service.db_pool

        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE provider_id = $1 AND archived_at IS NULL",
                provider_id,
            )

            conversations = await conn.fetch(
                "SELECT id, title, model FROM conversations WHERE provider_id = $1 AND archived_at IS NULL LIMIT 5",
                provider_id,
            )

            return {
                "success": True,
                "provider_id": provider_id,
                "conversation_count": count or 0,
                "sample_conversations": (
                    [
                        {
                            "id": str(conv["id"]),
                            "title": conv["title"] or "Untitled",
                            "model": conv["model"],
                        }
                        for conv in conversations
                    ]
                    if conversations
                    else []
                ),
            }

    except Exception as e:
        import logging

        logging.error(f"Failed to check provider usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to check provider usage: {str(e)}"
        ) from e


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    update_conversations: bool = Query(
        default=False,
        description="Update affected conversations to use default provider",
    ),
):
    """
    Delete a provider.

    Removes from manager, cleans up resources, and deletes stored credentials.
    Optionally updates affected conversations to use the default provider.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    if not server.credential_service:
        raise HTTPException(status_code=503, detail="Credential service not available")

    try:
        affected_conversations = 0

        should_update = (
            update_conversations
            and server.service_container
            and server.service_container.conversation_service
        )

        if should_update:
            fallback_provider_id, fallback_model = await determine_fallback_provider(
                server.llm_manager, provider_id
            )

            db_pool = server.service_container.conversation_service.db_pool  # type: ignore[union-attr]
            affected_conversations = await update_conversations_provider(
                db_pool,
                provider_id,
                fallback_provider_id,
                fallback_model,
            )

        remove_result = await server.llm_manager.remove_provider(provider_id)

        if remove_result.is_failure():
            return JSONResponse(
                content=remove_result.to_dict(),
                status_code=remove_result.status_code,
            )

        delete_result = await server.credential_service.delete_provider(provider_id)

        if delete_result.is_failure():
            return JSONResponse(
                content=delete_result.to_dict(),
                status_code=delete_result.status_code,
            )

        return {
            "success": True,
            "provider_id": provider_id,
            "message": "Provider deleted successfully",
            "affected_conversations": affected_conversations,
            "conversations_updated": update_conversations
            and affected_conversations > 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.patch("/{provider_id}")
async def update_provider(provider_id: str, request: UpdateProviderRequest):
    """
    Update provider configuration.

    Can update credentials and/or default status.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    if not server.credential_service:
        raise HTTPException(status_code=503, detail="Credential service not available")

    if request.config is None and request.set_as_default is None:
        raise HTTPException(
            status_code=400,
            detail="Must provide at least one of: config, set_as_default",
        )

    try:
        metadata_result = await server.credential_service.get_provider_metadata(
            provider_id
        )

        if metadata_result.is_failure():
            return JSONResponse(
                content=metadata_result.to_dict(),
                status_code=metadata_result.status_code,
            )

        metadata = metadata_result.unwrap()
        provider_type = _parse_provider_type(metadata["provider_type"])

        new_config = None
        if request.config is not None:
            new_config = _create_provider_config(provider_type, request.config)

        if new_config is not None and server.provider_loader:
            error_response = await reload_provider_with_new_config(
                server.credential_service,
                server.provider_loader,
                server.llm_manager,
                provider_id,
                new_config,
                request.set_as_default,
            )
            if error_response:
                return error_response
        else:
            if request.set_as_default is not None:
                error_response = await update_provider_default_status(
                    server.credential_service,
                    server.llm_manager,
                    provider_id,
                    request.set_as_default,
                )
                if error_response:
                    return error_response

        return {
            "success": True,
            "provider_id": provider_id,
            "message": "Provider updated successfully",
            "config_updated": new_config is not None,
            "default_updated": request.set_as_default is not None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{provider_id}/test")
async def test_provider(provider_id: str):
    """
    Test provider credentials and connectivity.

    Validates that the provider can be reached and credentials are valid.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        # Get provider
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found",
            )

        # Validate credentials
        is_valid = await provider.validate_credentials()

        return {
            "success": True,
            "provider_id": provider_id,
            "is_valid": is_valid,
            "message": "Credentials valid" if is_valid else "Credentials invalid",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{provider_id}/models")
async def list_provider_models(provider_id: str):
    """
    List available models for a provider.

    Returns model metadata including context window, cost, and capabilities.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        # List models
        result = await server.llm_manager.list_models(provider_id=provider_id)

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        models = result.unwrap()

        # Format models for response
        formatted_models = [
            {
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "provider_id": model.provider_id,  # NEW: Include provider instance ID
                "context_window": model.context_window,
                "max_output_tokens": model.max_output_tokens,
                "supports_streaming": model.supports_streaming,
                "supports_functions": model.supports_functions,
                "supports_vision": model.supports_vision,
                "cost_per_1k_input": model.cost_per_1k_input,
                "cost_per_1k_output": model.cost_per_1k_output,
                "metadata": model.metadata,
            }
            for model in models
        ]

        return {
            "success": True,
            "provider_id": provider_id,
            "models": formatted_models,
            "total": len(formatted_models),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/generate")
async def generate_text(request: GenerateRequest):
    """
    Generate text using a provider.

    Example:
        ```json
        {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "model": "gpt-4o-mini",
            "provider_id": "my-openai",
            "temperature": 0.7,
            "max_tokens": 500
        }
        ```
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        # Convert messages to LLMMessage objects
        llm_messages = [
            LLMMessage(
                role=msg["role"],
                content=msg["content"],
                name=msg.get("name"),
            )
            for msg in request.messages
        ]

        # Generate response
        result = await server.llm_manager.generate(
            messages=llm_messages,
            model=request.model,
            provider_id=request.provider_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        response = result.unwrap()

        return {
            "success": True,
            "content": response.content,
            "model": response.model,
            "provider": response.provider,
            "tokens_used": response.tokens_used,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "cost_usd": response.cost_usd,
            "finish_reason": response.finish_reason,
            "metadata": response.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/default")
async def set_default_provider(request: SetDefaultRequest):
    """
    Set the default provider and optionally a default model.

    The default provider is used when no explicit provider is specified.
    Admin providers cannot be set as default since they cannot provide inference.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        provider = server.llm_manager.get_provider(request.provider_id)
        if not provider:
            raise HTTPException(
                status_code=404, detail=f"Provider '{request.provider_id}' not found"
            )

        provider_info = next(
            (
                p
                for p in server.llm_manager.list_providers()
                if p["id"] == request.provider_id
            ),
            None,
        )

        if provider_info and provider_info.get("is_admin"):
            raise HTTPException(
                status_code=400,
                detail="Admin providers cannot be set as default. Admin keys are for analytics only and cannot provide inference.",
            )

        result = server.llm_manager.set_default_provider(request.provider_id)

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        if request.default_model:
            from lifearchivist.config import get_settings

            settings = get_settings()
            settings.llm_model = request.default_model

        return {
            "success": True,
            "provider_id": request.provider_id,
            "default_model": request.default_model,
            "message": "Default provider updated",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{provider_id}/metadata")
async def get_provider_metadata(
    provider_id: str,
    include: List[str] = Query(  # noqa: B008
        default=["capabilities"], description="Metadata types to include"
    ),
    start_time: Optional[str] = Query(  # noqa: B008
        None, description="Start time for usage/cost reports (ISO 8601)"
    ),
    end_time: Optional[str] = Query(  # noqa: B008
        None, description="End time for usage/cost reports (ISO 8601)"
    ),
):
    """
    Get provider metadata including capabilities, workspaces, usage, and costs.

    Query Parameters:
        - include: List of metadata types to include (capabilities, workspaces, usage, costs)
        - start_time: Start time for usage/cost reports (ISO 8601 format)
        - end_time: End time for usage/cost reports (ISO 8601 format)

    Examples:
        - GET /api/providers/anthropic-work/metadata
        - GET /api/providers/anthropic-work/metadata?include=capabilities&include=workspaces
        - GET /api/providers/anthropic-work/metadata?include=usage&include=costs&start_time=2025-01-01T00:00:00Z&end_time=2025-01-08T00:00:00Z

    Returns:
        Metadata object with requested fields. Unsupported features return 501.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found",
            )

        response: Dict[str, Any] = {
            "success": True,
            "provider_id": provider_id,
        }

        valid_includes = {"capabilities", "workspaces", "usage", "costs"}
        requested = set(include) & valid_includes

        if "capabilities" in requested:
            await fetch_provider_capabilities(server.llm_manager, provider_id, response)

        if "workspaces" in requested:
            error_response = await fetch_provider_workspaces(
                server.llm_manager, provider, provider_id, response
            )
            if error_response:
                return error_response

        error_response = await fetch_time_based_metadata(
            server.llm_manager, provider_id, requested, start_time, end_time, response
        )
        if error_response:
            return error_response

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
