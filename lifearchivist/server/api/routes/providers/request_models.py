"""
Pydantic models for provider endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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
        ..., min_length=1, description="Conversation messages"
    )
    model: str = Field(..., min_length=1, description="Model identifier")
    provider_id: Optional[str] = Field(
        None, description="Provider ID (uses default if None)"
    )
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=2000, ge=1, le=100000, description="Maximum tokens to generate"
    )


class SetDefaultRequest(BaseModel):
    """Request to set default provider."""

    provider_id: str = Field(
        ..., min_length=1, description="Provider ID to set as default"
    )
    default_model: Optional[str] = Field(
        None, description="Default model to use with this provider"
    )


class UpdateProviderRequest(BaseModel):
    """Request to update provider configuration."""

    config: Optional[Dict[str, Any]] = Field(None, description="New configuration")
    set_as_default: Optional[bool] = Field(None, description="Set as default provider")
