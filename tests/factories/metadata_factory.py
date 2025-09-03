"""
Factory for creating metadata objects that match production usage.

Based on actual production code in:
- lifearchivist/models/core.py (IngestRequest.metadata, Document.metadata)
- lifearchivist/tools/file_import/file_import_utils.py (create_document_metadata)
- Upload routes that use metadata during file processing
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional


class MetadataFactory:
    """Factory for creating metadata objects that match production patterns."""
    
    @classmethod
    def create_upload_metadata(
        self,
        original_filename: Optional[str] = None,
        source: str = "test_upload",
        **kwargs
    ) -> Dict[str, Any]:
        """Create metadata for upload requests (matches IngestRequest.metadata)."""
        if original_filename is None:
            original_filename = f"test_file_{uuid.uuid4().hex[:8]}.txt"
        
        return {
            "original_filename": original_filename,
            "source": source,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            **kwargs
        }
    
    @classmethod
    def create_document_metadata(
        self,
        file_id: Optional[str] = None,
        file_hash: Optional[str] = None,
        mime_type: str = "text/plain",
        created_at: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create document metadata (matches production create_document_metadata)."""
        if file_id is None:
            file_id = f"doc_{uuid.uuid4().hex[:12]}"
        
        if file_hash is None:
            file_hash = f"hash_{uuid.uuid4().hex}"
        
        if created_at is None:
            created_at = datetime.now(timezone.utc).isoformat()
        
        return {
            "document_id": file_id,
            "file_hash": file_hash,
            "mime_type": mime_type,
            "created_at": created_at,
            "status": "processed",
            "size_bytes": 1024,
            **kwargs
        }
    
    @classmethod
    def create_search_filters(
        self,
        status: Optional[str] = None,
        mime_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        date_range: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create search filters (matches production search filter patterns)."""
        filters = {}
        
        if status:
            filters["status"] = status
        if mime_type:
            filters["mime_type"] = mime_type
        if tags:
            filters["tags"] = tags
        if date_range:
            filters["date_range"] = date_range
        
        filters.update(kwargs)
        return filters


# Convenience functions based on actual production usage patterns
def create_bulk_upload_metadata(file_count: int = 5) -> List[Dict[str, Any]]:
    """Create metadata for bulk upload testing (matches bulk-ingest route)."""
    metadata_list = []
    for i in range(file_count):
        metadata = MetadataFactory.create_upload_metadata(
            original_filename=f"bulk_file_{i+1}.txt",
            source="bulk_folder_upload",
            folder_path="/tmp/test_folder",
        )
        metadata_list.append(metadata)
    return metadata_list


def create_test_document_filters() -> Dict[str, Dict[str, Any]]:
    """Create common filter combinations used in production."""
    return {
        "medical_docs": MetadataFactory.create_search_filters(
            status="processed",
            tags=["medical"],
        ),
        "pdf_documents": MetadataFactory.create_search_filters(
            mime_type="application/pdf",
            status="processed",
        ),
        "recent_docs": MetadataFactory.create_search_filters(
            date_range={
                "start": "2024-01-01T00:00:00Z",
                "end": "2024-12-31T23:59:59Z"
            }
        ),
    }