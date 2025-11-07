"""
Request models for activity endpoints.
"""

from pydantic import BaseModel, Field

from .constants import DEFAULT_LIMIT, MAX_LIMIT, MIN_LIMIT


class GetActivityEventsRequest(BaseModel):
    """
    Request parameters for getting activity events.
    """

    limit: int = Field(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description="Maximum number of events to return",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "limit": 200,
            }
        }
