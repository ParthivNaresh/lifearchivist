"""
Update conversation endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import success_response
from ..shared.utils import handle_service_result
from .models import UpdateConversationRequest
from .utils import validate_conversation_service

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
    service, error_response = validate_conversation_service(server)
    if error_response:
        return error_response

    assert service is not None

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

    error_response = handle_service_result(result)
    if error_response:
        return error_response

    conversation = result.unwrap()

    return success_response(
        {
            "conversation": conversation,
        }
    )
