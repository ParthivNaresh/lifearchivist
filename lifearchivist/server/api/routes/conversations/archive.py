"""
Archive conversation endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..constants import ErrorMessages
from ..shared.dependencies import get_server

router = APIRouter()


@router.delete("/{conversation_id}")
async def archive_conversation(conversation_id: str):
    """
    Archive (soft delete) a conversation.

    Archived conversations can be restored by updating archived_at to null.
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503, detail=ErrorMessages.CONVERSATION_SERVICE_NOT_AVAILABLE
        )

    service = server.service_container.conversation_service

    result = await service.archive_conversation(conversation_id)

    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )

    conversation = result.unwrap()

    return {
        "success": True,
        "conversation": conversation,
        "message": "Conversation archived successfully",
    }
