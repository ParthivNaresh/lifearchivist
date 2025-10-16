"""
Activity feed API endpoints.

Provides endpoints for retrieving system activity events.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..dependencies import get_server

router = APIRouter(prefix="/api/activity", tags=["activity"])


class ActivityEventsResponse(BaseModel):
    """Response model for activity events."""

    success: bool = Field(description="Whether the request was successful")
    events: list = Field(description="List of activity events")
    count: int = Field(description="Number of events returned")


@router.get("/events", response_model=ActivityEventsResponse)
async def get_activity_events(limit: int = 200):
    """
    Get recent activity events.

    Args:
        limit: Maximum number of events to return (default: 200, max: 200)

    Returns:
        List of recent activity events, newest first

    Notes:
        - Events are stored in Redis with a maximum of 50 events
        - Events include folder watch, uploads, deletions, Q&A queries, etc.
        - Real-time updates available via WebSocket (type: "activity_event")
    """
    server = get_server()

    if not server.activity_manager:
        return JSONResponse(
            content={
                "success": False,
                "error": "Activity manager not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    # Enforce maximum limit
    limit = min(limit, 100)

    try:
        events = await server.activity_manager.get_recent_events(limit)

        return {
            "success": True,
            "events": events,
            "count": len(events),
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to retrieve activity events: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.get("/count")
async def get_activity_count():
    """
    Get total count of stored activity events.

    Returns:
        Number of events currently stored in Redis
    """
    server = get_server()

    if not server.activity_manager:
        return JSONResponse(
            content={
                "success": False,
                "error": "Activity manager not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        count = await server.activity_manager.get_event_count()

        return {
            "success": True,
            "count": count,
            "max_events": server.activity_manager.MAX_EVENTS,
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to get event count: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


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

    if not server.activity_manager:
        return JSONResponse(
            content={
                "success": False,
                "error": "Activity manager not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        cleared_count = await server.activity_manager.clear_all()

        return {
            "success": True,
            "message": "Activity events cleared",
            "events_cleared": cleared_count,
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to clear activity events: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
