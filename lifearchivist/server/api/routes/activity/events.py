"""
Activity events endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from .models import ActivityEventsResponse
from .utils import enforce_limit, validate_activity_manager

router = APIRouter()


@router.get("/events", response_model=ActivityEventsResponse)
async def get_activity_events(limit: int = 200):
    """
    Get recent activity events.

    Args:
        limit: Maximum number of events to return (default: 200, max: 100)

    Returns:
        List of recent activity events, newest first

    Notes:
        - Events are stored in Redis with a maximum of 50 events
        - Events include folder watch, uploads, deletions, Q&A queries, etc.
        - Real-time updates available via WebSocket (type: "activity_event")
    """
    server = get_server()

    error_response = validate_activity_manager(server)
    if error_response:
        return error_response

    assert server.activity_manager is not None

    limit = enforce_limit(limit, max_limit=100)

    try:
        events = await server.activity_manager.get_recent_events(limit)

        return success_response(
            {
                "events": events,
                "count": len(events),
            }
        )

    except Exception as e:
        return internal_error_response(
            operation="Retrieve activity events",
            error=e,
        )
