"""
Get messages endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import success_response
from ..shared.utils import handle_service_result
from .utils import validate_message_service

router = APIRouter()


@router.get("/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    include_citations: bool = True,
):
    """
    Get message history for a conversation.

    Returns paginated messages with optional citations.
    """
    server = get_server()
    service, error_response = validate_message_service(server)
    if error_response:
        return error_response

    assert service is not None

    result = await service.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
        include_citations=include_citations,
    )

    error_response = handle_service_result(result)
    if error_response:
        return error_response

    data = result.unwrap()

    return success_response(data)
