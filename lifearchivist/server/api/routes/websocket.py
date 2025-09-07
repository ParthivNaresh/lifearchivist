"""
WebSocket connection handling.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..dependencies import get_server

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time communication."""
    server = get_server()

    await server.session_manager.connect(session_id, websocket)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "tool_execute":
                result = await server.execute_tool(data["tool"], data.get("params", {}))
                await websocket.send_json(
                    {"type": "tool_result", "id": data.get("id"), "result": result}
                )

            elif data.get("type") == "agent_query":
                result = await server.query_agent_async(data["agent"], data["query"])
                await websocket.send_json(
                    {"type": "agent_result", "id": data.get("id"), "result": result}
                )

    except WebSocketDisconnect:
        server.session_manager.disconnect(session_id)
    except Exception as e:
        await websocket.close()
        server.session_manager.disconnect(session_id)
