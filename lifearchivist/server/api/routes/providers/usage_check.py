"""
Check provider usage endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .misc_models import ConversationSample
from .response_models import UsageCheckResponse

router = APIRouter()


@router.get(
    "/{provider_id}/usage-check",
    response_model=UsageCheckResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "Conversation service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Conversation service not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Check usage failed: <error message>"}
                }
            },
        },
    },
)
async def check_provider_usage(provider_id: str) -> UsageCheckResponse:
    """
    Check if a provider is being used by any active conversations.

    Returns the count of conversations using this provider and a sample of up to 5 conversations.
    Useful for determining if a provider can be safely deleted.

    ## Path Parameters

    - **provider_id**: Unique provider identifier to check

    ## Response Fields

    - **provider_id**: ID of the checked provider
    - **conversation_count**: Number of active conversations using this provider
    - **sample_conversations**: Sample of conversations (max 5) with ID, title, and model

    ## Use Cases

    - Check if provider is in use before deletion
    - Identify which conversations would be affected by provider removal
    - Audit provider usage across conversations
    - Determine migration impact

    ## Example Response (Provider in Use)

    ```json
    {
        "provider_id": "my-openai",
        "conversation_count": 12,
        "sample_conversations": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "My conversation",
                "model": "gpt-4o-mini"
            },
            {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "title": "Another chat",
                "model": "gpt-4o"
            }
        ]
    }
    ```

    ## Example Response (Provider Not in Use)

    ```json
    {
        "provider_id": "unused-provider",
        "conversation_count": 0,
        "sample_conversations": []
    }
    ```

    ## Notes

    - Only counts active (non-archived) conversations
    - Returns up to 5 sample conversations for preview
    - Provider doesn't need to exist to check usage
    - Useful before deleting a provider to see impact
    - Empty sample list means provider is safe to delete
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise ServiceUnavailableError("Conversation service")

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

            sample_conversations = [
                ConversationSample(
                    id=str(conv["id"]),
                    title=conv["title"] or "Untitled",
                    model=conv["model"],
                )
                for conv in conversations
            ]

            return UsageCheckResponse(
                provider_id=provider_id,
                conversation_count=count or 0,
                sample_conversations=sample_conversations,
            )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        import logging

        logging.error(f"Failed to check provider usage: {e}", exc_info=True)
        raise InternalServerError("Check provider usage", e) from e
