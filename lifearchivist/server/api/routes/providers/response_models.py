"""
Response models for provider endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..shared.constants import SUCCESS_MESSAGE
from .misc_models import (
    ConversationSample,
    CostInfo,
    ModelInfo,
    ProviderInfo,
    UsageInfo,
    WorkspaceInfo,
)


class AddProviderResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the added provider")
    provider_type: str = Field(
        ..., description="Provider type (openai, anthropic, ollama, etc)"
    )
    is_default: bool = Field(..., description="Whether this is the default provider")
    message: str = Field(..., description=SUCCESS_MESSAGE)

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "my-openai",
                "provider_type": "openai",
                "is_default": True,
                "message": "Provider added successfully",
            }
        }


class DeleteProviderResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the deleted provider")
    message: str = Field(..., description=SUCCESS_MESSAGE)
    affected_conversations: int = Field(
        ..., description="Number of conversations that were affected"
    )
    conversations_updated: bool = Field(
        ..., description="Whether conversations were updated to use fallback provider"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "openai-backup",
                "message": "Provider deleted successfully",
                "affected_conversations": 5,
                "conversations_updated": True,
            }
        }


class GetProviderResponse(BaseModel):
    provider_id: str = Field(..., description="Unique provider identifier")
    provider_type: str = Field(
        ..., description="Provider type (openai, anthropic, ollama, etc)"
    )
    is_default: bool = Field(..., description="Whether this is the default provider")
    is_initialized: bool = Field(
        ..., description="Whether provider has been initialized"
    )
    is_healthy: bool = Field(..., description="Current health status")
    user_id: str = Field(..., description="User ID associated with this provider")

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "openai-main",
                "provider_type": "openai",
                "is_default": True,
                "is_initialized": True,
                "is_healthy": True,
                "user_id": "default",
            }
        }


class GenerateResponse(BaseModel):
    content: str = Field(..., description="Generated text response")
    model: str = Field(..., description="Model identifier used for generation")
    provider: str = Field(..., description="Provider type that generated the response")
    tokens_used: Optional[int] = Field(
        None, description="Total tokens consumed (prompt + completion)"
    )
    prompt_tokens: Optional[int] = Field(None, description="Tokens in the prompt")
    completion_tokens: Optional[int] = Field(
        None, description="Tokens in the completion"
    )
    cost_usd: Optional[float] = Field(None, description="Estimated cost in USD")
    finish_reason: Optional[str] = Field(
        None, description="Reason generation stopped (stop, length, error, etc)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional provider-specific response data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": "The capital of France is Paris.",
                "model": "gpt-4o-mini",
                "provider": "openai",
                "tokens_used": 25,
                "prompt_tokens": 15,
                "completion_tokens": 10,
                "cost_usd": 0.000125,
                "finish_reason": "stop",
                "metadata": {},
            }
        }


class ListModelsResponse(BaseModel):
    provider_id: str = Field(..., description="Provider identifier")
    models: List[ModelInfo] = Field(..., description="List of available models")
    total: int = Field(..., description="Total number of models")

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "openai-main",
                "models": [
                    {
                        "id": "gpt-4o",
                        "name": "GPT-4o",
                        "provider": "openai",
                        "provider_id": "openai-main",
                        "context_window": 128000,
                        "max_output_tokens": 4096,
                        "supports_streaming": True,
                        "supports_functions": True,
                        "supports_vision": True,
                        "cost_per_1k_input": 0.005,
                        "cost_per_1k_output": 0.015,
                        "metadata": {},
                    }
                ],
                "total": 1,
            }
        }


class ListProvidersResponse(BaseModel):
    providers: List[ProviderInfo] = Field(
        ..., description="List of registered providers"
    )
    total: int = Field(..., description="Total number of providers")

    class Config:
        json_schema_extra = {
            "example": {
                "providers": [
                    {
                        "id": "openai-main",
                        "type": "openai",
                        "name": "OpenAI",
                        "is_default": True,
                        "is_healthy": True,
                        "is_admin": False,
                    },
                    {
                        "id": "anthropic-backup",
                        "type": "anthropic",
                        "name": "Anthropic",
                        "is_default": False,
                        "is_healthy": True,
                        "is_admin": False,
                    },
                ],
                "total": 2,
            }
        }


class SetDefaultResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the new default provider")
    default_model: Optional[str] = Field(
        None, description="Default model that was set (if provided)"
    )
    message: str = Field(..., description=SUCCESS_MESSAGE)

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "my-openai",
                "default_model": "gpt-4o-mini",
                "message": "Default provider updated",
            }
        }


class TestProviderResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the tested provider")
    is_valid: bool = Field(
        ..., description="Whether credentials are valid and provider is reachable"
    )
    message: str = Field(..., description="Test result message")

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "my-openai",
                "is_valid": True,
                "message": "Credentials valid",
            }
        }


class UpdateProviderResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the updated provider")
    message: str = Field(..., description=SUCCESS_MESSAGE)
    config_updated: bool = Field(..., description="Whether configuration was updated")
    default_updated: bool = Field(..., description="Whether default status was updated")

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "my-openai",
                "message": "Provider updated successfully",
                "config_updated": True,
                "default_updated": False,
            }
        }


class UsageCheckResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the checked provider")
    conversation_count: int = Field(
        ..., description="Number of active conversations using this provider"
    )
    sample_conversations: List[ConversationSample] = Field(
        ..., description="Sample of conversations using this provider (max 5)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "my-openai",
                "conversation_count": 12,
                "sample_conversations": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "title": "My conversation",
                        "model": "gpt-4o-mini",
                    }
                ],
            }
        }


class ProviderMetadataResponse(BaseModel):
    provider_id: str = Field(..., description="Provider identifier")
    capabilities: Optional[List[str]] = Field(
        None, description="Provider capabilities (if requested)"
    )
    workspaces: Optional[List[WorkspaceInfo]] = Field(
        None, description="Provider workspaces (if requested)"
    )
    usage: Optional[UsageInfo] = Field(
        None, description="Usage information (if requested)"
    )
    costs: Optional[CostInfo] = Field(
        None, description="Cost information (if requested)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "anthropic-work",
                "capabilities": ["workspaces", "usage_tracking", "cost_tracking"],
                "workspaces": [
                    {
                        "id": "ws-123",
                        "name": "My Workspace",
                        "is_default": True,
                        "metadata": {},
                    }
                ],
                "usage": None,
                "costs": None,
            }
        }
