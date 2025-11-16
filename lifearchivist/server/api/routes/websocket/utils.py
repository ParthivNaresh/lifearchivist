"""
Utility functions for WebSocket endpoints.
"""

import logging
from typing import Any

from fastapi import WebSocket

from ..websocket_handlers import process_websocket_message, send_error
from .constants import (
    CLOSE_CODE_INVALID_SESSION,
    CLOSE_CODE_SERVICE_UNAVAILABLE,
    MIN_SESSION_ID_LENGTH,
)

logger = logging.getLogger(__name__)


def validate_session_id(session_id: str) -> bool:
    """
    Validate session ID format.

    Args:
        session_id: Session identifier to validate

    Returns:
        True if valid, False otherwise
    """
    return bool(session_id and len(session_id) >= MIN_SESSION_ID_LENGTH)


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
        await websocket.close(
            code=CLOSE_CODE_INVALID_SESSION, reason="Invalid session_id"
        )
        return False

    if server.session_manager is None:
        await websocket.close(
            code=CLOSE_CODE_SERVICE_UNAVAILABLE,
            reason="Session manager not available",
        )
        logger.error("WebSocket connection rejected: session manager not initialized")
        return False

    await websocket.accept()
    server.session_manager.connect(session_id, websocket)
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


def cleanup_connection(session_id: str, server: Any, websocket: WebSocket) -> None:
    """
    Clean up WebSocket connection resources.

    Args:
        session_id: Session identifier
        server: Server instance
        websocket: WebSocket connection
    """
    if server.session_manager is not None:
        server.session_manager.disconnect(session_id)

    if (
        hasattr(server, "websocket_broadcaster")
        and server.websocket_broadcaster is not None
    ):
        server.websocket_broadcaster.unsubscribe_all(websocket)
