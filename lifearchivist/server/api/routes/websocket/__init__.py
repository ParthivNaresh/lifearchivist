"""
WebSocket connection handling for real-time communication.

Provides bidirectional communication for:
- Tool execution with progress updates
- Agent queries and responses
- Real-time status updates
- File upload progress tracking
"""

from fastapi import APIRouter

from . import connection

router = APIRouter(tags=["websocket"])

router.include_router(connection.router)

__all__ = ["router"]
