"""
Update conversation endpoint.
"""

from typing import Any, Dict

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status
from pydantic import BaseModel, Field

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .models import UpdateConversationRequest

router = APIRouter()


class UpdateConversationResponse(BaseModel):
    """Response from updating a conversation."""

    conversation: Dict[str, Any] = Field(..., description="Updated conversation data")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": "conv_123",
                    "title": "Updated Title",
                    "model": "gpt-4",
                    "updated_at": "2025-01-08T14:30:00Z",
                }
            }
        }


@router.patch(
    "/{conversation_id}",
    response_model=UpdateConversationResponse,
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
                    "example": {"detail": "Update conversation failed: <error message>"}
                }
            },
        },
    },
)
async def update_conversation(
    request: UpdateConversationRequest,
    conversation_id: str = PathParam(..., description="Unique conversation identifier"),
) -> UpdateConversationResponse:
    """
    Update conversation settings and configuration.

    Allows partial updates - only provided fields will be modified. Useful for
    changing model, updating title, or adjusting conversation parameters.

    ## Path Parameters

    - **conversation_id**: Unique identifier of the conversation to update

    ## Request Body

    All fields optional - only provided fields updated:
    - **title**: Conversation title
    - **model**: Model name to use
    - **provider_id**: Provider identifier
    - **context_documents**: List of document IDs for context
    - **system_prompt**: Custom system prompt
    - **temperature**: Model temperature (0.0-2.0)
    - **max_tokens**: Maximum tokens to generate

    ## Response Fields

    - **conversation**: Updated conversation object with all current fields

    ## Example Request (Update Title)

    ```json
    {
        "title": "Updated Conversation Title"
    }
    ```

    ## Example Request (Update Model Settings)

    ```json
    {
        "model": "gpt-4-turbo",
        "temperature": 0.8,
        "max_tokens": 3000
    }
    ```

    ## Example Request (Update Context)

    ```json
    {
        "context_documents": ["doc_123", "doc_456", "doc_789"],
        "system_prompt": "You are an expert in these documents."
    }
    ```

    ## Example Response

    ```json
    {
        "conversation": {
            "id": "conv_123",
            "user_id": "default",
            "title": "Updated Conversation Title",
            "model": "gpt-4-turbo",
            "provider_id": "openai-main",
            "context_documents": ["doc_123", "doc_456", "doc_789"],
            "system_prompt": "You are an expert in these documents.",
            "temperature": 0.8,
            "max_tokens": 3000,
            "created_at": "2025-01-08T14:30:00Z",
            "updated_at": "2025-01-08T15:00:00Z",
            "archived_at": null
        }
    }
    ```

    ## Use Cases

    - Change conversation title
    - Switch to different model
    - Update context documents
    - Adjust temperature/max_tokens
    - Modify system prompt
    - Change provider

    ## Update Behavior

    - **Partial Updates**: Only provided fields modified
    - **Null Values**: Explicitly set fields to null if provided
    - **Immediate Effect**: Changes apply to next message
    - **History Preserved**: Previous messages unchanged
    - **Updated Timestamp**: updated_at field refreshed

    ## Field Updates

    - **title**: Change conversation name
    - **model**: Switch LLM model
    - **provider_id**: Change provider
    - **context_documents**: Update RAG context
    - **system_prompt**: Modify AI behavior
    - **temperature**: Adjust randomness
    - **max_tokens**: Change response length

    ## Notes

    - Returns 404 if conversation doesn't exist
    - Only provided fields are updated
    - Null values explicitly set if provided
    - Changes affect future messages only
    - Previous messages use old settings
    """
    server = get_server()

    if not server.service_container:
        raise ServiceUnavailableError("Service Container")

    if not server.service_container.conversation_service:
        raise ServiceUnavailableError("Conversation Service")

    try:
        result = (
            await server.service_container.conversation_service.update_conversation(
                conversation_id=conversation_id,
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
            error_msg = result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Conversation", conversation_id)
            raise InternalServerError("Update conversation", Exception(error_msg))

        conversation = result.unwrap()

        return UpdateConversationResponse(conversation=conversation)

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Update conversation", e) from e
