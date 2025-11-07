from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..shared.constants import FieldDescriptions


class FolderHealthCheckResponse(BaseModel):
    """Response from folder health check."""

    success: bool = Field(description="Whether check succeeded")
    folder_id: str = Field(description=FieldDescriptions.FOLDER_UUID)
    folder_path: str = Field(description="Folder path")
    accessible: bool = Field(description="Whether folder is accessible")
    exists: bool = Field(description="Whether folder exists")
    readable: bool = Field(description="Whether folder is readable")
    health: str = Field(description="Health status")
    error: Optional[str] = Field(default=None, description="Error message if any")


class FolderScanResponse(BaseModel):
    """Response from manual folder scan."""

    success: bool = Field(description="Whether scan succeeded")
    folder_id: str = Field(description=FieldDescriptions.FOLDER_UUID)
    folder_path: str = Field(description="Folder path")
    files_found: int = Field(description="Number of files found")
    files_queued: int = Field(description="Number of files queued for ingestion")
    files_failed: int = Field(description="Number of files failed")
    message: str = Field(description="Status message")


class FolderResponse(BaseModel):
    """Response containing folder information."""

    id: str = Field(description=FieldDescriptions.FOLDER_UUID)
    path: str = Field(description="Absolute folder path")
    enabled: bool = Field(description="Whether watching is enabled")
    created_at: str = Field(description="ISO timestamp when folder was added")
    status: str = Field(description="Current status (active/paused/error/stopped)")
    health: str = Field(description="Health status (healthy/degraded/unhealthy)")
    is_active: bool = Field(description="Whether actively watching")
    success_rate: float = Field(description="Success rate 0.0-1.0")
    stats: Dict[str, Any] = Field(description="Detailed statistics")


class FolderListResponse(BaseModel):
    """Response containing list of folders."""

    success: bool = Field(description="Whether request succeeded")
    folders: List[FolderResponse] = Field(description="List of watched folders")
    total: int = Field(description="Total number of folders")


class AggregateStatusResponse(BaseModel):
    """Aggregate status across all watched folders."""

    success: bool = Field(description="Whether request succeeded")
    total_folders: int = Field(description="Total watched folders")
    active_folders: int = Field(description="Currently active folders")
    total_pending: int = Field(description="Total pending files across all folders")
    total_detected: int = Field(description="Total files detected (all time)")
    total_ingested: int = Field(description="Total files ingested (all time)")
    total_failed: int = Field(description="Total files failed (all time)")
    total_bytes_processed: int = Field(description="Total bytes processed (all time)")
    folders: List[FolderResponse] = Field(description="Individual folder details")
    supported_extensions: List[str] = Field(description="Supported file extensions")
    ingestion_concurrency: int = Field(
        description="Max concurrent ingestions across all folders"
    )


class RemoveFolderResponse(BaseModel):
    """Response from removing a watched folder."""

    message: str = Field(..., description="Success message")
    folder_id: str = Field(..., description="UUID of the removed folder")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Folder removed successfully",
                "folder_id": "123e4567-e89b-12d3-a456-426614174000",
            }
        }
