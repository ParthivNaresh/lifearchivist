"""
WebSocket connection endpoint.
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..shared.dependencies import get_server
from .constants import CLOSE_CODE_INTERNAL_ERROR
from .utils import cleanup_connection, handle_connection_setup, handle_message_loop

router = APIRouter()
logger = logging.getLogger(__name__)


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
        cleanup_connection(session_id, server, websocket)

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            await websocket.close(
                code=CLOSE_CODE_INTERNAL_ERROR, reason="Internal server error"
            )
        except Exception:
            pass
        finally:
            cleanup_connection(session_id, server, websocket)
