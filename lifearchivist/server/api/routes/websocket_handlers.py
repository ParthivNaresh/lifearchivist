"""
WebSocket message handlers.

Provides modular message handling for different WebSocket message types.
Each handler is responsible for processing a specific message type.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


async def send_error(
    websocket: WebSocket,
    error: str,
    error_type: str = "Error",
    message_id: Optional[str] = None,
) -> None:
    """
    Send error message to WebSocket client.

    Args:
        websocket: WebSocket connection
        error: Error message
        error_type: Type of error
        message_id: Optional message ID for correlation
    """
    error_payload: Dict[str, Any] = {
        "type": "error",
        "error": error,
        "error_type": error_type,
    }
    if message_id is not None:
        error_payload["id"] = message_id

    await websocket.send_json(error_payload)


def validate_message_structure(data: Any) -> Optional[str]:
    """
    Validate basic message structure.

    Args:
        data: Received message data

    Returns:
        Error message if invalid, None if valid
    """
    if not isinstance(data, dict):
        return "Invalid message format. Expected JSON object."
    return None


async def handle_tool_execute(
    websocket: WebSocket,
    data: Dict[str, Any],
    server: Any,
) -> None:
    """
    Handle tool execution request.

    Args:
        websocket: WebSocket connection
        data: Message data containing tool name and parameters
        server: Server instance with execute_tool method
    """
    message_id = data.get("id")
    tool_name = data.get("tool")
    params = data.get("params", {})

    if not tool_name:
        await send_error(
            websocket,
            "Missing 'tool' field",
            "ValidationError",
            message_id,
        )
        return

    try:
        result = await server.execute_tool(tool_name, params)
        await websocket.send_json(
            {
                "type": "tool_result",
                "id": message_id,
                "result": result,
            }
        )
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        await send_error(
            websocket,
            f"Tool execution failed: {str(e)}",
            type(e).__name__,
            message_id,
        )


async def handle_agent_query(
    websocket: WebSocket,
    data: Dict[str, Any],
    server: Any,
) -> None:
    """
    Handle agent query request.

    Args:
        websocket: WebSocket connection
        data: Message data containing agent name and query
        server: Server instance with query_agent_async method
    """
    message_id = data.get("id")
    agent_name = data.get("agent")
    query = data.get("query")

    if not agent_name or not query:
        await send_error(
            websocket,
            "Missing 'agent' or 'query' field",
            "ValidationError",
            message_id,
        )
        return

    try:
        result = await server.query_agent_async(agent_name, query)
        await websocket.send_json(
            {
                "type": "agent_result",
                "id": message_id,
                "result": result,
            }
        )
    except Exception as e:
        logger.error(f"Agent query error: {e}", exc_info=True)
        await send_error(
            websocket,
            f"Agent query failed: {str(e)}",
            type(e).__name__,
            message_id,
        )


async def handle_unknown_message_type(
    websocket: WebSocket,
    message_type: Optional[str],
    message_id: Optional[str],
) -> None:
    """
    Handle unknown message type.

    Args:
        websocket: WebSocket connection
        message_type: The unknown message type
        message_id: Optional message ID for correlation
    """
    await send_error(
        websocket,
        f"Unknown message type: {message_type}",
        "ValidationError",
        message_id,
    )


async def process_websocket_message(
    websocket: WebSocket,
    data: Dict[str, Any],
    server: Any,
) -> None:
    """
    Process a single WebSocket message by routing to appropriate handler.

    Args:
        websocket: WebSocket connection
        data: Parsed message data
        server: Server instance
    """
    validation_error = validate_message_structure(data)
    if validation_error:
        await send_error(websocket, validation_error, "ValidationError")
        return

    message_type = data.get("type")
    message_id = data.get("id")

    if message_type == "tool_execute":
        await handle_tool_execute(websocket, data, server)
    elif message_type == "agent_query":
        await handle_agent_query(websocket, data, server)
    else:
        await handle_unknown_message_type(websocket, message_type, message_id)
