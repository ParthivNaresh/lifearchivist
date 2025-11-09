"""
Miscellaneous models for activity endpoints.
"""

from typing import Any, Dict

from pydantic import BaseModel, Field


class ActivityEvent(BaseModel):
    """
    Individual activity event model.
    """

    id: str = Field(..., description="Unique event identifier")
    type: str = Field(..., description="Event type identifier")
    data: Dict[str, Any] = Field(..., description="Event-specific data")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "1704723000.123_document_uploaded",
                "type": "document_uploaded",
                "data": {
                    "document_id": "doc_123",
                    "filename": "report.pdf",
                    "size_bytes": 1024000,
                },
                "timestamp": "2025-01-08T14:30:00.123Z",
            }
        }
