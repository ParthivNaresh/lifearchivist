"""
Activity count endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import create_error_response
from .utils import validate_activity_manager

router = APIRouter()


@router.get("/count")
async def get_activity_count():
    """
    Get total count of stored activity events.

    Returns:
        Number of events currently stored in Redis
    """
    server = get_server()

    error_response = validate_activity_manager(server)
    if error_response:
        return error_response

    try:
        count = await server.activity_manager.get_event_count()

        return {
            "success": True,
            "count": count,
            "max_events": server.activity_manager.MAX_EVENTS,
        }

    except Exception as e:
        return create_error_response(
            error_message=f"Failed to get event count: {str(e)}",
            error_type=type(e).__name__,
            status_code=500,
        )
