"""
Miscellaneous models for conversation endpoints.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..shared.constants import CREATION_TIMESTAMP_LABEL
from .request_models import SendMessageRequest


class Citation(BaseModel):
    """
    Document citation model matching message_citations table.
    """

    id: UUID = Field(..., description="Citation identifier")
    message_id: UUID = Field(..., description="Parent message identifier")
    document_id: str = Field(..., description="Source document identifier")
    chunk_id: Optional[str] = Field(None, description="Specific chunk identifier")
    score: Optional[float] = Field(None, description="Relevance score (0-1)")
    snippet: Optional[str] = Field(None, description="Text excerpt from document")
    position: Optional[int] = Field(None, description="Position in citation list")
    created_at: datetime = Field(..., description=CREATION_TIMESTAMP_LABEL)

    class Config:
        json_schema_extra: Dict[str, Any] = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "message_id": "660e8400-e29b-41d4-a716-446655440000",
                "document_id": "doc_123",
                "chunk_id": "chunk_1",
                "score": 0.85,
                "snippet": "Relevant text from document...",
                "position": 0,
                "created_at": "2025-01-08T14:30:00Z",
            }
        }


class Message(BaseModel):
    """
    Conversation message model matching messages table.
    """

    id: UUID = Field(..., description="Unique message identifier")
    conversation_id: UUID = Field(..., description="Parent conversation identifier")
    parent_message_id: Optional[UUID] = Field(
        None, description="Parent message for threading"
    )
    sequence_number: int = Field(..., description="Order within conversation")
    role: str = Field(..., description="Message role (user/assistant/system)")
    content: str = Field(..., description="Message content")
    model: Optional[str] = Field(None, description="Model used for generation")
    confidence: Optional[float] = Field(None, description="Confidence score (0-1)")
    method: Optional[str] = Field(None, description="Generation method")
    tokens_used: Optional[int] = Field(None, description="Token count")
    latency_ms: Optional[int] = Field(None, description="Generation latency")
    created_at: datetime = Field(..., description=CREATION_TIMESTAMP_LABEL)
    edited_at: Optional[datetime] = Field(None, description="Edit timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    citations: Optional[List[Citation]] = Field(None, description="Document citations")

    class Config:
        json_schema_extra: Dict[str, Any] = {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440000",
                "conversation_id": "770e8400-e29b-41d4-a716-446655440000",
                "parent_message_id": None,
                "sequence_number": 0,
                "role": "assistant",
                "content": "Based on the documents...",
                "model": "gpt-4",
                "confidence": 0.8,
                "method": "rag_with_provider",
                "tokens_used": 150,
                "latency_ms": 1500,
                "created_at": "2025-01-08T14:30:01Z",
                "edited_at": None,
                "metadata": {},
                "citations": [],
            }
        }


class Conversation(BaseModel):
    """
    Conversation model matching conversations table.
    """

    id: UUID = Field(..., description="Unique conversation identifier")
    user_id: str = Field(..., description="Owner user identifier")
    title: Optional[str] = Field(None, description="Conversation title")
    model: str = Field(..., description="LLM model name")
    provider_id: Optional[str] = Field(None, description="LLM provider identifier")
    context_documents: Optional[List[str]] = Field(
        None, description="Document IDs for context"
    )
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    temperature: float = Field(..., description="Model temperature")
    max_tokens: int = Field(..., description="Maximum tokens")
    created_at: datetime = Field(..., description=CREATION_TIMESTAMP_LABEL)
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_message_at: Optional[datetime] = Field(
        None, description="Last message timestamp"
    )
    archived_at: Optional[datetime] = Field(None, description="Archive timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    messages: Optional[List[Message]] = Field(None, description="Message history")
    message_count: Optional[int] = Field(None, description="Total message count")

    class Config:
        json_schema_extra: Dict[str, Any] = {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440000",
                "user_id": "default",
                "title": "Research Discussion",
                "model": "gpt-4",
                "provider_id": "openai-main",
                "context_documents": ["doc_123"],
                "system_prompt": "You are a helpful assistant.",
                "temperature": 0.7,
                "max_tokens": 2000,
                "created_at": "2025-01-08T14:30:02Z",
                "updated_at": "2025-01-08T14:30:03Z",
                "last_message_at": None,
                "archived_at": None,
                "metadata": {},
            }
        }


@dataclass
class MessageContext:
    """Context for message processing."""

    conversation_id: str
    conversation: Dict[str, Any]
    user_content: str
    context_limit: int
    start_time: float


@dataclass
class SearchContext:
    """Search results and sources."""

    sources: List[Dict[str, Any]]
    context_text: Optional[str]


@dataclass
class LLMConfig:
    """LLM configuration parameters."""

    provider_id: Optional[str]
    model: str
    temperature: float
    max_tokens: int
    system_prompt: str
    response_format: Optional[str]


class EventType(Enum):
    """SSE event types."""

    USER_MESSAGE = "user_message"
    ASSISTANT_MESSAGE_CREATED = "assistant_message_created"
    INTENT = "intent"
    CONTEXT = "context"
    SOURCES = "sources"
    CHUNK = "chunk"
    METADATA = "metadata"
    COMPLETE = "complete"
    ERROR = "error"
    AGENT_PROGRESS = "agent_progress"


@dataclass
class StreamContext:
    """Context for streaming operations."""

    conversation_id: str
    request: SendMessageRequest
    start_time: float
    conversation: Optional[Dict[str, Any]] = None
    provider_id: Optional[str] = None
    model: Optional[str] = None
    user_message: Optional[Dict[str, Any]] = None
    sources: Optional[List[Dict[str, Any]]] = None
    accumulated_text: Optional[str] = None

    def __post_init__(self) -> None:
        if self.sources is None:
            self.sources = []


@dataclass
class StreamConfig:
    """Configuration for streaming."""

    temperature: float = 0.7
    max_tokens: int = 2000
    response_timeout: int = 30
    context_window_size: int = 10
    response_format: Optional[str] = None
    system_prompt: str = (
        "You are a helpful assistant that answers questions based on the provided context."
    )


@dataclass
class StreamMetadata:
    """Metadata for streaming response."""

    confidence_score: float
    method: str
    model: str
    provider_id: Optional[str]
    tokens_used: int
    finish_reason: Optional[str]
    latency_ms: int
