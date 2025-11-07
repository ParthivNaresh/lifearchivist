"""
Clear activity events endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .response_models import ClearActivityResponse

router = APIRouter()


@router.delete(
    "/events",
    response_model=ClearActivityResponse,
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
                    "example": {
                        "detail": "Clear activity events failed: <error message>"
                    }
                }
            },
        },
    },
)
async def clear_activity_events() -> ClearActivityResponse:
    """
    Clear all activity events from Redis.

    Removes all stored activity events. This is a destructive operation that
    cannot be undone. Useful for testing or clearing old events.

    ## Response Fields

    - **message**: Success confirmation message
    - **events_cleared**: Number of events removed

    ## Example Response

    ```json
    {
        "message": "Activity events cleared",
        "events_cleared": 150
    }
    ```

    ## Use Cases

    - Clear test data
    - Remove old events
    - Reset activity history
    - Free Redis memory
    - Development cleanup

    ## Important Warnings

    - **DESTRUCTIVE**: Cannot be undone
    - **ALL EVENTS LOST**: Every activity event removed
    - **NO BACKUP**: No automatic backup created
    - **IMMEDIATE**: Takes effect immediately
    - **SYSTEM-WIDE**: Affects all users

    ## What Gets Cleared

    - All activity events in Redis
    - Event history
    - Activity logs
    - Tracking data

    ## Performance Notes

    - Fast operation
    - Frees Redis memory
    - No file system impact
    - Immediate effect

    ## Notes

    - Returns 503 if activity manager unavailable
    - Count reflects actual events cleared
    - Safe to call when no events exist
    - Use with caution in production
    """
    server = get_server()

    if not server.activity_manager:
        raise ServiceUnavailableError("Activity manager")

    try:
        cleared_count = await server.activity_manager.clear_all()

        return ClearActivityResponse(
            message="Activity events cleared",
            events_cleared=cleared_count,
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Clear activity events", e) from e
