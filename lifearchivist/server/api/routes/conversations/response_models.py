"""
Pydantic models for conversation endpoints.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ArchiveConversationResponse(BaseModel):
    """Response from archiving a conversation."""

    conversation: Dict[str, Any] = Field(..., description="Archived conversation data")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": "conv_123",
                    "title": "Archived Conversation",
                    "archived_at": "2025-01-08T14:30:00Z",
                },
                "message": "Conversation archived successfully",
            }
        }


class CreateConversationResponse(BaseModel):
    """Response from creating a conversation."""

    conversation: Dict[str, Any] = Field(..., description="Created conversation data")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": "conv_123",
                    "title": "New Conversation",
                    "model": "gpt-4",
                    "provider_id": "openai-main",
                    "created_at": "2025-01-08T14:30:00Z",
                }
            }
        }


class GetConversationResponse(BaseModel):
    """Response from getting a conversation."""

    conversation: Dict[str, Any] = Field(..., description="Conversation data")

    class Config:
        json_schema_extra = {
            "example": {
                "conversation": {
                    "id": "conv_123",
                    "title": "My Conversation",
                    "model": "gpt-4",
                    "messages": [],
                    "message_count": 0,
                }
            }
        }


class ListConversationsResponse(BaseModel):
    """Response from listing conversations."""

    conversations: List[Dict[str, Any]] = Field(
        ..., description="List of conversations"
    )
    total: int = Field(..., description="Total number of conversations")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")

    class Config:
        json_schema_extra = {
            "example": {
                "conversations": [
                    {
                        "id": "conv_123",
                        "title": "My Conversation",
                        "model": "gpt-4",
                        "created_at": "2025-01-08T14:30:00Z",
                    }
                ],
                "total": 1,
                "limit": 50,
                "offset": 0,
            }
        }


class MessagesListResponse(BaseModel):
    """Response from getting messages."""

    messages: List[Dict[str, Any]] = Field(..., description="List of messages")
    total: int = Field(..., description="Total number of messages")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "id": "msg_1",
                        "role": "user",
                        "content": "Hello",
                        "created_at": "2025-01-08T14:30:00Z",
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
    user_message: Dict[str, Any] = Field(..., description="User message data")
    assistant_message: Dict[str, Any] = Field(
        ..., description="Assistant response data"
    )
    latency_ms: int = Field(..., description="Response latency in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "user_message": {
                    "id": "msg_1",
                    "role": "user",
                    "content": "What is this about?",
                },
                "assistant_message": {
                    "id": "msg_2",
                    "role": "assistant",
                    "content": "Based on the documents...",
                    "citations": [],
                },
                "latency_ms": 1500,
            }
        }


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
