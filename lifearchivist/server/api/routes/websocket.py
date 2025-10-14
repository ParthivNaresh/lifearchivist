"""
WebSocket connection handling for real-time communication.

Provides bidirectional communication for:
- Tool execution with progress updates
- Agent queries and responses
- Real-time status updates
- File upload progress tracking
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..dependencies import get_server

router = APIRouter(tags=["websocket"])

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

    # Validate session_id
    if not session_id or len(session_id) < 3:
        await websocket.close(code=1008, reason="Invalid session_id")
        return

    try:
        # Accept connection and register with session manager
        await server.session_manager.connect(session_id, websocket)
        logger.info(f"WebSocket connected: session_id={session_id}")

        # Message processing loop
        while True:
            try:
                # Receive and parse message
                data = await websocket.receive_json()

                # Validate message structure
                if not isinstance(data, dict):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "error": "Invalid message format. Expected JSON object.",
                            "error_type": "ValidationError",
                        }
                    )
                    continue

                message_type = data.get("type")
                message_id = data.get("id")

                # Handle tool execution
                if message_type == "tool_execute":
                    tool_name = data.get("tool")
                    params = data.get("params", {})

                    if not tool_name:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "id": message_id,
                                "error": "Missing 'tool' field",
                                "error_type": "ValidationError",
                            }
                        )
                        continue

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
                        await websocket.send_json(
                            {
                                "type": "error",
                                "id": message_id,
                                "error": f"Tool execution failed: {str(e)}",
                                "error_type": type(e).__name__,
                            }
                        )

                # Handle agent query
                elif message_type == "agent_query":
                    agent_name = data.get("agent")
                    query = data.get("query")

                    if not agent_name or not query:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "id": message_id,
                                "error": "Missing 'agent' or 'query' field",
                                "error_type": "ValidationError",
                            }
                        )
                        continue

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
                        await websocket.send_json(
                            {
                                "type": "error",
                                "id": message_id,
                                "error": f"Agent query failed: {str(e)}",
                                "error_type": type(e).__name__,
                            }
                        )

                # Handle unknown message types
                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "id": message_id,
                            "error": f"Unknown message type: {message_type}",
                            "error_type": "ValidationError",
                        }
                    )

            except ValueError as e:
                # JSON parsing error
                logger.warning(f"Invalid JSON received: {e}")
                await websocket.send_json(
                    {
                        "type": "error",
                        "error": f"Invalid JSON: {str(e)}",
                        "error_type": "JSONDecodeError",
                    }
                )

    except WebSocketDisconnect:
        # Normal disconnection
        logger.info(f"WebSocket disconnected: session_id={session_id}")
        server.session_manager.disconnect(session_id)

    except Exception as e:
        # Unexpected error - close connection
        logger.error(f"WebSocket error for session {session_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass  # Connection may already be closed
        finally:
            server.session_manager.disconnect(session_id)
