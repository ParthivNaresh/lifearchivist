"""
Response models for conversation endpoints.
"""

from typing import List

from pydantic import BaseModel, Field

from ..shared.constants import CREATION_TIMESTAMP_EXAMPLE
from .misc_models import Conversation, Message


class ArchiveConversationResponse(BaseModel):
    """Response from archiving a conversation."""

    conversation: Conversation = Field(..., description="Archived conversation data")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "user_id": "default",
                    "title": "Archived Conversation",
                    "model": "gpt-4",
                    "provider_id": "openai-main",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "created_at": CREATION_TIMESTAMP_EXAMPLE,
                    "updated_at": CREATION_TIMESTAMP_EXAMPLE,
                    "archived_at": CREATION_TIMESTAMP_EXAMPLE,
                },
                "message": "Conversation archived successfully",
            }
        }


class CreateConversationResponse(BaseModel):
    """Response from creating a conversation."""

    conversation: Conversation = Field(..., description="Created conversation data")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "user_id": "default",
                    "title": "New Conversation",
                    "model": "gpt-4",
                    "provider_id": "openai-main",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "created_at": CREATION_TIMESTAMP_EXAMPLE,
                    "updated_at": CREATION_TIMESTAMP_EXAMPLE,
                }
            }
        }


class GetConversationResponse(BaseModel):
    """Response from getting a conversation."""

    conversation: Conversation = Field(..., description="Conversation data")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "user_id": "default",
                    "title": "My Conversation",
                    "model": "gpt-4",
                    "provider_id": "openai-main",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "created_at": CREATION_TIMESTAMP_EXAMPLE,
                    "updated_at": CREATION_TIMESTAMP_EXAMPLE,
                    "messages": [],
                    "message_count": 0,
                }
            }
        }


class ListConversationsResponse(BaseModel):
    """Response from listing conversations."""

    conversations: List[Conversation] = Field(..., description="List of conversations")
    total: int = Field(..., description="Total number of conversations")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")
    has_more: bool = Field(..., description="Whether more results exist")

    class Config:
        json_schema_extra = {
            "example": {
                "conversations": [
                    {
                        "id": "770e8400-e29b-41d4-a716-446655440000",
                        "user_id": "default",
                        "title": "My Conversation",
                        "model": "gpt-4",
                        "provider_id": "openai-main",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "created_at": CREATION_TIMESTAMP_EXAMPLE,
                        "updated_at": CREATION_TIMESTAMP_EXAMPLE,
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
                "has_more": False,
            }
        }


class MessagesListResponse(BaseModel):
    """Response from getting messages."""

    messages: List[Message] = Field(..., description="List of messages")
    total: int = Field(..., description="Total number of messages")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "id": "660e8400-e29b-41d4-a716-446655440000",
                        "conversation_id": "770e8400-e29b-41d4-a716-446655440000",
                        "sequence_number": 0,
                        "role": "user",
                        "content": "Hello",
                        "created_at": CREATION_TIMESTAMP_EXAMPLE,
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            }
        }


class SendMessageResponse(BaseModel):
    """Response from sending a message."""

    success: bool = Field(
        default=True, description="Whether message was sent successfully"
    )
    user_message: Message = Field(..., description="User message data")
    assistant_message: Message = Field(..., description="Assistant response data")
    latency_ms: int = Field(..., description="Response latency in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "user_message": {
                    "id": "660e8400-e29b-41d4-a716-446655440000",
                    "conversation_id": "770e8400-e29b-41d4-a716-446655440000",
                    "sequence_number": 0,
                    "role": "user",
                    "content": "What is this about?",
                    "created_at": "2025-01-08T14:30:00Z",
                },
                "assistant_message": {
                    "id": "660e8400-e29b-41d4-a716-446655440001",
                    "conversation_id": "770e8400-e29b-41d4-a716-446655440000",
                    "sequence_number": 1,
                    "role": "assistant",
                    "content": "Based on the documents...",
                    "model": "gpt-4",
                    "confidence": 0.8,
                    "method": "rag_with_provider",
                    "latency_ms": 1500,
                    "created_at": "2025-01-08T14:30:02Z",
                    "citations": [],
                },
                "latency_ms": 1500,
            }
        }


class UpdateConversationResponse(BaseModel):
    """Response from updating a conversation."""

    conversation: Conversation = Field(..., description="Updated conversation data")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": "770e8400-e29b-41d4-a716-446655440000",
                    "user_id": "default",
                    "title": "Updated Title",
                    "model": "gpt-4",
                    "provider_id": "openai-main",
                    "temperature": 0.7,
                    "max_tokens": 2000,
                    "created_at": "2025-01-08T14:30:00Z",
                    "updated_at": "2025-01-08T15:00:00Z",
                }
            }
        }
