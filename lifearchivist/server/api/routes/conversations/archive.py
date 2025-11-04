"""
Archive conversation endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import success_response
from ..shared.utils import handle_service_result
from .utils import validate_conversation_service

router = APIRouter()


@router.delete("/{conversation_id}")
async def archive_conversation(conversation_id: str):
    """
    Archive (soft delete) a conversation.

    Archived conversations can be restored by updating archived_at to null.
    """
    server = get_server()
    service, error_response = validate_conversation_service(server)
    if error_response:
        return error_response

    assert service is not None

    result = await service.archive_conversation(conversation_id)

    error_response = handle_service_result(result)
    if error_response:
        return error_response

    conversation = result.unwrap()

    return success_response(
        {
            "conversation": conversation,
            "message": "Conversation archived successfully",
        }
    )
