"""
Check provider usage endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..constants import ErrorMessages
from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/{provider_id}/usage-check")
async def check_provider_usage(provider_id: str):
    """
    Check if a provider is being used by any conversations.

    Returns the count of conversations using this provider.
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503, detail=ErrorMessages.CONVERSATION_SERVICE_NOT_AVAILABLE
        )

    try:
        db_pool = server.service_container.conversation_service.db_pool

        async with db_pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM conversations WHERE provider_id = $1 AND archived_at IS NULL",
                provider_id,
            )

            conversations = await conn.fetch(
                "SELECT id, title, model FROM conversations WHERE provider_id = $1 AND archived_at IS NULL LIMIT 5",
                provider_id,
            )

            return {
                "success": True,
                "provider_id": provider_id,
                "conversation_count": count or 0,
                "sample_conversations": (
                    [
                        {
                            "id": str(conv["id"]),
                            "title": conv["title"] or "Untitled",
                            "model": conv["model"],
                        }
                        for conv in conversations
                    ]
                    if conversations
                    else []
                ),
            }

    except Exception as e:
        import logging

        logging.error(f"Failed to check provider usage: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to check provider usage: {str(e)}"
        ) from e
