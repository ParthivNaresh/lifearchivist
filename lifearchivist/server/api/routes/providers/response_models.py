"""
Response models for provider endpoints.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProviderInfo(BaseModel):
    id: str = Field(..., description="Unique provider identifier")
    type: str = Field(..., description="Provider type (openai, anthropic, ollama, etc)")
    name: str = Field(..., description="Human-readable provider name")
    is_default: bool = Field(..., description="Whether this is the default provider")
    is_healthy: bool = Field(..., description="Provider health status")
    is_admin: bool = Field(
        ..., description="Whether this provider uses an admin/organization key"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "openai-main",
                "type": "openai",
                "name": "OpenAI",
                "is_default": True,
                "is_healthy": True,
                "is_admin": False,
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


class ModelInfo(BaseModel):
    id: str = Field(..., description="Unique model identifier (e.g., 'gpt-4o')")
    name: str = Field(..., description="Human-readable model name")
    provider: str = Field(
        ..., description="Provider type (e.g., 'openai', 'anthropic')"
    )
    provider_id: str = Field(
        ..., description="Specific provider instance ID (e.g., 'work-openai')"
    )
    context_window: int = Field(
        ..., description="Maximum context window size in tokens"
    )
    max_output_tokens: int = Field(..., description="Maximum output tokens")
    supports_streaming: bool = Field(..., description="Whether streaming is supported")
    supports_functions: bool = Field(
        ..., description="Whether function calling is supported"
    )
    supports_vision: bool = Field(
        ..., description="Whether vision/image inputs are supported"
    )
    cost_per_1k_input: Optional[float] = Field(
        None, description="Cost per 1K input tokens in USD"
    )
    cost_per_1k_output: Optional[float] = Field(
        None, description="Cost per 1K output tokens in USD"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional model-specific information"
    )

    class Config:
        json_schema_extra = {
            "example": {
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


class DeleteProviderResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the deleted provider")
    message: str = Field(..., description="Success message")
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


class AddProviderResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the added provider")
    provider_type: str = Field(
        ..., description="Provider type (openai, anthropic, ollama, etc)"
    )
    is_default: bool = Field(..., description="Whether this is the default provider")
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "my-openai",
                "provider_type": "openai",
                "is_default": True,
                "message": "Provider added successfully",
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
    message: str = Field(..., description="Success message")
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


class ConversationSample(BaseModel):
    id: str = Field(..., description="Conversation ID")
    title: str = Field(..., description="Conversation title")
    model: str = Field(..., description="Model used in conversation")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "My conversation",
                "model": "gpt-4o-mini",
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


class SetDefaultResponse(BaseModel):
    provider_id: str = Field(..., description="ID of the new default provider")
    default_model: Optional[str] = Field(
        None, description="Default model that was set (if provided)"
    )
    message: str = Field(..., description="Success message")

    class Config:
        json_schema_extra = {
            "example": {
                "provider_id": "my-openai",
                "default_model": "gpt-4o-mini",
                "message": "Default provider updated",
            }
        }


class WorkspaceInfo(BaseModel):
    id: str = Field(..., description="Workspace ID")
    name: str = Field(..., description="Workspace name")
    is_default: bool = Field(..., description="Whether this is the default workspace")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional workspace metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "ws-123",
                "name": "My Workspace",
                "is_default": True,
                "metadata": {},
            }
        }


class UsageInfo(BaseModel):
    start_time: str = Field(..., description="Start time (ISO 8601)")
    end_time: str = Field(..., description="End time (ISO 8601)")
    total_tokens: int = Field(..., description="Total tokens used")
    input_tokens: int = Field(..., description="Input tokens used")
    output_tokens: int = Field(..., description="Output tokens used")
    cached_tokens: Optional[int] = Field(None, description="Cached tokens used")
    requests_count: int = Field(..., description="Number of requests made")
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional usage metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-08T00:00:00Z",
                "total_tokens": 50000,
                "input_tokens": 30000,
                "output_tokens": 20000,
                "cached_tokens": 5000,
                "requests_count": 150,
                "metadata": {},
            }
        }


class CostInfo(BaseModel):
    start_time: str = Field(..., description="Start time (ISO 8601)")
    end_time: str = Field(..., description="End time (ISO 8601)")
    total_cost_usd: float = Field(..., description="Total cost in USD")
    currency: str = Field(..., description="Currency code")
    breakdown: Optional[Dict[str, Any]] = Field(
        None, description="Cost breakdown by model/feature"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional cost metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "start_time": "2025-01-01T00:00:00Z",
                "end_time": "2025-01-08T00:00:00Z",
                "total_cost_usd": 12.50,
                "currency": "USD",
                "breakdown": {"gpt-4o": 10.0, "gpt-4o-mini": 2.5},
                "metadata": {},
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
