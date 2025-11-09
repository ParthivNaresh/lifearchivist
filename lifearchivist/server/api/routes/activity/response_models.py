"""
Response models for activity endpoints.
"""

from typing import List

from pydantic import BaseModel, Field

from .misc_models import ActivityEvent


class ActivityEventsResponse(BaseModel):
    """
    Response containing activity events.
    """

    events: List[ActivityEvent] = Field(..., description="List of activity events")
    count: int = Field(..., description="Number of events returned")

    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "id": "1704723000.123_document_uploaded",
                        "type": "document_uploaded",
                        "data": {
                            "document_id": "doc_123",
                            "filename": "report.pdf",
                            "size_bytes": 1024000,
                        },
                        "timestamp": "2025-01-08T14:30:00.123Z",
                    }
                ],
                "count": 1,
            }
        }


class ActivityCountResponse(BaseModel):
    """
    Response containing activity event count.
    """

    count: int = Field(..., description="Number of events currently stored")
    max_events: int = Field(..., description="Maximum events that can be stored")

    class Config:
        json_schema_extra = {
            "example": {
                "count": 150,
                "max_events": 1000,
            }
        }


class ClearActivityResponse(BaseModel):
    """
    Response from clearing activity events.
    """

    message: str = Field(..., description="Success message")
    events_cleared: int = Field(..., description="Number of events cleared")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Activity events cleared",
                "events_cleared": 150,
            }
        }
