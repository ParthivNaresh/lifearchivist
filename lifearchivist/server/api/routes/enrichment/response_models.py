from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EnrichmentStatusResponse(BaseModel):
    """Response containing enrichment service status."""

    enabled: bool = Field(..., description="Whether enrichment is enabled")
    enrichment_worker: Optional[Dict[str, Any]] = Field(
        None, description="Worker status details (if enabled)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "enrichment_worker": {
                    "status": "running",
                    "tasks_processed": 150,
                    "uptime_seconds": 3600,
                },
            }
        }


class QueueStatsResponse(BaseModel):
    """Response containing enrichment queue statistics."""

    status: str = Field(..., description="Queue operational status")
    queue_length: int = Field(..., description="Number of tasks waiting in queue")
    processing: int = Field(..., description="Number of tasks currently processing")
    completed: int = Field(..., description="Number of recently completed tasks")
    failed: int = Field(..., description="Number of recently failed tasks")
    error: Optional[str] = Field(None, description="Error message if status is 'error'")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "operational",
                "queue_length": 5,
                "processing": 2,
                "completed": 150,
                "failed": 3,
                "error": None,
            }
        }
