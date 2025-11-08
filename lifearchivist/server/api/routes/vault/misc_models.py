"""
Miscellaneous models for vault endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class DatabaseRecord(BaseModel):
    """Database record linked to vault file."""

    id: str = Field(..., description="Document ID")
    original_path: Optional[str] = Field(None, description="Original file path")
    status: Optional[str] = Field(None, description="Document status")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_123",
                "original_path": "/path/to/file.pdf",
                "status": "completed",
            }
        }


class VaultFile(BaseModel):
    """Vault file information."""

    path: str = Field(..., description="Relative path from vault root")
    full_path: str = Field(..., description="Absolute file path")
    hash: str = Field(..., description="File content hash")
    extension: str = Field(..., description="File extension")
    size_bytes: int = Field(..., description="File size in bytes")
    created_at: float = Field(..., description="Creation timestamp")
    modified_at: float = Field(..., description="Modification timestamp")
    database_record: Optional[DatabaseRecord] = Field(
        None, description="Linked database record"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "path": "content/ab/cd/ef123456.pdf",
                "full_path": "/vault/content/ab/cd/ef123456.pdf",
                "hash": "abcdef123456",
                "extension": "pdf",
                "size_bytes": 1024000,
                "created_at": 1704067200.0,
                "modified_at": 1704067200.0,
                "database_record": {
                    "id": "doc_123",
                    "original_path": "/path/to/file.pdf",
                    "status": "completed",
                },
            }
        }


class ReconciliationResult(BaseModel):
    """Result of vault reconciliation."""

    documents_checked: int = Field(..., description="Total documents checked")
    orphaned_removed: int = Field(..., description="Orphaned metadata removed")
    errors: int = Field(default=0, description="Number of errors encountered")

    class Config:
        json_schema_extra = {
            "example": {
                "documents_checked": 1250,
                "orphaned_removed": 5,
                "errors": 0,
            }
        }
