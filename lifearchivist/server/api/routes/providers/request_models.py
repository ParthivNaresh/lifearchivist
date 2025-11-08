"""
Pydantic models for provider endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .constants import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    MAX_MAX_TOKENS,
    MAX_TEMPERATURE,
    MIN_MAX_TOKENS,
    MIN_MESSAGE_LENGTH,
    MIN_PROVIDER_ID_LENGTH,
    MIN_TEMPERATURE,
)


class AddProviderRequest(BaseModel):
    """Request to add a new provider."""

    provider_id: str = Field(..., description="Unique identifier for the provider")
    provider_type: str = Field(
        ..., description="Type of provider (ollama, openai, anthropic, google)"
    )
    config: Dict[str, Any] = Field(..., description="Provider configuration")
    set_as_default: bool = Field(default=False, description="Set as default provider")


class GenerateRequest(BaseModel):
    """Request to generate text."""

    messages: List[Dict[str, str]] = Field(
        ..., min_length=MIN_MESSAGE_LENGTH, description="Conversation messages"
    )
    model: str = Field(
        ..., min_length=MIN_MESSAGE_LENGTH, description="Model identifier"
    )
    provider_id: Optional[str] = Field(
        None, description="Provider ID (uses default if None)"
    )
    temperature: float = Field(
        default=DEFAULT_TEMPERATURE,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
        description="Sampling temperature",
    )
    max_tokens: int = Field(
        default=DEFAULT_MAX_TOKENS,
        ge=MIN_MAX_TOKENS,
        le=MAX_MAX_TOKENS,
        description="Maximum tokens to generate",
    )


class SetDefaultRequest(BaseModel):
    """Request to set default provider."""

    provider_id: str = Field(
        ...,
        min_length=MIN_PROVIDER_ID_LENGTH,
        description="Provider ID to set as default",
    )
    default_model: Optional[str] = Field(
        None, description="Default model to use with this provider"
    )


class UpdateProviderRequest(BaseModel):
    """Request to update provider configuration."""

    config: Optional[Dict[str, Any]] = Field(None, description="New configuration")
    set_as_default: Optional[bool] = Field(None, description="Set as default provider")
