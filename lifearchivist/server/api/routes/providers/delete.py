"""
Delete provider endpoint.
"""

from fastapi import APIRouter, Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .response_models import DeleteProviderResponse
from .utils import determine_fallback_provider, update_conversations_provider

router = APIRouter()


@router.delete(
    "/{provider_id}",
    response_model=DeleteProviderResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Provider not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Provider not found: invalid-provider"}
                }
            },
        },
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {"example": {"detail": "LLM manager not available"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Delete provider failed: <error message>"}
                }
            },
        },
    },
)
async def delete_provider(
    provider_id: str,
    update_conversations: bool = Query(
        default=False,
        description="Update affected conversations to use fallback provider",
    ),
) -> DeleteProviderResponse:
    """
    Delete a provider and clean up all associated resources.

    Removes provider from manager, cleans up resources, deletes stored credentials,
    and optionally migrates affected conversations to a fallback provider.

    ## Path Parameters

    - **provider_id**: Unique provider identifier to delete

    ## Query Parameters

    - **update_conversations**: Whether to update affected conversations (default: false)
      - If true, conversations using this provider will be migrated to fallback
      - Fallback priority: current default → ollama-default
      - Returns count of affected conversations

    ## Response Fields

    - **provider_id**: ID of the deleted provider
    - **message**: Success confirmation message
    - **affected_conversations**: Number of conversations that were using this provider
    - **conversations_updated**: Whether conversations were migrated to fallback

    ## Deletion Process

    1. **Optional**: Determine fallback provider and migrate conversations
    2. Remove provider from LLM manager (cleans up resources)
    3. Delete encrypted credentials from storage
    4. Return deletion summary

    ## Example Response

    ```json
    {
        "provider_id": "openai-backup",
        "message": "Provider deleted successfully",
        "affected_conversations": 5,
        "conversations_updated": true
    }
    ```

    ## Notes

    - Cannot delete a provider that doesn't exist (404)
    - Conversations are only updated if `update_conversations=true`
    - If no conversations exist, `affected_conversations` will be 0
    - Fallback provider is automatically determined (default or ollama)
    - All resources are cleaned up (connections, sessions, etc.)
    - Credentials are permanently deleted from secure storage
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM Manager")

    if not server.credential_service:
        raise ServiceUnavailableError("Credential Service")

    if not server.service_container:
        raise ServiceUnavailableError("Service Container")

    if not server.service_container.conversation_service:
        raise ServiceUnavailableError("Conversation Service")

    if not server.service_container.conversation_service.db_pool:
        raise ServiceUnavailableError("Database Pool")

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

            db_pool = server.service_container.conversation_service.db_pool
            affected_conversations = await update_conversations_provider(
                db_pool,
                provider_id,
                fallback_provider_id,
                fallback_model,
            )

        remove_result = await server.llm_manager.remove_provider(provider_id)

        if remove_result.is_failure():
            error = remove_result.error_or("Unknown error")
            error_type = remove_result.error_type
            status_code = remove_result.status_code

            if status_code == 404 or error_type == "ProviderNotFound":
                raise ResourceNotFoundError("Provider", provider_id)
            else:
                raise InternalServerError(
                    "Remove provider", Exception(f"{error_type}: {error}")
                )

        delete_result = await server.credential_service.delete_provider(provider_id)

        if delete_result.is_failure():
            error = delete_result.error_or("Unknown error")
            error_type = delete_result.error_type
            status_code = delete_result.status_code

            if status_code == 404 or error_type == "NotFoundError":
                raise ResourceNotFoundError("Provider credentials", provider_id)
            else:
                raise InternalServerError(
                    "Delete credentials", Exception(f"{error_type}: {error}")
                )

        return DeleteProviderResponse(
            provider_id=provider_id,
            message="Provider deleted successfully",
            affected_conversations=affected_conversations,
            conversations_updated=update_conversations and affected_conversations > 0,
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Delete provider", e) from e
