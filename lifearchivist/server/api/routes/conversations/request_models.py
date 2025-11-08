from typing import List, Optional

from pydantic import BaseModel, Field

from .constants import (
    DEFAULT_CONTEXT_LIMIT,
    MAX_CONTEXT_LIMIT,
    MAX_MAX_TOKENS,
    MAX_TEMPERATURE,
    MIN_CONTEXT_LIMIT,
    MIN_MAX_TOKENS,
    MIN_TEMPERATURE,
)


class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation."""

    title: Optional[str] = Field(None, description="Conversation title")
    model: Optional[str] = Field(
        None, description="LLM model to use (defaults to current settings)"
    )
    provider_id: Optional[str] = Field(
        None, description="LLM provider ID (e.g., 'my-openai'). NULL = use default"
    )
    context_documents: Optional[List[str]] = Field(
        None, description="Document IDs for context"
    )
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    temperature: Optional[float] = Field(
        None,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
        description="LLM temperature (uses user preferences if None)",
    )
    max_tokens: Optional[int] = Field(
        None,
        ge=MIN_MAX_TOKENS,
        le=MAX_MAX_TOKENS,
        description="Max tokens per response (uses user preferences if None)",
    )


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""

    content: str = Field(..., description="Message content (user question)")
    context_limit: int = Field(
        default=DEFAULT_CONTEXT_LIMIT,
        ge=MIN_CONTEXT_LIMIT,
        le=MAX_CONTEXT_LIMIT,
        description="Number of context documents to use",
    )


class UpdateConversationRequest(BaseModel):
    """Request model for updating a conversation."""

    title: Optional[str] = Field(None, description="New title")
    model: Optional[str] = Field(None, description="New model")
    provider_id: Optional[str] = Field(None, description="New provider ID")
    context_documents: Optional[List[str]] = Field(
        None, description="New context documents"
    )
    system_prompt: Optional[str] = Field(None, description="New system prompt")
    temperature: Optional[float] = Field(
        None,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
        description="New temperature",
    )
    max_tokens: Optional[int] = Field(
        None, ge=MIN_MAX_TOKENS, le=MAX_MAX_TOKENS, description="New max tokens"
    )
