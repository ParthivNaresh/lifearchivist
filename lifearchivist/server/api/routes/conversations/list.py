"""
List conversations endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import success_response
from ..shared.utils import handle_service_result
from .utils import validate_conversation_service

router = APIRouter()


@router.get("/")
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    include_archived: bool = False,
):
    """
    List conversations for the current user.

    Supports pagination and filtering.
    """
    server = get_server()
    service, error_response = validate_conversation_service(server)
    if error_response:
        return error_response

    assert service is not None

    result = await service.list_conversations(
        user_id="default",
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )

    error_response = handle_service_result(result)
    if error_response:
        return error_response

    data = result.unwrap()

    return success_response(data)
