"""
Utility functions for activity endpoints.
"""

from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from ....constants import ErrorMessages
from ..shared.responses import create_error_response

if TYPE_CHECKING:
    from ....application_server import ApplicationServer


def validate_activity_manager(server: "ApplicationServer") -> JSONResponse | None:
    """
    Validate that activity manager is initialized.

    Args:
        server: Application server instance

    Returns:
        Error response if validation fails, None if valid
    """
    if not server.activity_manager:
        return create_error_response(
            error_message=ErrorMessages.ACTIVITY_MANAGER_NOT_INITIALIZED,
            error_type="ServiceUnavailable",
            status_code=503,
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
