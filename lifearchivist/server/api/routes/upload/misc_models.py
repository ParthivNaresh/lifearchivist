"""
Miscellaneous models for upload endpoints.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class IngestionResult(BaseModel):
    """Result of document ingestion."""

    document_id: str = Field(..., description="Ingested document ID")
    file_hash: str = Field(..., description="File content hash")
    status: str = Field(..., description="Ingestion status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "file_hash": "abc123def456",
                "status": "completed",
                "metadata": {"mime_type": "application/pdf"},
            }
        }


class ProgressUpdate(BaseModel):
    """Progress update model."""

    session_id: str = Field(..., description="Session identifier")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0.0-1.0)")
    status: str = Field(..., description="Current status")
    message: Optional[str] = Field(None, description="Status message")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_123",
                "progress": 0.75,
                "status": "processing",
                "message": "Extracting text...",
            }
        }
