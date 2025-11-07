from pydantic import BaseModel, Field


class ClearAllSummary(BaseModel):
    """Summary of clear all operation."""

    total_files_deleted: int = Field(..., description="Total files deleted")
    total_bytes_reclaimed: int = Field(..., description="Total bytes reclaimed")
    total_mb_reclaimed: float = Field(..., description="Total MB reclaimed")
