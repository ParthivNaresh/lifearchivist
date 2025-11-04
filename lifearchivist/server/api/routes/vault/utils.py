from pathlib import Path
from typing import Any, Optional, Tuple

from fastapi.responses import JSONResponse

from ..constants import DocumentConstants, VaultConstants
from ..shared.responses import not_found_response, validation_error_response
from ..shared.utils import extract_result_value


def validate_file_hash(file_hash: str) -> Optional[JSONResponse]:
    """
    Validate SHA256 file hash format.

    Args:
        file_hash: Hash string to validate

    Returns:
        JSONResponse with error if invalid, None if valid
    """
    if not file_hash or len(file_hash) < VaultConstants.MIN_HASH_LENGTH:
        return validation_error_response(
            "Invalid file hash format. Expected SHA256 hash (64 characters)."
        )

    if len(file_hash) != VaultConstants.HASH_LENGTH:
        return validation_error_response(
            f"Invalid hash length: {len(file_hash)}. Expected {VaultConstants.HASH_LENGTH} characters."
        )

    return None


def resolve_vault_file_path(
    content_dir: Path, file_hash: str
) -> Tuple[Optional[Path], Optional[JSONResponse]]:
    """
    Resolve vault file path from hash using content-addressed storage structure.

    Vault structure: content/XX/YY/ZZZZ...{ext}
    where XXYYZZZZ... is the SHA256 hash split for directory sharding.

    Args:
        content_dir: Vault content directory
        file_hash: SHA256 hash of the file

    Returns:
        Tuple of (file_path, error_response) where one is None
    """
    dir1 = file_hash[:2]
    dir2 = file_hash[2:4]
    file_stem = file_hash[4:]

    file_dir = content_dir / dir1 / dir2

    if not file_dir.exists():
        return None, not_found_response("File", file_hash)

    matching_files = list(file_dir.glob(f"{file_stem}.*"))

    if not matching_files:
        return None, not_found_response("File", file_hash)

    file_path = matching_files[0]

    if not file_path.exists():
        return None, not_found_response("File", file_hash)

    return file_path, None


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
