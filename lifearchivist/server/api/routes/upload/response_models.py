"""
Response models for upload endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    """Response from document ingestion."""

    success: bool = Field(..., description="Whether ingestion succeeded")
    document_id: Optional[str] = Field(None, description="Ingested document ID")
    file_hash: Optional[str] = Field(None, description="File content hash")
    status: Optional[str] = Field(None, description="Ingestion status")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    error: Optional[str] = Field(None, description="Error message if failed")
    error_type: Optional[str] = Field(None, description="Error type if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "document_id": "doc_123",
                "file_hash": "abc123def456",
                "status": "completed",
                "metadata": {},
                "error": None,
                "error_type": None,
            }
        }


class BulkIngestResponse(BaseModel):
    """Response from bulk ingestion."""

    success: bool = Field(..., description="Whether bulk ingestion succeeded")
    total_files: int = Field(..., description="Total files processed")
    successful: int = Field(..., description="Successfully ingested files")
    failed: int = Field(..., description="Failed files")
    results: List[Dict[str, Any]] = Field(
        default_factory=list, description="Individual file results"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "total_files": 10,
                "successful": 9,
                "failed": 1,
                "results": [],
            }
        }


class FileUploadResponse(BaseModel):
    """Response from file upload."""

    success: bool = Field(..., description="Whether upload succeeded")
    filename: str = Field(..., description="Uploaded filename")
    file_path: str = Field(..., description="Saved file path")
    file_size: int = Field(..., description="File size in bytes")
    mime_type: Optional[str] = Field(None, description="Detected MIME type")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "filename": "document.pdf",
                "file_path": "/path/to/document.pdf",
                "file_size": 1024000,
                "mime_type": "application/pdf",
            }
        }


class ProgressResponse(BaseModel):
    """Response from progress endpoint."""

    session_id: str = Field(..., description="Session identifier")
    progress: float = Field(..., ge=0.0, le=1.0, description="Progress (0.0-1.0)")
    status: str = Field(..., description="Current status")
    message: Optional[str] = Field(None, description="Status message")
    completed: bool = Field(..., description="Whether processing is complete")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "session_123",
                "progress": 0.75,
                "status": "processing",
                "message": "Extracting text...",
                "completed": False,
            }
        }
