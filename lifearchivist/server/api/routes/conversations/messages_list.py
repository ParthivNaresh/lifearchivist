"""
Get messages endpoint.
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
from .constants import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    MAX_MESSAGE_LIMIT,
    MIN_MESSAGE_LIMIT,
)
from .response_models import MessagesListResponse

router = APIRouter()


@router.get(
    "/{conversation_id}/messages",
    response_model=MessagesListResponse,
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
            "description": "Message service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Message service not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Get messages failed: <error message>"}
                }
            },
        },
    },
)
async def get_messages(
    conversation_id: str = PathParam(..., description="Unique conversation identifier"),
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=MIN_MESSAGE_LIMIT,
        le=MAX_MESSAGE_LIMIT,
        description="Maximum messages to return",
    ),
    offset: int = Query(
        default=DEFAULT_OFFSET, ge=0, description="Number of messages to skip"
    ),
    include_citations: bool = Query(
        default=True, description="Include document citations in messages"
    ),
) -> MessagesListResponse:
    """
    Get message history for a conversation with pagination.

    Returns messages ordered chronologically with optional document citations.
    Useful for loading conversation history in UI.

    ## Path Parameters

    - **conversation_id**: Unique identifier of the conversation

    ## Query Parameters

    - **limit**: Maximum messages to return (1-500, default: 50)
    - **offset**: Number of messages to skip (default: 0)
    - **include_citations**: Include document citations (default: true)

    ## Response Fields

    - **messages**: Array of message objects
    - **total**: Total number of messages returned
    - **limit**: Applied limit
    - **offset**: Applied offset

    ## Example Response (With Citations)

    ```json
    {
        "messages": [
            {
                "id": "msg_1",
                "conversation_id": "conv_123",
                "role": "user",
                "content": "What does the document say?",
                "created_at": "2025-01-08T14:30:00Z"
            },
            {
                "id": "msg_2",
                "conversation_id": "conv_123",
                "role": "assistant",
                "content": "According to the document...",
                "created_at": "2025-01-08T14:30:05Z",
                "citations": [
                    {
                        "document_id": "doc_123",
                        "title": "Source Document.pdf",
                        "excerpt": "Relevant text..."
                    }
                ]
            }
        ],
        "total": 2,
        "limit": 50,
        "offset": 0
    }
    ```

    ## Example Response (Without Citations)

    ```json
    {
        "messages": [
            {
                "id": "msg_1",
                "role": "user",
                "content": "Hello",
                "created_at": "2025-01-08T14:30:00Z"
            },
            {
                "id": "msg_2",
                "role": "assistant",
                "content": "Hi there!",
                "created_at": "2025-01-08T14:30:05Z"
            }
        ],
        "total": 2,
        "limit": 50,
        "offset": 0
    }
    ```

    ## Use Cases

    - Load conversation history
    - Display message thread
    - Paginate through messages
    - Show document citations
    - Export conversation

    ## Message Roles

    - **user**: Messages from the user
    - **assistant**: AI-generated responses
    - **system**: System messages (rare)

    ## Citations

    - **include_citations=true**: Full citation objects included
    - **include_citations=false**: Citations omitted for performance
    - Citations show source documents used
    - Includes document excerpts

    ## Pagination

    Use limit and offset for pagination:
    - First page: `?limit=50&offset=0`
    - Second page: `?limit=50&offset=50`
    - Third page: `?limit=50&offset=100`

    ## Ordering

    - Messages ordered chronologically (oldest first)
    - Maintains conversation flow
    - Newest messages at end

    ## Performance Notes

    - Fast query with indexed fields
    - Citations add minimal overhead
    - Efficient pagination
    - Suitable for real-time updates

    ## Notes

    - Returns 404 if conversation doesn't exist
    - Empty array if no messages found
    - Limit enforced: 1-500 per request
    - Offset must be non-negative
    - Total reflects actual message count
    """
    server = get_server()

    if not server.service_container or not server.service_container.message_service:
        raise ServiceUnavailableError("Message service")

    try:
        result = await server.service_container.message_service.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset,
            include_citations=include_citations,
        )

        if result.is_failure():
            error_msg = result.unwrap_error().message
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Conversation", conversation_id)
            raise InternalServerError("Get messages", Exception(error_msg))

        data = result.unwrap()

        from .misc_models import Citation, Message

        messages = []
        for msg_dict in data["messages"]:
            if msg_dict.get("citations"):
                msg_dict["citations"] = [
                    Citation(**cit) for cit in msg_dict["citations"]
                ]
            messages.append(Message(**msg_dict))

        return MessagesListResponse(
            messages=messages,
            total=data["total"],
            limit=data["limit"],
            offset=data["offset"],
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Get messages", e) from e
