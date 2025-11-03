"""
Delete provider endpoint.
"""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from ..utils import determine_fallback_provider, update_conversations_provider

router = APIRouter()


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: str,
    update_conversations: bool = Query(
        default=False,
        description="Update affected conversations to use default provider",
    ),
):
    """
    Delete a provider.

    Removes from manager, cleans up resources, and deletes stored credentials.
    Optionally updates affected conversations to use the default provider.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    if not server.credential_service:
        raise HTTPException(status_code=503, detail="Credential service not available")

    try:
        affected_conversations = 0

        should_update = (
            update_conversations
            and server.service_container
            and server.service_container.conversation_service
        )

        if should_update:
            fallback_provider_id, fallback_model = await determine_fallback_provider(
                server.llm_manager, provider_id
            )

            db_pool = server.service_container.conversation_service.db_pool  # type: ignore[union-attr]
            affected_conversations = await update_conversations_provider(
                db_pool,
                provider_id,
                fallback_provider_id,
                fallback_model,
            )

        remove_result = await server.llm_manager.remove_provider(provider_id)

        if remove_result.is_failure():
            return JSONResponse(
                content=remove_result.to_dict(),
                status_code=remove_result.status_code,
            )

        delete_result = await server.credential_service.delete_provider(provider_id)

        if delete_result.is_failure():
            return JSONResponse(
                content=delete_result.to_dict(),
                status_code=delete_result.status_code,
            )

        return {
            "success": True,
            "provider_id": provider_id,
            "message": "Provider deleted successfully",
            "affected_conversations": affected_conversations,
            "conversations_updated": update_conversations
            and affected_conversations > 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
