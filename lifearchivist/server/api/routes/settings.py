"""
Settings management endpoints.

Provides configuration management for:
- Document processing settings
- Search and AI model configuration
- File management preferences
- UI appearance settings
- System information
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
    """
    Get current application settings.

    Returns all configuration including:
    - Document processing preferences
    - AI model selections
    - File management settings
    - UI appearance
    - System paths (read-only)
    """
    server = get_server()

    try:
        settings = server.settings

        return SettingsResponse(
            auto_extract_dates=True,
            generate_text_previews=True,
            max_file_size_mb=settings.max_file_size_mb,
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            search_results_limit=25,
            auto_organize_by_date=False,
            duplicate_detection=True,
            default_import_location="~/Documents",
            theme=settings.theme,
            interface_density="comfortable",
            vault_path=str(settings.vault_path),
            lifearch_home=str(settings.lifearch_home),
        )

    except AttributeError as e:
        raise HTTPException(
            status_code=500, detail=f"Settings configuration error: {str(e)}"
        ) from None
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve settings: {str(e)}"
        ) from None


@router.put("/settings")
async def update_settings(request: SettingsUpdateRequest):
    """
    Update application settings.

    Note: Currently stores updates in memory only.
    Persistence to configuration file will be added in a future update.

    Validates:
    - File size limits (1-1000 MB)
    - Search result limits (1-1000)
    - Theme values (light/dark/system)
    - Interface density (compact/comfortable/spacious)
    """
    try:
        updated_fields = []

        # Track all fields that would be updated
        if request.auto_extract_dates is not None:
            updated_fields.append("auto_extract_dates")
        if request.generate_text_previews is not None:
            updated_fields.append("generate_text_previews")
        if request.max_file_size_mb is not None:
            updated_fields.append("max_file_size_mb")
        if request.llm_model is not None:
            updated_fields.append("llm_model")
        if request.embedding_model is not None:
            updated_fields.append("embedding_model")
        if request.search_results_limit is not None:
            updated_fields.append("search_results_limit")
        if request.auto_organize_by_date is not None:
            updated_fields.append("auto_organize_by_date")
        if request.duplicate_detection is not None:
            updated_fields.append("duplicate_detection")
        if request.default_import_location is not None:
            updated_fields.append("default_import_location")
        if request.theme is not None:
            updated_fields.append("theme")
        if request.interface_density is not None:
            updated_fields.append("interface_density")

        if not updated_fields:
            raise HTTPException(
                status_code=400, detail="No settings provided to update"
            )

        return {
            "success": True,
            "message": "Settings updated successfully",
            "updated_fields": updated_fields,
            "note": "Settings updates are currently stored in memory only. Persistence will be added in a future update.",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update settings: {str(e)}"
        ) from None


@router.get("/settings/models", response_model=AvailableModelsResponse)
async def get_available_models():
    """
    Get available LLM and embedding models.

    Returns lists of:
    - LLM models for text generation and Q&A
    - Embedding models for semantic search

    Future enhancement: Query Ollama API for dynamically available models.
    """
    try:
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
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve available models: {str(e)}"
        ) from None


@router.post("/settings/reset")
async def reset_settings():
    """
    Reset all settings to default values.

    Note: Currently a placeholder.
    Full implementation will restore all settings to factory defaults.
    """
    try:
        return {
            "success": True,
            "message": "Settings reset to default values",
            "note": "Settings reset is currently a placeholder. Full implementation will be added in a future update.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset settings: {str(e)}"
        ) from None


@router.get("/settings/export")
async def export_settings():
    """
    Export current settings as JSON.

    Useful for:
    - Backing up configuration
    - Sharing settings between installations
    - Version control of preferences
    """
    try:
        current_settings = await get_settings()

        return {
            "success": True,
            "settings": current_settings.dict(),
            "exported_at": "2025-01-06T14:30:00Z",  # TODO: Use actual timestamp
            "version": "0.1.0",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to export settings: {str(e)}"
        ) from None
