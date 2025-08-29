"""
Dependency injection for API routes.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..mcp_server import MCPServer


# Global server instance - will be set during app initialization
_server_instance: "MCPServer" = None


def set_server_instance(server: "MCPServer"):
    """Set the global server instance."""
    global _server_instance
    _server_instance = server


def get_server() -> "MCPServer":
    """Get the current server instance."""
    if _server_instance is None:
        raise RuntimeError("Server instance not initialized")
    return _server_instance
