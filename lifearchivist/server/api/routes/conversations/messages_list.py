"""
Get messages endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

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

    if not server.service_container or not server.service_container.message_service:
        raise HTTPException(status_code=503, detail="Message service not available")

    service = server.service_container.message_service

    result = await service.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
        include_citations=include_citations,
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
