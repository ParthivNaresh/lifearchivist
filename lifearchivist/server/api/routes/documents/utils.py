"""
Utility functions for document endpoints.
"""

from typing import Dict


def format_document_for_ui(doc: Dict) -> Dict:
    """
    Format a document for UI consumption.

    Extracts and flattens metadata for easier frontend access.
    """
    metadata = doc.get("metadata", {})
    theme_metadata = metadata.get("classifications", {})

    return {
        "id": doc.get("document_id") or metadata.get("document_id"),
        "file_hash": metadata.get("file_hash", ""),
        "original_path": metadata.get("original_path", ""),
        "mime_type": metadata.get("mime_type"),
        "size_bytes": metadata.get("size_bytes", 0),
        "created_at": metadata.get("created_at", ""),
        "modified_at": metadata.get("modified_at"),
        "ingested_at": metadata.get("created_at", ""),
        "status": metadata.get("status", "unknown"),
        "error_message": metadata.get("error_message"),
        "word_count": metadata.get("word_count"),
        "language": metadata.get("language"),
        "extraction_method": metadata.get("extraction_method"),
        "text_preview": doc.get("text_preview", ""),
        "has_content": metadata.get("has_content", False),
        "tags": metadata.get("tags", []),
        "tag_count": len(metadata.get("tags", [])),
        "theme": theme_metadata.get("theme"),
        "theme_confidence": theme_metadata.get("confidence"),
        "confidence_level": theme_metadata.get("confidence_level"),
        "classification": theme_metadata.get("match_tier"),
        "pattern_or_phrase": theme_metadata.get("match_pattern"),
        "subthemes": theme_metadata.get("subthemes", []),
        "primary_subtheme": theme_metadata.get("primary_subtheme"),
        "subclassifications": theme_metadata.get("subclassifications", []),
        "primary_subclassification": theme_metadata.get("primary_subclassification"),
        "subclassification_confidence": theme_metadata.get(
            "subclassification_confidence"
        ),
        "category_mapping": theme_metadata.get("category_mapping", {}),
    }


def validate_pagination(
    limit: int,
    offset: int,
    max_limit: int,
    min_limit: int,
    default_limit: int,
    default_offset: int,
) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters.

    Returns normalized (limit, offset) tuple.
    """
    if limit > max_limit:
        limit = max_limit
    elif limit < min_limit:
        limit = default_limit

    if offset < default_offset:
        offset = default_offset

    return limit, offset
