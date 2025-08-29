"""
File import utilities and constants for document processing.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from lifearchivist.utils.logging import log_event

SUPPORTED_TEXT_EXTRACTION_TYPES = [
    "text/",  # All text/* types
    "application/pdf",  # PDF documents
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # Word documents
]

MIN_TEXT_LENGTH_FOR_EMBEDDINGS = 100
MIN_TEXT_LENGTH_FOR_DATE_EXTRACTION = 50
HASH_CHUNK_SIZE = 4096


def is_text_extraction_supported(mime_type: str) -> bool:
    """
    Check if a file type supports text extraction.

    Args:
        mime_type: MIME type to check

    Returns:
        True if text extraction is supported for this type
    """
    return any(
        (
            mime_type.startswith(file_type)
            if file_type.endswith("/")
            else mime_type == file_type
        )
        for file_type in SUPPORTED_TEXT_EXTRACTION_TYPES
    )


def should_extract_embeddings(text: str) -> bool:
    """
    Determine if text is long enough for meaningful embedding generation.

    Args:
        text: Text content to evaluate

    Returns:
        True if text should be processed for embeddings
    """
    return len(text.strip()) >= MIN_TEXT_LENGTH_FOR_EMBEDDINGS


def should_extract_dates(text: str) -> bool:
    """
    Determine if text is long enough for date extraction.

    Args:
        text: Text content to evaluate

    Returns:
        True if text should be processed for date extraction
    """
    return len(text.strip()) >= MIN_TEXT_LENGTH_FOR_DATE_EXTRACTION


async def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA256 hash of file in chunks for memory efficiency.

    Args:
        file_path: Path to file to hash

    Returns:
        SHA256 hash as hexadecimal string
    """
    hash_sha256 = hashlib.sha256()
    bytes_processed = 0

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b""):
            hash_sha256.update(chunk)
            bytes_processed += len(chunk)

    file_hash = hash_sha256.hexdigest()
    log_event(
        "hash_calculation_completed",
        {
            "file_path": str(file_path),
            "bytes_processed": bytes_processed,
            "hash_algorithm": "sha256",
        },
    )

    return file_hash


def create_document_metadata(
    file_id: str,
    file_hash: str,
    original_path: str,
    mime_type: str,
    stat,
    text: str = "",
) -> Dict[str, Any]:
    """
    Create comprehensive document metadata for LlamaIndex.

    Args:
        file_id: Unique document identifier
        file_hash: SHA256 hash of file content
        original_path: Original file path or filename
        mime_type: MIME type of the file
        stat: File stat object with timestamps and size
        text: Extracted text content

    Returns:
        Dictionary containing complete document metadata
    """
    title = original_path.split("/")[-1] if "/" in original_path else original_path

    metadata = {
        # Core document identification
        "document_id": file_id,
        "file_id": file_id,  # Keep both for compatibility
        # Document metadata
        "file_hash": file_hash,
        "original_path": original_path,
        "title": title,
        "mime_type": mime_type,
        "size_bytes": stat.st_size,
        "status": "processing",  # Will be updated to "ready" later
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": (
            datetime.fromtimestamp(stat.st_mtime).isoformat() if stat.st_mtime else None
        ),
        # Content metadata
        "word_count": len(text.split()) if text else 0,
        "text_length": len(text) if text else 0,
        "has_content": bool(text and len(text.strip()) > 0),
        # Initialize empty arrays for future metadata updates
        "content_dates": [],  # Will be populated by ContentDateExtractionTool
        "tags": [],  # Will be populated by TagTool
        "provenance": [
            create_provenance_entry(
                action="import",
                agent="file_import_tool",
                tool="file.import",
                params={"original_path": original_path},
            )
        ],
    }

    return metadata


def create_provenance_entry(
    action: str,
    agent: str,
    tool: str,
    params: Dict[str, Any],
    result: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Create a standardized provenance entry for audit trails.

    Args:
        action: Action performed (e.g., "import", "extract", "process")
        agent: Agent/component performing the action
        tool: Specific tool used
        params: Parameters passed to the operation
        result: Optional result data from the operation

    Returns:
        Standardized provenance entry dictionary
    """
    entry = {
        "action": action,
        "agent": agent,
        "tool": tool,
        "params": params,
        "timestamp": datetime.now().isoformat(),
    }

    if result is not None:
        entry["result"] = result

    return entry


def create_duplicate_response(
    existing_doc: Dict[str, Any],
    file_hash: str,
    stat,
    mime_type: str,
    display_path: str,
) -> Dict[str, Any]:
    """
    Create standardized response for duplicate file detection.

    Args:
        existing_doc: Existing document metadata from LlamaIndex
        file_hash: SHA256 hash of the duplicate file
        stat: File stat object
        mime_type: MIME type of the file
        display_path: Display path for user feedback

    Returns:
        Standardized duplicate response dictionary
    """
    existing_metadata = existing_doc["metadata"]
    existing_path = existing_metadata.get("original_path", "Unknown")

    return {
        "success": True,
        "file_id": existing_doc["document_id"],
        "hash": file_hash,
        "size": stat.st_size,
        "mime_type": mime_type,
        "status": "duplicate",
        "original_path": display_path,
        "existing_path": existing_path,
        "message": f"File already exists in your archive as '{existing_path}'. Using existing copy.",
        "deduped": True,
    }


def create_success_response(
    file_id: str,
    file_hash: str,
    stat,
    mime_type: str,
    display_path: str,
    vault_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create standardized response for successful file import.

    Args:
        file_id: Document identifier
        file_hash: SHA256 hash of the file
        stat: File stat object
        mime_type: MIME type of the file
        display_path: Display path for user feedback
        vault_result: Result from vault storage operation

    Returns:
        Standardized success response dictionary
    """
    return {
        "success": True,
        "file_id": file_id,
        "hash": file_hash,
        "size": stat.st_size,
        "mime_type": mime_type,
        "status": "ready",
        "original_path": display_path,
        "vault_path": vault_result["path"],
        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "deduped": vault_result["existed"],
    }


def create_error_response(error: Exception, display_path: str) -> Dict[str, Any]:
    """
    Create standardized response for import errors.

    Args:
        error: Exception that occurred
        display_path: Display path for user feedback

    Returns:
        Standardized error response dictionary
    """
    return {
        "success": False,
        "error": str(error),
        "original_path": display_path,
    }
