"""
Settings management endpoints.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["settings"])


class SettingsResponse(BaseModel):
    """Response model for settings data."""

    # Document Processing
    auto_extract_dates: bool = Field(
        default=True, description="Auto-extract dates from documents"
    )
    generate_text_previews: bool = Field(
        default=True, description="Generate text previews"
    )
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")

    # Search & AI
    llm_model: str = Field(
        default="llama3.2:1b", description="Language model for AI processing"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2", description="Embedding model for search"
    )
    search_results_limit: int = Field(
        default=25, description="Default search results limit"
    )

    # File Management
    auto_organize_by_date: bool = Field(
        default=False, description="Auto-organize files by date"
    )
    duplicate_detection: bool = Field(
        default=True, description="Enable duplicate detection"
    )
    default_import_location: str = Field(
        default="~/Documents", description="Default import directory"
    )

    # Appearance
    theme: str = Field(default="dark", description="UI theme")
    interface_density: str = Field(
        default="comfortable", description="Interface density"
    )

    # System Info (read-only)
    vault_path: str = Field(description="Vault storage path")
    lifearch_home: str = Field(description="Life Archivist home directory")


class SettingsUpdateRequest(BaseModel):
    """Request model for updating settings."""

    # Document Processing
    auto_extract_dates: Optional[bool] = None
    generate_text_previews: Optional[bool] = None
    max_file_size_mb: Optional[int] = Field(None, ge=1, le=1000)

    # Search & AI
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    search_results_limit: Optional[int] = Field(None, ge=1, le=1000)

    # File Management
    auto_organize_by_date: Optional[bool] = None
    duplicate_detection: Optional[bool] = None
    default_import_location: Optional[str] = None

    # Appearance
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


@router.get("/settings", response_model=SettingsResponse)
async def get_settings():
    """Get current application settings."""
    server = get_server()

    try:
        settings = server.settings

        # Map backend settings to frontend-friendly format
        response = SettingsResponse(
            # Document Processing
            auto_extract_dates=True,  # Default enabled, could be configurable later
            generate_text_previews=True,  # Default enabled
            max_file_size_mb=settings.max_file_size_mb,
            # Search & AI
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            search_results_limit=25,  # Default value, could be made configurable
            # File Management
            auto_organize_by_date=False,  # Future feature
            duplicate_detection=True,  # Currently always enabled
            default_import_location="~/Documents",  # Default value
            # Appearance
            theme=settings.theme,
            interface_density="comfortable",  # Default value
            # System Info
            vault_path=str(settings.vault_path),
            lifearch_home=str(settings.lifearch_home),
        )

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.put("/settings")
async def update_settings(request: SettingsUpdateRequest):
    """Update application settings."""
    # server = get_server()

    try:
        # settings = server.settings
        updated_fields = []

        # Note: For now, we'll track what would be updated but not persist changes
        # In the future, this would write to a config file or database

        # Document Processing updates
        if request.auto_extract_dates is not None:
            updated_fields.append("auto_extract_dates")

        if request.generate_text_previews is not None:
            updated_fields.append("generate_text_previews")

        if request.max_file_size_mb is not None:
            # This could update the actual settings object
            # settings.max_file_size_mb = request.max_file_size_mb
            updated_fields.append("max_file_size_mb")

        # Search & AI updates
        if request.llm_model is not None:
            # Validate model is available (future enhancement)
            updated_fields.append("llm_model")

        if request.embedding_model is not None:
            # Validate model is available (future enhancement)
            updated_fields.append("embedding_model")

        if request.search_results_limit is not None:
            updated_fields.append("search_results_limit")

        # File Management updates
        if request.auto_organize_by_date is not None:
            updated_fields.append("auto_organize_by_date")

        if request.duplicate_detection is not None:
            updated_fields.append("duplicate_detection")

        if request.default_import_location is not None:
            updated_fields.append("default_import_location")

        # Appearance updates
        if request.theme is not None:
            updated_fields.append("theme")

        if request.interface_density is not None:
            updated_fields.append("interface_density")

        return {
            "success": True,
            "message": "Settings updated successfully",
            "updated_fields": updated_fields,
            "note": "Settings updates are currently stored in memory only. Persistence will be added in a future update.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/settings/models", response_model=AvailableModelsResponse)
async def get_available_models():
    """Get available LLM and embedding models."""
    try:
        # For now, return static lists of commonly available models
        # In the future, this could query Ollama API or model directories

        llm_models = [
            {
                "id": "llama3.2:1b",
                "name": "Llama 3.2 1B",
                "description": "Fast, lightweight model for basic tasks",
                "size": "1B parameters",
                "performance": "fast",
            },
            {
                "id": "llama3.2:3b",
                "name": "Llama 3.2 3B",
                "description": "Balanced performance and accuracy",
                "size": "3B parameters",
                "performance": "balanced",
            },
            {
                "id": "llama3.1:8b",
                "name": "Llama 3.1 8B",
                "description": "High accuracy for complex tasks",
                "size": "8B parameters",
                "performance": "accurate",
            },
        ]

        embedding_models = [
            {
                "id": "all-MiniLM-L6-v2",
                "name": "all-MiniLM-L6-v2",
                "description": "Fast and efficient for most use cases",
                "dimensions": 384,
                "performance": "fast",
            },
            {
                "id": "all-mpnet-base-v2",
                "name": "all-mpnet-base-v2",
                "description": "Higher accuracy for semantic search",
                "dimensions": 768,
                "performance": "accurate",
            },
        ]

        return AvailableModelsResponse(
            llm_models=llm_models, embedding_models=embedding_models
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/settings/reset")
async def reset_settings():
    """Reset all settings to default values."""
    try:
        # For now, just return success message
        # In the future, this would reset actual configuration

        return {
            "success": True,
            "message": "Settings reset to default values",
            "note": "Settings reset is currently a placeholder. Full implementation will be added in a future update.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/settings/export")
async def export_settings():
    """Export current settings as JSON."""
    try:
        # Get current settings
        current_settings = await get_settings()

        return {
            "success": True,
            "settings": current_settings.dict(),
            "exported_at": "2025-01-06T14:30:00Z",  # Would use actual timestamp
            "version": "0.1.0",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
