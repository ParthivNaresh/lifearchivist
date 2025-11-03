"""
List conversations endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..constants import ErrorMessages
from ..shared.dependencies import get_server

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

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503, detail=ErrorMessages.CONVERSATION_SERVICE_NOT_AVAILABLE
        )

    service = server.service_container.conversation_service

    result = await service.list_conversations(
        user_id="default",
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )

    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )

    data = result.unwrap()

    return {
        "success": True,
        **data,
    }
