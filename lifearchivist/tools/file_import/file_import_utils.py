"""
File import utilities and constants for document processing.
"""

import hashlib
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

SUPPORTED_TEXT_EXTRACTION_TYPES = [
    "text/",  # All text/* types (includes text/csv)
    "application/pdf",  # PDF documents
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # Word documents
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # Excel .xlsx
    "application/vnd.ms-excel",  # Excel .xls
    "application/excel",  # Alternative Excel MIME type
    "application/x-excel",  # Alternative Excel MIME type
    "application/x-msexcel",  # Alternative Excel MIME type
    "image/",  # All image/* types for OCR extraction
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


def get_platform_creation_date(file_path: Path) -> Optional[str]:
    """
    Get file creation date using platform-specific methods.

    On macOS: Reads kMDItemContentCreationDate from extended attributes
    On Windows: Uses st_ctime (actual creation time on Windows)
    On Linux: Falls back to st_mtime (Linux doesn't track creation time)

    This is synchronous and fast (<1ms per file), so it doesn't need to be async.

    Args:
        file_path: Path to file

    Returns:
        ISO 8601 formatted creation date string, or None if unavailable
    """
    system = platform.system()

    try:
        if system == "Darwin":  # macOS
            # Use xattr to read macOS extended attributes
            # This is much faster than subprocess calls to mdls
            try:
                import xattr

                # Get the creation date from macOS metadata
                # kMDItemContentCreationDate is stored as a binary plist
                attrs = xattr.xattr(str(file_path))

                # Try to get the creation date attribute
                # macOS stores this in com.apple.metadata:kMDItemContentCreationDate
                creation_date_key = "com.apple.metadata:kMDItemContentCreationDate"
                if creation_date_key in attrs:
                    # Parse the binary plist data
                    import plistlib

                    date_data = attrs[creation_date_key]
                    date_obj = plistlib.loads(date_data)
                    if isinstance(date_obj, datetime):
                        return date_obj.isoformat()
            except (ImportError, KeyError, Exception):
                # xattr not available or attribute doesn't exist
                # Fall back to stat
                pass

        elif system == "Windows":
            # On Windows, st_ctime is actually creation time
            stat = os.stat(file_path)
            return datetime.fromtimestamp(stat.st_ctime).isoformat()

        # Linux or fallback: use modification time (best we can do)
        stat = os.stat(file_path)
        return datetime.fromtimestamp(stat.st_mtime).isoformat()

    except Exception:
        # If anything fails, return None
        # The caller will handle the fallback
        return None


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
    return file_hash


def create_document_metadata(
    file_id: str,
    file_hash: str,
    original_path: str,
    mime_type: str,
    stat,
    text: str = "",
    custom_metadata: Optional[Dict[str, Any]] = None,
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
        custom_metadata: Rest of the custom metadata

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
        # Time tracking - File system timestamps
        "uploaded_at": datetime.now().isoformat(),  # When uploaded to Life Archivist
        "file_created_at_disk": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "file_modified_at_disk": (
            datetime.fromtimestamp(stat.st_mtime).isoformat() if stat.st_mtime else None
        ),
        "document_created_at": None,  # Will be set by metadata extraction
        "document_modified_at": None,  # Will be set by metadata extraction
        # Content metadata
        "word_count": len(text.split()) if text else 0,
        "text_length": len(text) if text else 0,
        "has_content": bool(text and len(text.strip()) > 0),
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

    # Merge in any custom metadata provided during import
    if custom_metadata:
        # Skip reserved fields that could conflict with core metadata
        reserved_fields = {
            "document_id",
            "file_id",
            "file_hash",
            "original_path",
            "title",
            "mime_type",
            "size_bytes",
            "status",
            "uploaded_at",
            "file_created_at_disk",
            "file_modified_at_disk",
            "word_count",
            "text_length",
            "has_content",
            "provenance",
        }

        for key, value in custom_metadata.items():
            if key not in reserved_fields:
                metadata[key] = value

    return metadata


def create_provenance_entry(
    action: str,
    agent: str,
    tool: str,
    params: Dict[str, Any],
    result: Optional[Dict[str, Any]] = None,
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
