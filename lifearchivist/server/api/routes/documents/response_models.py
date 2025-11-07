from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .misc_models import ClearAllSummary


class ClearAllResponse(BaseModel):
    """Response from clearing all documents."""

    operation: str = Field(..., description="Operation name")
    summary: ClearAllSummary = Field(..., description="Operation summary")
    vault_metrics: Dict[str, Any] = Field(..., description="Vault clearing metrics")
    llamaindex_metrics: Dict[str, Any] = Field(
        ..., description="LlamaIndex clearing metrics"
    )
    progress_metrics: Dict[str, Any] = Field(
        ..., description="Progress tracking metrics"
    )
    errors: List[str] = Field(
        default_factory=list, description="Any errors encountered"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "operation": "comprehensive_clear_all",
                "summary": {
                    "total_files_deleted": 150,
                    "total_bytes_reclaimed": 52428800,
                    "total_mb_reclaimed": 50.0,
                },
                "vault_metrics": {"files_deleted": 150, "bytes_reclaimed": 52428800},
                "llamaindex_metrics": {
                    "vectors_deleted": 150,
                    "metadata_cleared": True,
                },
                "progress_metrics": {"progress_cleared": True},
                "errors": [],
            }
        }


class DeleteDocumentResponse(BaseModel):
    """Response from deleting a document."""

    document_id: str = Field(..., description="Deleted document ID")
    index_deleted: bool = Field(..., description="Whether index entry was deleted")
    vault_deleted: bool = Field(..., description="Whether vault file was deleted")
    file_hash: Optional[str] = Field(None, description="File hash of deleted document")
    chunks_deleted: Optional[int] = Field(None, description="Number of chunks deleted")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "index_deleted": True,
                "vault_deleted": True,
                "file_hash": "abc123def456",
                "chunks_deleted": 15,
            }
        }


class DocumentAnalysisResponse(BaseModel):
    """Response containing comprehensive document analysis."""

    analysis: Dict[str, Any]

    class Config:
        extra = "allow"


class DocumentChunksResponse(BaseModel):
    """Response containing paginated document chunks."""

    document_id: str = Field(..., description="Document identifier")
    chunks: List[Dict[str, Any]] = Field(..., description="List of chunk objects")
    total: int = Field(..., description="Total number of chunks")
    limit: int = Field(..., description="Requested limit")
    offset: int = Field(..., description="Requested offset")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "chunks": [
                    {
                        "chunk_id": "chunk_1",
                        "text": "This is the first chunk...",
                        "metadata": {"page": 1},
                    }
                ],
                "total": 15,
                "limit": 20,
                "offset": 0,
            }
        }


class DocumentListResponse(BaseModel):
    """Response containing list of documents."""

    documents: List[Dict[str, Any]] = Field(..., description="List of documents")
    total: int = Field(..., description="Number of documents returned")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")

    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "document_id": "doc_123",
                        "title": "Example Document",
                        "status": "completed",
                    }
                ],
                "total": 1,
                "limit": 20,
                "offset": 0,
            }
        }


class DocumentCountResponse(BaseModel):
    """Response containing document count."""

    total: int = Field(..., description="Total number of documents")
    filters: Dict[str, Any] = Field(..., description="Applied filters")

    class Config:
        json_schema_extra = {
            "example": {"total": 150, "filters": {"status": "completed"}}
        }


class DocumentNeighborsResponse(BaseModel):
    """Response containing similar documents."""

    document_id: str = Field(..., description="Source document ID")
    neighbors: List[Dict[str, Any]] = Field(
        ..., description="List of similar documents"
    )
    top_k: int = Field(..., description="Number of neighbors requested")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "neighbors": [
                    {
                        "document_id": "doc_456",
                        "title": "Similar Document",
                        "similarity_score": 0.85,
                    }
                ],
                "top_k": 10,
            }
        }


class SubthemeUpdateResponse(BaseModel):
    """Response from updating document subtheme."""

    document_id: str = Field(..., description="Updated document ID")
    updated_fields: List[str] = Field(..., description="List of updated field names")
    success: bool = Field(default=True, description="Whether update succeeded")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "updated_fields": ["classification", "theme", "subtheme"],
                "success": True,
            }
        }
