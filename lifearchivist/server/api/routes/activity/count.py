"""
Activity count endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
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

    assert server.activity_manager is not None

    try:
        count = await server.activity_manager.get_event_count()

        return success_response(
            {
                "count": count,
                "max_events": server.activity_manager.MAX_EVENTS,
            }
        )

    except Exception as e:
        return internal_error_response(
            operation="Get activity count",
            error=e,
        )
