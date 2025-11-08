"""
Get conversation endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .constants import DEFAULT_MESSAGE_LIMIT, MAX_MESSAGE_LIMIT, MIN_MESSAGE_LIMIT
from .response_models import GetConversationResponse

router = APIRouter()


@router.get(
    "/{conversation_id}",
    response_model=GetConversationResponse,
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
                    "example": {"detail": "Get conversation failed: <error message>"}
                }
            },
        },
    },
)
async def get_conversation(
    conversation_id: str = PathParam(..., description="Unique conversation identifier"),
    include_messages: bool = Query(
        default=True, description="Include message history in response"
    ),
    message_limit: int = Query(
        default=DEFAULT_MESSAGE_LIMIT,
        ge=MIN_MESSAGE_LIMIT,
        le=MAX_MESSAGE_LIMIT,
        description="Maximum messages to include",
    ),
) -> GetConversationResponse:
    """
    Get a conversation by ID with optional message history.

    Retrieves conversation details and optionally includes recent messages.
    Useful for loading conversation state in UI.

    ## Path Parameters

    - **conversation_id**: Unique identifier of the conversation

    ## Query Parameters

    - **include_messages**: Include message history (default: true)
    - **message_limit**: Max messages to include (1-500, default: 50)

    ## Response Fields

    - **conversation**: Conversation object containing:
      - id: Conversation identifier
      - title: Conversation title
      - model: Model name
      - provider_id: Provider identifier
      - messages: Array of messages (if include_messages=true)
      - message_count: Total message count (if include_messages=true)
      - All other conversation fields

    ## Example Response (With Messages)

    ```json
    {
        "conversation": {
            "id": "conv_123",
            "title": "Research Discussion",
            "model": "gpt-4",
            "provider_id": "openai-main",
            "created_at": "2025-01-08T14:30:00Z",
            "messages": [
                {
                    "id": "msg_1",
                    "role": "user",
                    "content": "Hello",
                    "created_at": "2025-01-08T14:31:00Z"
                },
                {
                    "id": "msg_2",
                    "role": "assistant",
                    "content": "Hi there!",
                    "created_at": "2025-01-08T14:31:05Z"
                }
            ],
            "message_count": 2
        }
    }
    ```

    ## Example Response (Without Messages)

    ```json
    {
        "conversation": {
            "id": "conv_123",
            "title": "Research Discussion",
            "model": "gpt-4",
            "provider_id": "openai-main",
            "created_at": "2025-01-08T14:30:00Z"
        }
    }
    ```

    ## Use Cases

    - Load conversation in UI
    - Resume conversation session
    - View conversation details
    - Check conversation configuration
    - Display conversation history

    ## Message Loading

    - **include_messages=true**: Loads recent messages
    - **include_messages=false**: Conversation metadata only
    - **message_limit**: Controls how many messages loaded
    - Messages ordered by creation time (newest first)
    - Includes citations if available

    ## Performance Notes

    - Fast for metadata-only requests
    - Message loading adds overhead
    - Limit messages for better performance
    - Messages cached when possible

    ## Notes

    - Returns 404 if conversation doesn't exist
    - Message limit enforced: 1-500
    - Empty messages array if none exist
    - Citations included in messages
    - Archived conversations still accessible
    """
    server = get_server()

    if not server.service_container:
        raise ServiceUnavailableError("Service Container")

    if not server.service_container.conversation_service:
        raise ServiceUnavailableError("Conversation service")

    try:
        conv_result = (
            await server.service_container.conversation_service.get_conversation(
                conversation_id
            )
        )

        if conv_result.is_failure():
            error_msg = conv_result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Conversation", conversation_id)
            raise InternalServerError("Get conversation", Exception(error_msg))

        conversation_dict = conv_result.unwrap()

        if include_messages and server.service_container:
            msg_service = server.service_container.message_service
            if msg_service:
                msg_result = await msg_service.get_messages(
                    conversation_id=conversation_id,
                    limit=message_limit,
                    offset=0,
                    include_citations=True,
                )

                if msg_result.is_success():
                    messages_data = msg_result.unwrap()
                    conversation_dict["messages"] = messages_data.get("messages", [])
                    conversation_dict["message_count"] = messages_data.get("total", 0)
                else:
                    conversation_dict["messages"] = []
                    conversation_dict["message_count"] = 0
            else:
                conversation_dict["messages"] = []
                conversation_dict["message_count"] = 0

        from .misc_models import Conversation, Message

        if conversation_dict.get("messages"):
            conversation_dict["messages"] = [
                Message(**msg) for msg in conversation_dict["messages"]
            ]

        conversation = Conversation(**conversation_dict)

        return GetConversationResponse(conversation=conversation)

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Get conversation", e) from e
