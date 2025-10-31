"""
Settings management endpoints.

Provides configuration management for:
- Document processing settings
- Search and AI model configuration
- File management preferences
- UI appearance settings
- System information
"""

from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from lifearchivist.config import get_settings as get_app_settings

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

    # Conversation Defaults
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

    # Conversation Defaults
    temperature: Optional[float] = Field(None, ge=0, le=2)
    max_output_tokens: Optional[int] = Field(None, ge=1, le=1000000)
    response_format: Optional[str] = Field(None, pattern="^(concise|verbose)$")
    context_window_size: Optional[int] = Field(None, ge=1, le=50)
    response_timeout: Optional[int] = Field(None, ge=5, le=300)

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
    - Conversation defaults
    - File management settings
    - UI appearance
    - System paths (read-only)
    """
    server = get_server()

    try:
        settings = server.settings

        # Get user preferences from database
        temperature = 0.7
        max_output_tokens = 2000
        response_format = "concise"
        context_window_size = 10
        response_timeout = 30

        if server.service_container and server.service_container.conversation_service:
            db_pool = server.service_container.conversation_service.db_pool

            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO user_preferences (user_id)
                    VALUES ('default')
                    ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
                    RETURNING temperature, max_output_tokens, response_format, 
                              context_window_size, response_timeout
                    """
                )

                if row:
                    temperature = row["temperature"]
                    max_output_tokens = row["max_output_tokens"]
                    response_format = row["response_format"]
                    context_window_size = row["context_window_size"]
                    response_timeout = row["response_timeout"]

        return SettingsResponse(
            auto_extract_dates=True,
            generate_text_previews=True,
            max_file_size_mb=settings.max_file_size_mb,
            llm_model=settings.llm_model,
            embedding_model=settings.embedding_model,
            search_results_limit=25,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_format=response_format,
            context_window_size=context_window_size,
            response_timeout=response_timeout,
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

    Updates are applied to the global settings instance and will affect:
    - New conversation creation (llm_model)
    - File size validation (max_file_size_mb)
    - UI theme (theme)
    - Other runtime behavior

    Note: Settings are stored in memory only. Changes persist until server restart.
    For permanent changes, update environment variables or .env file.

    Validates:
    - File size limits (1-1000 MB)
    - Search result limits (1-1000)
    - Theme values (light/dark/system)
    - Interface density (compact/comfortable/spacious)
    """
    try:
        settings = get_app_settings()
        updated_fields = []

        # Update settings in memory
        if request.max_file_size_mb is not None:
            settings.max_file_size_mb = request.max_file_size_mb
            updated_fields.append("max_file_size_mb")

        if request.llm_model is not None:
            settings.llm_model = request.llm_model
            updated_fields.append("llm_model")

        if request.embedding_model is not None:
            settings.embedding_model = request.embedding_model
            updated_fields.append("embedding_model")

        if request.theme is not None:
            settings.theme = request.theme
            updated_fields.append("theme")

        # Track other fields (not yet persisted to settings object)
        if request.auto_extract_dates is not None:
            updated_fields.append("auto_extract_dates")
        if request.generate_text_previews is not None:
            updated_fields.append("generate_text_previews")
        if request.search_results_limit is not None:
            updated_fields.append("search_results_limit")
        if request.auto_organize_by_date is not None:
            updated_fields.append("auto_organize_by_date")
        if request.duplicate_detection is not None:
            updated_fields.append("duplicate_detection")
        if request.default_import_location is not None:
            updated_fields.append("default_import_location")
        if request.interface_density is not None:
            updated_fields.append("interface_density")

        # Update conversation defaults in database
        if any(
            [
                request.temperature is not None,
                request.max_output_tokens is not None,
                request.response_format is not None,
                request.context_window_size is not None,
                request.response_timeout is not None,
            ]
        ):
            server = get_server()
            if (
                server.service_container
                and server.service_container.conversation_service
            ):
                db_pool = server.service_container.conversation_service.db_pool

                async with db_pool.acquire() as conn:
                    # Build update query dynamically
                    updates = []
                    values: List[Union[float, int, str]] = []
                    param_count = 1

                    if request.temperature is not None:
                        updates.append(f"temperature = ${param_count}")
                        values.append(request.temperature)
                        param_count += 1
                        updated_fields.append("temperature")

                    if request.max_output_tokens is not None:
                        updates.append(f"max_output_tokens = ${param_count}")
                        values.append(request.max_output_tokens)
                        param_count += 1
                        updated_fields.append("max_output_tokens")

                    if request.response_format is not None:
                        updates.append(f"response_format = ${param_count}")
                        values.append(request.response_format)
                        param_count += 1
                        updated_fields.append("response_format")

                    if request.context_window_size is not None:
                        updates.append(f"context_window_size = ${param_count}")
                        values.append(request.context_window_size)
                        param_count += 1
                        updated_fields.append("context_window_size")

                    if request.response_timeout is not None:
                        updates.append(f"response_timeout = ${param_count}")
                        values.append(request.response_timeout)
                        param_count += 1
                        updated_fields.append("response_timeout")

                    if updates:
                        updates.append("updated_at = NOW()")
                        # Use UPDATE directly since we know the record exists (created by schema.sql)
                        query = f"""
                            UPDATE user_preferences 
                            SET {', '.join(updates)}
                            WHERE user_id = 'default'
                        """
                        await conn.execute(query, *values)

                        # Optionally update existing conversations that are using defaults
                        if request.temperature is not None:
                            await conn.execute(
                                """
                                UPDATE conversations 
                                SET temperature = $1, updated_at = NOW()
                                WHERE temperature = 0.7 AND archived_at IS NULL
                                """,
                                request.temperature,
                            )

                        if request.max_output_tokens is not None:
                            await conn.execute(
                                """
                                UPDATE conversations 
                                SET max_tokens = $1, updated_at = NOW()
                                WHERE max_tokens = 2000 AND archived_at IS NULL
                                """,
                                request.max_output_tokens,
                            )

        if not updated_fields:
            raise HTTPException(
                status_code=400, detail="No settings provided to update"
            )

        return {
            "success": True,
            "message": "Settings updated successfully",
            "updated_fields": updated_fields,
            "current_llm_model": settings.llm_model,
            "note": "Settings are stored in memory and persist until server restart. For permanent changes, update environment variables.",
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
    Get available LLM and embedding models from all providers.

    Returns lists of:
    - LLM models from all registered providers (Ollama, OpenAI, etc.)
    - Embedding models for semantic search

    Queries the provider manager to get real-time model availability.
    """
    server = get_server()

    try:
        llm_models = []

        # Get models from all providers
        if server.service_container and server.service_container.llm_provider_manager:
            provider_manager = server.service_container.llm_provider_manager
            providers = provider_manager.list_providers()

            # Fetch models from each provider
            for provider_info in providers:
                provider_id = provider_info["id"]
                provider_type = provider_info["type"]

                try:
                    models_result = await provider_manager.list_models(provider_id)

                    if models_result.is_success():
                        models = models_result.unwrap()

                        # Convert ModelInfo to dict format
                        for model in models:
                            llm_models.append(
                                {
                                    "id": model.id,
                                    "name": model.name,
                                    "description": f"{provider_type.upper()} model",
                                    "provider": provider_type,
                                    "provider_id": provider_id,
                                    "context_window": model.context_window,
                                    "supports_streaming": model.supports_streaming,
                                    "cost_per_1k_input": model.cost_per_1k_input,
                                    "cost_per_1k_output": model.cost_per_1k_output,
                                }
                            )
                except Exception as e:
                    # Log but don't fail if one provider fails
                    import logging

                    logging.warning(
                        f"Failed to fetch models from provider {provider_id}: {e}"
                    )
                    continue

        # Hardcoded embedding models (these are local sentence-transformers)
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
