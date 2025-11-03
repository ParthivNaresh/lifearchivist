"""
Update conversation endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..constants import ErrorMessages
from ..shared.dependencies import get_server
from .models import UpdateConversationRequest

router = APIRouter()


@router.patch("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
):
    """
    Update a conversation's settings.

    Only provided fields will be updated.
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

    result = await service.update_conversation(
        conversation_id=conversation_id,
        title=request.title,
        model=request.model,
        provider_id=request.provider_id,
        context_documents=request.context_documents,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )

    conversation = result.unwrap()

    return {
        "success": True,
        "conversation": conversation,
    }
