"""
Factory for creating metadata objects that match production usage.

Aligned with:
- lifearchivist/tools/file_import/file_import_utils.py (create_document_metadata)
- lifearchivist/server/api/routes/upload.py (ingest/upload endpoints)
- Index/search filters supported by IndexSearchTool
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from .document_factory import DocumentFactory


class MetadataFactory:
    """Factory for creating metadata objects that match production patterns."""

    @classmethod
    def create_upload_metadata(
        cls,
        original_filename: Optional[str] = None,
        source: str = "test_upload",
        **kwargs,
    ) -> Dict[str, Any]:
        """Create metadata for upload/ingest requests (merged into file.import params)."""
        if original_filename is None:
            original_filename = f"test_file_{uuid.uuid4().hex[:8]}.txt"

        return {
            "original_filename": original_filename,
            "source": source,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }

    @classmethod
    def create_document_metadata(
        cls,
        *,
        document_id: Optional[str] = None,
        file_hash: Optional[str] = None,
        original_path: str = "",
        mime_type: str = "text/plain",
        size_bytes: int = 1024,
        status: str = "ready",
        tags: Optional[List[str]] = None,
        has_content: bool = True,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create LlamaIndex-style document metadata via DocumentFactory for exact shape."""
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        file_hash_val = file_hash or f"hash_{uuid.uuid4().hex}"
        meta = DocumentFactory.build_llamaindex_metadata(
            document_id=doc_id,
            file_hash=file_hash_val,
            original_path=original_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            status=status,
            tags=tags or [],
            has_content=has_content,
            extra=extra or {},
        )
        return meta

    @classmethod
    def create_search_filters(
        cls,
        status: Optional[str] = None,
        mime_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create search filters (IndexSearchTool supports mime_type, status, tags)."""
        filters: Dict[str, Any] = {}
        if status:
            filters["status"] = status
        if mime_type:
            filters["mime_type"] = mime_type
        if tags:
            filters["tags"] = tags
        # Additional keys are appended but may be ignored by search tool
        filters.update(kwargs)
        return filters


# Convenience functions based on actual production usage patterns

def create_bulk_upload_metadata(file_count: int = 5) -> List[Dict[str, Any]]:
    """Create per-file metadata commonly merged into file.import for bulk ingest tests."""
    return [
        MetadataFactory.create_upload_metadata(
            original_filename=f"bulk_file_{i+1}.txt", source="bulk_folder_upload", folder_path="/tmp/test_folder"
        )
        for i in range(file_count)
    ]


def create_test_document_filters() -> Dict[str, Dict[str, Any]]:
    """Create common filter combinations consistent with IndexSearchTool."""
    return {
        "medical_docs": MetadataFactory.create_search_filters(
            status="ready", tags=["medical"]
        ),
        "pdf_documents": MetadataFactory.create_search_filters(
            mime_type="application/pdf", status="ready"
        ),
        # date_range keys may be ignored by the current search tool but kept for future use
        "recent_docs": MetadataFactory.create_search_filters(
            date_range={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z",
            }
        ),
    }