"""
WebSocket message handlers.

Provides modular message handling for different WebSocket message types.
Each handler is responsible for processing a specific message type.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import WebSocket
from pydantic import ValidationError as PydanticValidationError

from .websocket.constants import (
    MESSAGE_TYPE_CONVERSATION_SUBSCRIBE,
    MESSAGE_TYPE_TOOL_EXECUTE,
)
from .websocket.message_models import (
    ConversationSubscribeMessage,
    ErrorMessage,
    ToolExecuteMessage,
    ToolResultMessage,
)

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
    error_msg = ErrorMessage(
        id=message_id,
        error=error,
        error_type=error_type,
    )
    await websocket.send_json(error_msg.model_dump(exclude_none=True))


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
    message: ToolExecuteMessage,
    server: Any,
) -> None:
    """
    Handle tool execution request.

    Args:
        websocket: WebSocket connection
        message: Validated tool execute message
        server: Server instance with execute_tool method
    """
    try:
        result = await server.execute_tool(message.tool, message.params)
        response = ToolResultMessage(
            id=message.id,
            result=result,
        )
        await websocket.send_json(response.model_dump(exclude_none=True))
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        await send_error(
            websocket,
            f"Tool execution failed: {str(e)}",
            type(e).__name__,
            message.id,
        )


async def handle_conversation_subscribe(
    websocket: WebSocket,
    message: ConversationSubscribeMessage,
    server: Any,
) -> None:
    """
    Handle conversation subscription request.

    Args:
        websocket: WebSocket connection
        message: Validated conversation subscribe message
        server: Server instance with websocket_broadcaster
    """
    try:
        if not hasattr(server, "websocket_broadcaster"):
            await send_error(
                websocket,
                "WebSocket broadcaster not available",
                "ServiceUnavailable",
                message.id,
            )
            return

        await server.websocket_broadcaster.subscribe(message.conversation_id, websocket)

        response = {
            "type": "subscription_confirmed",
            "id": message.id,
            "conversation_id": message.conversation_id,
        }
        await websocket.send_json(response)

    except Exception as e:
        logger.error(f"Conversation subscription error: {e}", exc_info=True)
        await send_error(
            websocket,
            f"Subscription failed: {str(e)}",
            type(e).__name__,
            message.id,
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

    try:
        if message_type == MESSAGE_TYPE_TOOL_EXECUTE:
            tool_message = ToolExecuteMessage(**data)
            await handle_tool_execute(websocket, tool_message, server)
        elif message_type == MESSAGE_TYPE_CONVERSATION_SUBSCRIBE:
            subscribe_message = ConversationSubscribeMessage(**data)
            await handle_conversation_subscribe(websocket, subscribe_message, server)
        else:
            await handle_unknown_message_type(websocket, message_type, message_id)
    except PydanticValidationError as e:
        logger.warning(f"Message validation error: {e}")
        await send_error(
            websocket,
            f"Invalid message format: {str(e)}",
            "ValidationError",
            message_id,
        )
