"""
Pydantic models for settings endpoints.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """Response model for settings data."""

    auto_extract_dates: bool = Field(
        default=True, description="Auto-extract dates from documents"
    )
    generate_text_previews: bool = Field(
        default=True, description="Generate text previews"
    )
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")

    llm_model: str = Field(
        default="llama3.2:1b", description="Language model for AI processing"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model for search"
    )
    search_results_limit: int = Field(
        default=25, description="Default search results limit"
    )

    temperature: float = Field(
        default=0.7, ge=0, le=2, description="Default temperature for conversations"
    )
    max_output_tokens: int = Field(
        default=2000, ge=1, le=1000000, description="Default max tokens for responses"
    )
    response_format: str = Field(
        default="concise", description="Default response format (concise/verbose)"
    )
    context_window_size: int = Field(
        default=10, ge=1, le=50, description="Number of messages to include in context"
    )
    response_timeout: int = Field(
        default=30, ge=5, le=300, description="Response timeout in seconds"
    )

    auto_organize_by_date: bool = Field(
        default=False, description="Auto-organize files by date"
    )
    duplicate_detection: bool = Field(
        default=True, description="Enable duplicate detection"
    )
    default_import_location: str = Field(
        default="~/Documents", description="Default import directory"
    )

    theme: str = Field(default="dark", description="UI theme")
    interface_density: str = Field(
        default="comfortable", description="Interface density"
    )

    vault_path: str = Field(description="Vault storage path")
    lifearch_home: str = Field(description="Life Archivist home directory")


class SettingsUpdateRequest(BaseModel):
    """Request model for updating settings."""

    auto_extract_dates: Optional[bool] = None
    generate_text_previews: Optional[bool] = None
    max_file_size_mb: Optional[int] = Field(None, ge=1, le=1000)

    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    search_results_limit: Optional[int] = Field(None, ge=1, le=1000)

    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_output_tokens: Optional[int] = Field(None, ge=1, le=1000000)
    response_format: Optional[str] = Field(None, pattern="^(concise|verbose)$")
    context_window_size: Optional[int] = Field(None, ge=1, le=50)
    response_timeout: Optional[int] = Field(None, ge=5, le=300)

    auto_organize_by_date: Optional[bool] = None
    duplicate_detection: Optional[bool] = None
    default_import_location: Optional[str] = None

    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
    interface_density: Optional[str] = Field(
        None, pattern="^(compact|comfortable|spacious)$"
    )


class AvailableModelsResponse(BaseModel):
    """Response model for available models."""

    llm_models: list[Dict[str, Any]] = Field(description="Available LLM models")
    embedding_models: list[Dict[str, Any]] = Field(
        description="Available embedding models"
    )
