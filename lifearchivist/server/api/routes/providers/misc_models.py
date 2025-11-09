from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


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
