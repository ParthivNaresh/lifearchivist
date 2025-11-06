"""
Activity count endpoint.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError

router = APIRouter()


class ActivityCountResponse(BaseModel):
    """Response containing activity event count."""

    count: int = Field(..., description="Number of events currently stored")
    max_events: int = Field(..., description="Maximum events that can be stored")

    class Config:
        json_schema_extra = {
            "example": {
                "count": 150,
                "max_events": 1000,
            }
        }


@router.get(
    "/count",
    response_model=ActivityCountResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "Activity manager unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Activity manager not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Get activity count failed: <error message>"}
                }
            },
        },
    },
)
async def get_activity_count() -> ActivityCountResponse:
    """
    Get total count of stored activity events.

    Returns the number of activity events currently stored in Redis along with
    the maximum capacity. Useful for monitoring storage usage.

    ## Response Fields

    - **count**: Number of events currently stored
    - **max_events**: Maximum events that can be stored (rolling window)

    ## Example Response

    ```json
    {
        "count": 150,
        "max_events": 1000
    }
    ```

    ## Use Cases

    - Monitor activity storage usage
    - Check if approaching capacity
    - Dashboard metrics
    - System health monitoring
    - Capacity planning

    ## Storage Behavior

    - **Rolling Window**: Oldest events removed when max reached
    - **Redis Storage**: Events stored in Redis
    - **Fast Query**: Count retrieved quickly
    - **Real-time**: Current snapshot

    ## Capacity Management

    - Events stored up to max_events limit
    - Oldest events automatically removed
    - No manual cleanup needed
    - Configurable maximum

    ## Performance Notes

    - Fast Redis count operation
    - No heavy computation
    - Safe to poll frequently
    - Minimal overhead

    ## Notes

    - Returns 503 if activity manager unavailable
    - Count is current snapshot
    - Max events is system configuration
    - Rolling window maintains capacity
    """
    server = get_server()

    if not server.activity_manager:
        raise ServiceUnavailableError("Activity manager")

    try:
        count = await server.activity_manager.get_event_count()

        return ActivityCountResponse(
            count=count,
            max_events=server.activity_manager.MAX_EVENTS,
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Get activity count", e) from e
