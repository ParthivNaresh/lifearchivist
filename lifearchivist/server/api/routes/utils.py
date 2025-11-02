"""
Shared utilities for API route handlers.

Provides common functionality for:
- Result type unwrapping and validation
- Document metadata extraction
- Vault file management
- Error response handling
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, TypeVar

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from .constants import DocumentConstants, HTTPStatus, VaultConstants

T = TypeVar("T")


def unwrap_result_or_error(
    result: Any,
    expected_type: type[T],
    error_message: str = "Operation failed",
) -> T:
    """
    Unwrap a Result object and validate its type, or raise HTTPException.

    Args:
        result: Result object to unwrap
        expected_type: Expected type of the result value
        error_message: Error message prefix for failures

    Returns:
        The unwrapped value of the expected type

    Raises:
        HTTPException: If result is a failure or type mismatch
    """
    if hasattr(result, "is_failure") and result.is_failure():
        raise HTTPException(
            status_code=getattr(
                result, "status_code", HTTPStatus.INTERNAL_SERVER_ERROR
            ),
            detail=f"{error_message}: {getattr(result, 'error', 'Unknown error')}",
        )

    if not hasattr(result, "value"):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"{error_message}: Invalid result object",
        )

    value = result.value
    if not isinstance(value, expected_type):
        raise HTTPException(
            status_code=500,
            detail=f"{error_message}: Expected {expected_type.__name__}, got {type(value).__name__}",
        )

    return value


def unwrap_result_to_json_response(result: Any) -> Optional[JSONResponse]:
    """
    Check if Result is a failure and return JSONResponse if so, otherwise None.

    Args:
        result: Result object to check

    Returns:
        JSONResponse if result is a failure, None if success
    """
    if hasattr(result, "is_failure") and result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=getattr(
                result, "status_code", HTTPStatus.INTERNAL_SERVER_ERROR
            ),
        )
    return None


def extract_result_value(result: Any, expected_type: type[T], default: T) -> T:
    """
    Safely extract value from Result object with type checking and default fallback.

    Args:
        result: Result object to extract from
        expected_type: Expected type of the value
        default: Default value if extraction fails

    Returns:
        Extracted value or default
    """
    if not hasattr(result, "value"):
        return default

    value = result.value
    if isinstance(value, expected_type):
        return value

    return default


async def check_document_deduplication(
    llamaindex_service: Any,
    file_hash: str,
) -> bool:
    """
    Check if a file hash is used by multiple documents (deduplication check).

    Args:
        llamaindex_service: LlamaIndex service instance
        file_hash: File hash to check

    Returns:
        True if file can be safely deleted (used by 0-1 documents), False otherwise
    """
    other_docs_result = await llamaindex_service.query_documents_by_metadata(
        filters={"file_hash": file_hash},
        limit=DocumentConstants.DEDUPLICATION_CHECK_LIMIT,
    )

    other_docs = extract_result_value(other_docs_result, list, [])
    return len(other_docs) <= 1


async def delete_vault_file_safe(
    vault: Any,
    file_hash: Optional[str],
    llamaindex_service: Any,
) -> bool:
    """
    Safely delete a file from vault with deduplication check.

    Only deletes if no other documents reference the same file hash.

    Args:
        vault: Vault service instance
        file_hash: File hash to delete (None if not available)
        llamaindex_service: LlamaIndex service for deduplication check

    Returns:
        True if file was deleted, False otherwise
    """
    if not file_hash or not vault:
        return False

    try:
        can_delete = await check_document_deduplication(llamaindex_service, file_hash)

        if not can_delete:
            return False

        metrics: Dict[str, Any] = {
            "files_deleted": 0,
            "bytes_reclaimed": 0,
            "errors": [],
        }
        await vault.delete_file_by_hash(file_hash, metrics)

        files_deleted_count = metrics.get("files_deleted", 0)
        return isinstance(files_deleted_count, int) and files_deleted_count > 0

    except Exception as e:
        print(f"Warning: Failed to delete file from vault: {e}")
        return False


def extract_document_metadata(
    documents: List[Dict[str, Any]],
    document_id: str,
) -> Dict[str, Any]:
    """
    Extract metadata from document list, raising 404 if not found.

    Args:
        documents: List of document dictionaries
        document_id: Document ID to find

    Returns:
        Document metadata dictionary

    Raises:
        HTTPException: If document not found
    """
    if not documents:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    metadata = documents[0].get("metadata", {})
    if not isinstance(metadata, dict):
        return {}
    return metadata


def validate_file_hash(file_hash: str) -> None:
    """
    Validate SHA256 file hash format.

    Args:
        file_hash: Hash string to validate

    Raises:
        HTTPException: If hash format is invalid
    """
    if not file_hash or len(file_hash) < VaultConstants.MIN_HASH_LENGTH:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="Invalid file hash format. Expected SHA256 hash (64 characters).",
        )

    if len(file_hash) != VaultConstants.HASH_LENGTH:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Invalid hash length: {len(file_hash)}. Expected {VaultConstants.HASH_LENGTH} characters.",
        )


def resolve_vault_file_path(content_dir: Path, file_hash: str) -> Path:
    """
    Resolve vault file path from hash using content-addressed storage structure.

    Vault structure: content/XX/YY/ZZZZ...{ext}
    where XXYYZZZZ... is the SHA256 hash split for directory sharding.

    Args:
        content_dir: Vault content directory
        file_hash: SHA256 hash of the file

    Returns:
        Path to the file

    Raises:
        HTTPException: If file not found
    """
    dir1 = file_hash[:2]
    dir2 = file_hash[2:4]
    file_stem = file_hash[4:]

    file_dir = content_dir / dir1 / dir2

    if not file_dir.exists():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"File not found for hash: {file_hash}",
        )

    matching_files = list(file_dir.glob(f"{file_stem}.*"))

    if not matching_files:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"File not found for hash: {file_hash}",
        )

    file_path = matching_files[0]

    if not file_path.exists():
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"File not found for hash: {file_hash}",
        )

    return file_path


async def get_original_filename(
    llamaindex_service: Any,
    file_hash: str,
    fallback_filename: str,
) -> str:
    """
    Retrieve original filename from metadata, with fallback.

    Args:
        llamaindex_service: LlamaIndex service instance
        file_hash: File hash to look up
        fallback_filename: Filename to use if lookup fails

    Returns:
        Original filename or fallback
    """
    if not llamaindex_service:
        return fallback_filename

    try:
        matching_docs_result = await llamaindex_service.query_documents_by_metadata(
            filters={"file_hash": file_hash},
            limit=DocumentConstants.SINGLE_DOCUMENT_LIMIT,
        )

        matching_docs = extract_result_value(matching_docs_result, list, [])

        if matching_docs:
            metadata = matching_docs[0].get("metadata", {})
            original_path = metadata.get("original_path", "")
            if original_path:
                return Path(original_path).name

    except Exception:
        pass

    return fallback_filename


def get_mime_type_and_disposition(extension: str) -> Tuple[str, str]:
    """
    Determine MIME type and Content-Disposition based on file extension.

    Args:
        extension: File extension (with or without leading dot)

    Returns:
        Tuple of (mime_type, disposition) where disposition is 'inline' or 'attachment'
    """
    ext = extension.lower().lstrip(".")

    mime_types = {
        "pdf": "application/pdf",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "txt": "text/plain",
        "text": "text/plain",
        "rtf": "application/rtf",
        "doc": "application/msword",
        "docx": "application/msword",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.ms-excel",
    }

    inline_extensions = {
        "pdf",
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp",
        "txt",
        "text",
        "rtf",
    }
    attachment_extensions = {"doc", "docx", "xls", "xlsx"}

    mime_type = mime_types.get(ext, "application/octet-stream")

    if ext in inline_extensions:
        disposition = "inline"
    elif ext in attachment_extensions:
        disposition = "attachment"
    else:
        disposition = "attachment"

    return mime_type, disposition


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
        HTTPException: If times are missing or invalid format
    """
    if not start_time or not end_time:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="start_time and end_time required for usage/cost reports",
        )

    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        return start_dt, end_dt
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=f"Invalid datetime format: {e}",
        ) from e


async def fetch_provider_capabilities(
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


def update_settings_in_memory(
    settings: Any,
    request: Any,
) -> List[str]:
    """
    Update settings in memory and return list of updated fields.

    Args:
        settings: Settings instance to update
        request: Settings update request

    Returns:
        List of field names that were updated
    """
    updated_fields = []

    if request.max_file_size_mb is not None:
        settings.max_file_size_mb = request.max_file_size_mb
        updated_fields.append("max_file_size_mb")

    if request.llm_model is not None:
        settings.llm_model = request.llm_model
        updated_fields.append("llm_model")

    if request.embedding_model is not None:
        settings.embedding_model = request.embedding_model
        updated_fields.append("embedding_model")

    if request.theme is not None:
        settings.theme = request.theme
        updated_fields.append("theme")

    return updated_fields


def track_non_persisted_fields(request: Any) -> List[str]:
    """
    Track fields that are not yet persisted to settings object.

    Args:
        request: Settings update request

    Returns:
        List of field names that were provided but not persisted
    """
    tracked_fields = []

    if request.auto_extract_dates is not None:
        tracked_fields.append("auto_extract_dates")
    if request.generate_text_previews is not None:
        tracked_fields.append("generate_text_previews")
    if request.search_results_limit is not None:
        tracked_fields.append("search_results_limit")
    if request.auto_organize_by_date is not None:
        tracked_fields.append("auto_organize_by_date")
    if request.duplicate_detection is not None:
        tracked_fields.append("duplicate_detection")
    if request.default_import_location is not None:
        tracked_fields.append("default_import_location")
    if request.interface_density is not None:
        tracked_fields.append("interface_density")

    return tracked_fields


def build_user_preferences_update_query(
    request: Any,
) -> Tuple[List[str], List[Any], List[str]]:
    """
    Build dynamic SQL update query for user preferences.

    Args:
        request: Settings update request

    Returns:
        Tuple of (update_clauses, values, updated_field_names)
    """
    from typing import Union

    updates = []
    values: List[Union[float, int, str]] = []
    updated_fields = []
    param_count = 1

    if request.temperature is not None:
        updates.append(f"temperature = ${param_count}")
        values.append(request.temperature)
        updated_fields.append("temperature")
        param_count += 1

    if request.max_output_tokens is not None:
        updates.append(f"max_output_tokens = ${param_count}")
        values.append(request.max_output_tokens)
        updated_fields.append("max_output_tokens")
        param_count += 1

    if request.response_format is not None:
        updates.append(f"response_format = ${param_count}")
        values.append(request.response_format)
        updated_fields.append("response_format")
        param_count += 1

    if request.context_window_size is not None:
        updates.append(f"context_window_size = ${param_count}")
        values.append(request.context_window_size)
        updated_fields.append("context_window_size")
        param_count += 1

    if request.response_timeout is not None:
        updates.append(f"response_timeout = ${param_count}")
        values.append(request.response_timeout)
        updated_fields.append("response_timeout")
        param_count += 1

    return updates, values, updated_fields


async def update_existing_conversations(
    conn: Any,
    request: Any,
) -> None:
    """
    Update existing conversations with new default values.

    Args:
        conn: Database connection
        request: Settings update request
    """
    if request.temperature is not None:
        await conn.execute(
            """
            UPDATE conversations 
            SET temperature = $1, updated_at = NOW()
            WHERE temperature = 0.7 AND archived_at IS NULL
            """,
            request.temperature,
        )

    if request.max_output_tokens is not None:
        await conn.execute(
            """
            UPDATE conversations 
            SET max_tokens = $1, updated_at = NOW()
            WHERE max_tokens = 2000 AND archived_at IS NULL
            """,
            request.max_output_tokens,
        )


async def update_conversation_defaults_in_db(
    db_pool: Any,
    request: Any,
) -> List[str]:
    """
    Update conversation default settings in database.

    Args:
        db_pool: Database connection pool
        request: Settings update request

    Returns:
        List of field names that were updated
    """
    async with db_pool.acquire() as conn:
        updates, values, updated_fields = build_user_preferences_update_query(request)

        if updates:
            updates.append("updated_at = NOW()")
            query = f"""
                UPDATE user_preferences 
                SET {', '.join(updates)}
                WHERE user_id = 'default'
            """
            await conn.execute(query, *values)

            await update_existing_conversations(conn, request)

        return updated_fields


def has_conversation_defaults_update(request: Any) -> bool:
    """
    Check if request contains conversation default updates.

    Args:
        request: Settings update request

    Returns:
        True if any conversation defaults are being updated
    """
    return any(
        [
            request.temperature is not None,
            request.max_output_tokens is not None,
            request.response_format is not None,
            request.context_window_size is not None,
            request.response_timeout is not None,
        ]
    )


def parse_date_filter(date_str: Optional[str], filter_name: str) -> Optional[Any]:
    """
    Parse ISO date string to date object.

    Args:
        date_str: ISO date string (YYYY-MM-DD)
        filter_name: Name of filter for error messages

    Returns:
        date object or None if date_str is None

    Raises:
        HTTPException: If date format is invalid
    """
    if not date_str:
        return None

    try:
        from datetime import datetime

        return datetime.fromisoformat(date_str).date()
    except ValueError as err:
        raise HTTPException(
            status_code=400, detail=f"Invalid {filter_name} format"
        ) from err


def extract_document_date(metadata: Dict[str, Any]) -> Optional[str]:
    """
    Extract best available date from document metadata.

    Priority order:
    1. document_created_at
    2. file_modified_at_disk
    3. uploaded_at

    Args:
        metadata: Document metadata dictionary

    Returns:
        ISO date string or None if no date available
    """
    return (
        metadata.get("document_created_at")
        or metadata.get("file_modified_at_disk")
        or metadata.get("uploaded_at")
    )


def parse_document_date(date_str: str) -> Optional[Any]:
    """
    Parse ISO date string to date object.

    Args:
        date_str: ISO date string

    Returns:
        date object or None if parsing fails
    """
    try:
        from datetime import datetime

        doc_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return doc_date.date()
    except (ValueError, AttributeError):
        return None


def should_include_document(
    doc_date: Any,
    filter_start: Optional[Any],
    filter_end: Optional[Any],
) -> bool:
    """
    Check if document date falls within filter range.

    Args:
        doc_date: Document date object
        filter_start: Start date filter (inclusive)
        filter_end: End date filter (inclusive)

    Returns:
        True if document should be included
    """
    if filter_start and doc_date < filter_start:
        return False
    if filter_end and doc_date > filter_end:
        return False
    return True


def update_date_range(
    doc_date: Any,
    earliest: Optional[Any],
    latest: Optional[Any],
) -> Tuple[Any, Any]:
    """
    Update earliest and latest dates.

    Args:
        doc_date: Current document date
        earliest: Current earliest date
        latest: Current latest date

    Returns:
        Tuple of (new_earliest, new_latest)
    """
    new_earliest = (
        earliest if earliest is not None and earliest < doc_date else doc_date
    )
    new_latest = latest if latest is not None and latest > doc_date else doc_date
    return new_earliest, new_latest


def initialize_year_structure(
    by_year: Dict[str, Dict[str, Any]],
    year: str,
) -> None:
    """
    Initialize year structure in timeline data if not exists.

    Args:
        by_year: Timeline data by year dictionary
        year: Year string (YYYY)
    """
    if year not in by_year:
        by_year[year] = {"count": 0, "months": {}}


def initialize_month_structure(
    year_data: Dict[str, Any],
    month: str,
) -> None:
    """
    Initialize month structure in year data if not exists.

    Args:
        year_data: Year data dictionary
        month: Month string (MM)
    """
    if month not in year_data["months"]:
        year_data["months"][month] = {"count": 0, "documents": []}


def create_document_summary(
    doc: Dict[str, Any],
    metadata: Dict[str, Any],
    doc_date_str: str,
) -> Dict[str, Any]:
    """
    Create document summary for timeline.

    Args:
        doc: Document dictionary
        metadata: Document metadata
        doc_date_str: ISO date string

    Returns:
        Document summary dictionary
    """
    return {
        "id": doc.get("document_id"),
        "title": metadata.get("title", "Untitled"),
        "date": doc_date_str,
        "mime_type": metadata.get("mime_type"),
        "theme": metadata.get("classifications", {}).get("theme"),
    }


def add_document_to_timeline(
    timeline_data: Dict[str, Any],
    year: str,
    month: str,
    doc_summary: Dict[str, Any],
) -> None:
    """
    Add document to timeline data structure.

    Args:
        timeline_data: Timeline data dictionary
        year: Year string (YYYY)
        month: Month string (MM)
        doc_summary: Document summary dictionary
    """
    timeline_data["by_year"][year]["months"][month]["documents"].append(doc_summary)
    timeline_data["by_year"][year]["months"][month]["count"] += 1
    timeline_data["by_year"][year]["count"] += 1
    timeline_data["total_documents"] += 1


def process_timeline_document(
    doc: Dict[str, Any],
    timeline_data: Dict[str, Any],
    filter_start: Optional[Any],
    filter_end: Optional[Any],
    earliest_date: Optional[Any],
    latest_date: Optional[Any],
) -> Tuple[Optional[Any], Optional[Any], bool]:
    """
    Process single document for timeline data.

    Args:
        doc: Document dictionary
        timeline_data: Timeline data to update
        filter_start: Start date filter
        filter_end: End date filter
        earliest_date: Current earliest date
        latest_date: Current latest date

    Returns:
        Tuple of (new_earliest, new_latest, was_processed)
    """
    from datetime import datetime

    metadata = doc.get("metadata", {})
    doc_date_str = extract_document_date(metadata)

    if not doc_date_str:
        timeline_data["documents_without_dates"] += 1
        return earliest_date, latest_date, False

    doc_date_only = parse_document_date(doc_date_str)
    if not doc_date_only:
        return earliest_date, latest_date, False

    if not should_include_document(doc_date_only, filter_start, filter_end):
        return earliest_date, latest_date, False

    earliest_date, latest_date = update_date_range(
        doc_date_only, earliest_date, latest_date
    )

    doc_date = datetime.fromisoformat(doc_date_str.replace("Z", "+00:00"))
    year = str(doc_date.year)
    month = f"{doc_date.month:02d}"

    initialize_year_structure(timeline_data["by_year"], year)
    initialize_month_structure(timeline_data["by_year"][year], month)

    doc_summary = create_document_summary(doc, metadata, doc_date_str)
    add_document_to_timeline(timeline_data, year, month, doc_summary)

    return earliest_date, latest_date, True


def extract_document_date_for_summary(
    metadata: Dict[str, Any],
    data_quality: Dict[str, int],
) -> Optional[str]:
    """
    Extract document date and track data quality metrics.

    Args:
        metadata: Document metadata dictionary
        data_quality: Data quality tracking dictionary to update

    Returns:
        ISO date string or None if no date available
    """
    doc_date_str = metadata.get("document_created_at")
    if doc_date_str:
        data_quality["with_document_created_at"] += 1
        return str(doc_date_str)

    doc_date_str = metadata.get("file_modified_at_disk")
    if doc_date_str:
        data_quality["fallback_to_disk"] += 1
        return str(doc_date_str)

    data_quality["no_dates"] += 1
    return None


def process_summary_document(
    doc: Dict[str, Any],
    summary: Dict[str, Any],
    earliest_date: Optional[Any],
    latest_date: Optional[Any],
) -> Tuple[Optional[Any], Optional[Any]]:
    """
    Process single document for timeline summary.

    Args:
        doc: Document dictionary
        summary: Summary data to update
        earliest_date: Current earliest date
        latest_date: Current latest date

    Returns:
        Tuple of (new_earliest, new_latest)
    """
    from datetime import datetime

    metadata = doc.get("metadata", {})
    doc_date_str = extract_document_date_for_summary(metadata, summary["data_quality"])

    if not doc_date_str:
        return earliest_date, latest_date

    try:
        doc_date = datetime.fromisoformat(doc_date_str.replace("Z", "+00:00"))
        doc_date_only = doc_date.date()

        earliest_date, latest_date = update_date_range(
            doc_date_only, earliest_date, latest_date
        )

        year = str(doc_date.year)
        summary["by_year"][year] = summary["by_year"].get(year, 0) + 1

        return earliest_date, latest_date
    except (ValueError, AttributeError):
        return earliest_date, latest_date


def validate_conversation_service(server: Any) -> Any:
    """
    Validate conversation service availability.

    Args:
        server: Server instance

    Returns:
        Conversation service instance

    Raises:
        HTTPException: If service not available
    """
    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503,
            detail="Conversation service not available",
        )

    return server.service_container.conversation_service


def handle_service_result(result: Any) -> Optional[JSONResponse]:
    """
    Handle service result and return error response if failed.

    Args:
        result: Service result object

    Returns:
        JSONResponse if result is failure, None if success
    """
    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )
    return None
