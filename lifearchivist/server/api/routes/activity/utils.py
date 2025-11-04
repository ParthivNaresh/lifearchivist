"""
Utility functions for activity endpoints.
"""

from typing import TYPE_CHECKING, Optional

from fastapi.responses import JSONResponse

from ....constants import ErrorMessages
from ..shared.responses import service_unavailable_response

if TYPE_CHECKING:
    from ....application_server import ApplicationServer


def validate_activity_manager(server: "ApplicationServer") -> Optional[JSONResponse]:
    """
    Validate that activity manager is initialized.

    Args:
        server: Application server instance

    Returns:
        Error response if validation fails, None if valid
    """
    if not server.activity_manager:
        return service_unavailable_response(
            service_name="ActivityManager",
            message=ErrorMessages.ACTIVITY_MANAGER_NOT_INITIALIZED,
        )
    return None


def enforce_limit(limit: int, max_limit: int = 100) -> int:
    """
    Enforce maximum limit for pagination.

    Args:
        limit: Requested limit
        max_limit: Maximum allowed limit

    Returns:
        Clamped limit value
    """
    return min(limit, max_limit)
