"""
Get conversation endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..constants import ErrorMessages
from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    include_messages: bool = True,
    message_limit: int = 50,
):
    """
    Get a conversation by ID.

    Optionally includes message history.
    """
    server = get_server()

    if not server.service_container:
        raise HTTPException(
            status_code=503, detail=ErrorMessages.SERVICES_NOT_AVAILABLE
        )

    conv_service = server.service_container.conversation_service
    msg_service = server.service_container.message_service

    if not conv_service:
        raise HTTPException(
            status_code=503, detail=ErrorMessages.CONVERSATION_SERVICE_NOT_AVAILABLE
        )

    conv_result = await conv_service.get_conversation(conversation_id)

    if conv_result.is_failure():
        return JSONResponse(
            content=conv_result.to_dict(),
            status_code=conv_result.status_code,
        )

    conversation = conv_result.unwrap()

    if include_messages and msg_service:
        msg_result = await msg_service.get_messages(
            conversation_id=conversation_id,
            limit=message_limit,
            offset=0,
            include_citations=True,
        )

        if msg_result.is_success():
            messages_data = msg_result.unwrap()
            conversation["messages"] = messages_data["messages"]
            conversation["message_count"] = messages_data["total"]
        else:
            conversation["messages"] = []
            conversation["message_count"] = 0

    return {
        "success": True,
        "conversation": conversation,
    }
