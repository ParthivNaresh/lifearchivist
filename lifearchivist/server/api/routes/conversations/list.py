"""
List conversations endpoint.
"""

from fastapi import APIRouter, Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .response_models import ListConversationsResponse

router = APIRouter()

MIN_LIMIT = 1
MAX_LIMIT = 100
DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0


@router.get(
    "/",
    response_model=ListConversationsResponse,
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
                    "example": {"detail": "List conversations failed: <error message>"}
                }
            },
        },
    },
)
async def list_conversations(
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description="Maximum conversations to return",
    ),
    offset: int = Query(
        default=DEFAULT_OFFSET, ge=0, description="Number of conversations to skip"
    ),
    include_archived: bool = Query(
        default=False, description="Include archived conversations"
    ),
) -> ListConversationsResponse:
    """
    List conversations for the current user with pagination.

    Returns conversations ordered by most recent activity. Supports filtering
    archived conversations and pagination for large conversation lists.

    ## Query Parameters

    - **limit**: Maximum conversations to return (1-100, default: 50)
    - **offset**: Number of conversations to skip (default: 0)
    - **include_archived**: Include archived conversations (default: false)

    ## Response Fields

    - **conversations**: Array of conversation objects
    - **total**: Total number of conversations returned
    - **limit**: Applied limit
    - **offset**: Applied offset

    ## Example Response

    ```json
    {
        "conversations": [
            {
                "id": "conv_123",
                "title": "Research Discussion",
                "model": "gpt-4",
                "provider_id": "openai-main",
                "created_at": "2025-01-08T14:30:00Z",
                "updated_at": "2025-01-08T15:00:00Z",
                "archived_at": null
            },
            {
                "id": "conv_456",
                "title": "Code Review",
                "model": "claude-3",
                "provider_id": "anthropic-main",
                "created_at": "2025-01-07T10:00:00Z",
                "updated_at": "2025-01-07T11:30:00Z",
                "archived_at": null
            }
        ],
        "total": 2,
        "limit": 50,
        "offset": 0
    }
    ```

    ## Use Cases

    - Display conversation list in UI
    - Browse conversation history
    - Paginate through conversations
    - Filter archived conversations
    - Load recent conversations

    ## Filtering

    - **include_archived=false**: Only active conversations (default)
    - **include_archived=true**: Both active and archived conversations

    ## Pagination

    Use limit and offset for pagination:
    - First page: `?limit=50&offset=0`
    - Second page: `?limit=50&offset=50`
    - Third page: `?limit=50&offset=100`

    ## Ordering

    - Conversations ordered by most recent activity
    - Updated conversations appear first
    - Newly created conversations at top

    ## Performance Notes

    - Fast query with indexed fields
    - Limit enforced for performance
    - Efficient pagination
    - Suitable for frequent polling

    ## Notes

    - Empty array if no conversations found
    - Limit enforced: 1-100 per request
    - Offset must be non-negative
    - User ID defaults to "default"
    - Total reflects filtered count
    """
    server = get_server()

    if not server.service_container:
        raise ServiceUnavailableError("Service Container")

    if not server.service_container.conversation_service:
        raise ServiceUnavailableError("Conversation Service")

    try:
        result = await server.service_container.conversation_service.list_conversations(
            user_id="default",
            limit=limit,
            offset=offset,
            include_archived=include_archived,
        )

        if result.is_failure():
            raise InternalServerError("List conversations", Exception(result.error))

        data = result.unwrap()

        return ListConversationsResponse(**data)

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("List conversations", e) from e
