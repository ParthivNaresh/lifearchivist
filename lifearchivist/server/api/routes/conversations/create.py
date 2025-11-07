"""
Create conversation endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .request_models import CreateConversationRequest
from .response_models import CreateConversationResponse
from .utils import serialize_for_json

router = APIRouter()


@router.post(
    "/",
    response_model=CreateConversationResponse,
    status_code=status.HTTP_201_CREATED,
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
                    "example": {"detail": "Create conversation failed: <error message>"}
                }
            },
        },
    },
)
async def create_conversation(
    request: CreateConversationRequest,
) -> CreateConversationResponse:
    """
    Create a new conversation.

    Initializes a new conversation with specified model, provider, and configuration.
    Returns the created conversation with generated ID.

    ## Request Body

    - **title**: Conversation title (optional)
    - **model**: Model name to use (e.g., "gpt-4", "claude-3")
    - **provider_id**: Provider identifier (e.g., "openai-main")
    - **context_documents**: List of document IDs for context (optional)
    - **system_prompt**: Custom system prompt (optional)
    - **temperature**: Model temperature 0.0-2.0 (optional)
    - **max_tokens**: Maximum tokens to generate (optional)

    ## Response Fields

    - **conversation**: Created conversation object containing:
      - id: Unique conversation identifier
      - title: Conversation title
      - model: Model name
      - provider_id: Provider identifier
      - created_at: Creation timestamp
      - updated_at: Last update timestamp
      - All other configuration fields

    ## Example Request

    ```json
    {
        "title": "Research Discussion",
        "model": "gpt-4",
        "provider_id": "openai-main",
        "context_documents": ["doc_123", "doc_456"],
        "system_prompt": "You are a helpful research assistant.",
        "temperature": 0.7,
        "max_tokens": 2000
    }
    ```

    ## Example Response

    ```json
    {
        "conversation": {
            "id": "conv_123",
            "user_id": "default",
            "title": "Research Discussion",
            "model": "gpt-4",
            "provider_id": "openai-main",
            "context_documents": ["doc_123", "doc_456"],
            "system_prompt": "You are a helpful research assistant.",
            "temperature": 0.7,
            "max_tokens": 2000,
            "created_at": "2025-01-08T14:30:00Z",
            "updated_at": "2025-01-08T14:30:00Z",
            "archived_at": null
        }
    }
    ```

    ## Use Cases

    - Start new chat session
    - Create conversation with document context
    - Initialize conversation with custom settings
    - Set up conversation with specific model
    - Begin research discussion

    ## Configuration Options

    - **context_documents**: Provide document context for RAG
    - **system_prompt**: Customize AI behavior
    - **temperature**: Control response randomness
    - **max_tokens**: Limit response length

    ## Notes

    - Returns 201 Created on success
    - Conversation ID auto-generated
    - User ID defaults to "default"
    - All fields except model/provider optional
    - Conversation starts with no messages
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise ServiceUnavailableError("Conversation service")

    try:
        result = (
            await server.service_container.conversation_service.create_conversation(
                user_id="default",
                title=request.title,
                model=request.model,
                provider_id=request.provider_id,
                context_documents=request.context_documents,
                system_prompt=request.system_prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        )

        if result.is_failure():
            raise InternalServerError("Create conversation", Exception(result.error))

        conversation = result.unwrap()

        return CreateConversationResponse(conversation=serialize_for_json(conversation))

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Create conversation", e) from e
