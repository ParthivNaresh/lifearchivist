"""
Shared dependency injection for API routes.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ....application_server import ApplicationServer


def get_server() -> "ApplicationServer":
    """
    Get the current server instance.

    Returns:
        The global ApplicationServer instance

    Raises:
        RuntimeError: If server instance not initialized
    """
    from ...dependencies import get_server as _get_server

    return _get_server()
