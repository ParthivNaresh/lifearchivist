"""
Pydantic models for activity endpoints.
"""

from pydantic import BaseModel, Field


class ActivityEventsResponse(BaseModel):
    """Response model for activity events."""

    success: bool = Field(description="Whether the request was successful")
    events: list = Field(description="List of activity events")
    count: int = Field(description="Number of events returned")
