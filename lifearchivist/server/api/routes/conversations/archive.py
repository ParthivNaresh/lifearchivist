"""
Archive conversation endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .response_models import ArchiveConversationResponse

router = APIRouter()


@router.delete(
    "/{conversation_id}",
    response_model=ArchiveConversationResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Conversation not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Conversation not found: invalid-id"}
                }
            },
        },
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
                    "example": {
                        "detail": "Archive conversation failed: <error message>"
                    }
                }
            },
        },
    },
)
async def archive_conversation(
    conversation_id: str = PathParam(..., description="Unique conversation identifier"),
) -> ArchiveConversationResponse:
    """
    Archive a conversation (soft delete).

    Marks conversation as archived without permanently deleting it. Archived
    conversations can be restored by updating archived_at to null.

    ## Path Parameters

    - **conversation_id**: Unique identifier of the conversation to archive

    ## Response Fields

    - **conversation**: Archived conversation object with updated archived_at timestamp
    - **message**: Success confirmation message

    ## Example Response

    ```json
    {
        "conversation": {
            "id": "conv_123",
            "title": "My Conversation",
            "archived_at": "2025-01-08T14:30:00Z",
            "created_at": "2025-01-01T10:00:00Z",
            "updated_at": "2025-01-08T14:30:00Z"
        },
        "message": "Conversation archived successfully"
    }
    ```

    ## Archive Behavior

    - **Soft Delete**: Conversation not permanently removed
    - **Restorable**: Can be unarchived later
    - **Timestamp**: Sets archived_at to current time
    - **Preserved**: All messages and metadata kept
    - **Hidden**: Excluded from default conversation lists

    ## Use Cases

    - Clean up conversation list
    - Hide old conversations
    - Organize conversation history
    - Temporary removal
    - Declutter interface

    ## Restoration

    To restore an archived conversation:
    - Update archived_at field to null
    - Use conversation update endpoint
    - Conversation becomes visible again

    ## Notes

    - Returns 404 if conversation doesn't exist
    - Idempotent (safe to archive multiple times)
    - Messages remain intact
    - Can be searched if needed
    - Metadata preserved
    """
    server = get_server()

    if not server.service_container:
        raise ServiceUnavailableError("Service Container")

    if not server.service_container.conversation_service:
        raise ServiceUnavailableError("Conversation service")

    try:
        result = (
            await server.service_container.conversation_service.archive_conversation(
                conversation_id
            )
        )

        if result.is_failure():
            error_msg = result.unwrap_error().message
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Conversation", conversation_id)
            raise InternalServerError("Archive conversation", Exception(error_msg))

        conversation_dict = result.unwrap()

        from .misc_models import Conversation

        conversation = Conversation(**conversation_dict)

        return ArchiveConversationResponse(
            conversation=conversation,
            message="Conversation archived successfully",
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Archive conversation", e) from e
