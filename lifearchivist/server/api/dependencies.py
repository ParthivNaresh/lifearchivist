"""
Dependency injection for API routes.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..mcp_server import MCPServer


# Global server instance - will be set during app initialization
_server_instance: Optional["MCPServer"] = None


def set_server_instance(server: "MCPServer"):
    """
    Set the global server instance.

    Args:
        server: The MCPServer instance to use globally
    """
    global _server_instance
    _server_instance = server


def get_server() -> "MCPServer":
    """
    Get the current server instance.

    Returns:
        The global MCPServer instance

    Raises:
        RuntimeError: If server instance not initialized
    """
    if _server_instance is None:
        raise RuntimeError("Server instance not initialized")
    return _server_instance
