"""
WebSocket connection handling for real-time communication.

Provides bidirectional communication for:
- Tool execution with progress updates
- Agent queries and responses
- Real-time status updates
- File upload progress tracking
"""

import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..dependencies import get_server
from .websocket_handlers import process_websocket_message, send_error

router = APIRouter(tags=["websocket"])

logger = logging.getLogger(__name__)


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format.

    Args:
        session_id: Session identifier to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(session_id and len(session_id) >= 3)


async def handle_connection_setup(
    websocket: WebSocket,
    session_id: str,
    server: Any,
) -> bool:
    """
    Handle WebSocket connection setup and validation.

    Args:
        websocket: WebSocket connection
        session_id: Session identifier
        server: Server instance

    Returns:
        True if setup successful, False if connection should be rejected
    """
    if not validate_session_id(session_id):
        await websocket.close(code=1008, reason="Invalid session_id")
        return False

    if server.session_manager is None:
        await websocket.close(code=1011, reason="Session manager not available")
        logger.error("WebSocket connection rejected: session manager not initialized")
        return False

    await server.session_manager.connect(session_id, websocket)
    logger.info(f"WebSocket connected: session_id={session_id}")
    return True


async def handle_message_loop(
    websocket: WebSocket,
    server: Any,
) -> None:
    """
    Process incoming WebSocket messages in a loop.

    Args:
        websocket: WebSocket connection
        server: Server instance
    """
    while True:
        try:
            data = await websocket.receive_json()
            await process_websocket_message(websocket, data, server)
        except ValueError as e:
            logger.warning(f"Invalid JSON received: {e}")
            await send_error(
                websocket,
                f"Invalid JSON: {str(e)}",
                "JSONDecodeError",
            )


def cleanup_connection(session_id: str, server: Any) -> None:
    """
    Clean up WebSocket connection resources.

    Args:
        session_id: Session identifier
        server: Server instance
    """
    if server.session_manager is not None:
        server.session_manager.disconnect(session_id)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time bidirectional communication.

    Args:
        websocket: WebSocket connection instance
        session_id: Unique session identifier for tracking

    Supported message types:

    1. tool_execute:
       Request: {"type": "tool_execute", "id": "...", "tool": "...", "params": {...}}
       Response: {"type": "tool_result", "id": "...", "result": {...}}

    2. agent_query:
       Request: {"type": "agent_query", "id": "...", "agent": "...", "query": "..."}
       Response: {"type": "agent_result", "id": "...", "result": {...}}

    Connection lifecycle:
    - Accepts connection and registers with session manager
    - Processes messages in continuous loop
    - Handles disconnection and cleanup
    - Sends error messages for invalid requests
    """
    server = get_server()

    if not await handle_connection_setup(websocket, session_id, server):
        return

    try:
        await handle_message_loop(websocket, server)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session_id={session_id}")
        cleanup_connection(session_id, server)

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
        finally:
            cleanup_connection(session_id, server)
