"""
Response models for vault endpoints.
"""

from typing import List

from pydantic import BaseModel, Field

from .misc_models import ReconciliationResult, VaultFile


class VaultInfoResponse(BaseModel):
    """Response from vault info endpoint."""

    vault_path: str = Field(..., description="Absolute path to vault root")
    total_files: int = Field(..., description="Total number of files")
    total_size_bytes: int = Field(..., description="Total storage in bytes")
    total_size_mb: float = Field(..., description="Total storage in MB")

    class Config:
        json_schema_extra = {
            "example": {
                "vault_path": "/path/to/vault",
                "total_files": 1250,
                "total_size_bytes": 5368709120,
                "total_size_mb": 5120.0,
            }
        }


class ListVaultFilesResponse(BaseModel):
    """Response from list vault files endpoint."""

    files: List[VaultFile] = Field(..., description="List of vault files")
    total: int = Field(..., description="Total number of files")
    directory: str = Field(..., description="Directory queried")
    limit: int = Field(..., description="Limit applied")
    offset: int = Field(..., description="Offset applied")

    class Config:
        json_schema_extra = {
            "example": {
                "files": [],
                "total": 1250,
                "directory": "content",
                "limit": 100,
                "offset": 0,
            }
        }


class ReconcileVaultResponse(BaseModel):
    """Response from vault reconciliation endpoint."""

    reconciliation: ReconciliationResult = Field(
        ..., description="Reconciliation results"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "reconciliation": {
                    "documents_checked": 1250,
                    "orphaned_removed": 5,
                    "errors": 0,
                }
            }
        }
