"""
Create conversation endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..utils import handle_service_result, validate_conversation_service
from .models import CreateConversationRequest
from .utils import serialize_for_json

router = APIRouter()


@router.post("/")
async def create_conversation(request: CreateConversationRequest):
    """
    Create a new conversation.

    Returns the created conversation with ID.
    """
    server = get_server()
    service = validate_conversation_service(server)

    result = await service.create_conversation(
        user_id="default",
        title=request.title,
        model=request.model,
        provider_id=request.provider_id,
        context_documents=request.context_documents,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    error_response = handle_service_result(result)
    if error_response:
        return error_response

    return {
        "success": True,
        "conversation": serialize_for_json(result.unwrap()),
    }
