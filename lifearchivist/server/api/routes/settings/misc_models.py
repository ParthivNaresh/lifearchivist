"""
Miscellaneous models for settings endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class LLMModel(BaseModel):
    """LLM model information."""

    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Model description")
    provider: str = Field(..., description="Provider type")
    provider_id: str = Field(..., description="Provider instance ID")
    context_window: int = Field(..., description="Maximum context tokens")
    supports_streaming: bool = Field(..., description="Streaming support")
    cost_per_1k_input: Optional[float] = Field(
        None, description="Cost per 1K input tokens"
    )
    cost_per_1k_output: Optional[float] = Field(
        None, description="Cost per 1K output tokens"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "gpt-4",
                "name": "GPT-4",
                "description": "OPENAI model",
                "provider": "openai",
                "provider_id": "openai-main",
                "context_window": 8192,
                "supports_streaming": True,
                "cost_per_1k_input": 0.03,
                "cost_per_1k_output": 0.06,
            }
        }


class EmbeddingModel(BaseModel):
    """Embedding model information."""

    id: str = Field(..., description="Model identifier")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Model description")
    dimensions: int = Field(..., description="Embedding vector dimensions")
    performance: str = Field(..., description="Performance characteristic")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "all-MiniLM-L6-v2",
                "name": "all-MiniLM-L6-v2",
                "description": "Fast and efficient for most use cases",
                "dimensions": 384,
                "performance": "fast",
            }
        }
