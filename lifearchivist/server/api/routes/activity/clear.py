"""
Clear activity events endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import create_error_response
from .utils import validate_activity_manager

router = APIRouter()


@router.delete("/events")
async def clear_activity_events():
    """
    Clear all activity events from Redis.

    Returns:
        Number of events cleared

    Notes:
        - This is a destructive operation
        - Use with caution - events cannot be recovered
        - Useful for testing or clearing old events
    """
    server = get_server()

    error_response = validate_activity_manager(server)
    if error_response:
        return error_response

    try:
        cleared_count = await server.activity_manager.clear_all()

        return {
            "success": True,
            "message": "Activity events cleared",
            "events_cleared": cleared_count,
        }

    except Exception as e:
        return create_error_response(
            error_message=f"Failed to clear activity events: {str(e)}",
            error_type=type(e).__name__,
            status_code=500,
        )
