"""
Shared utilities for API route handlers.

Provides common functionality for:
- Result type unwrapping and validation
- Document metadata extraction
- Vault file management
- Error response handling
"""

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
