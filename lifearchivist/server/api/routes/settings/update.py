"""
Update settings endpoint.
"""

from typing import List

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from lifearchivist.config import get_settings as get_app_settings

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ValidationError
from .models import SettingsUpdateRequest
from .utils import (
    has_conversation_defaults_update,
    track_non_persisted_fields,
    update_conversation_defaults_in_db,
    update_settings_in_memory,
)

router = APIRouter()


class UpdateSettingsResponse(BaseModel):
    """Response from updating settings."""

    message: str = Field(..., description="Success message")
    updated_fields: List[str] = Field(..., description="List of updated field names")
    current_llm_model: str = Field(..., description="Current LLM model")
    note: str = Field(..., description="Persistence note")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Settings updated successfully",
                "updated_fields": ["temperature", "max_output_tokens"],
                "current_llm_model": "gpt-4",
                "note": "Settings are stored in memory and persist until server restart. For permanent changes, update environment variables.",
            }
        }


@router.put(
    "/",
    response_model=UpdateSettingsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid settings",
            "content": {
                "application/json": {
                    "example": {"detail": "No settings provided to update"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Update settings failed: <error message>"}
                }
            },
        },
    },
)
async def update_settings(request: SettingsUpdateRequest) -> UpdateSettingsResponse:
    """
    Update application settings and user preferences.

    Updates are applied to global settings and database. Changes affect new
    conversations, file validation, UI theme, and other runtime behavior.

    ## Request Body

    All fields optional - only provided fields updated:
    - **llm_model**: LLM model name
    - **max_file_size_mb**: Max file size (1-1000 MB)
    - **theme**: UI theme (light/dark/system)
    - **temperature**: LLM temperature (0.0-2.0)
    - **max_output_tokens**: Max output tokens
    - **response_format**: Response format
    - **context_window_size**: Context window size
    - **response_timeout**: Response timeout (seconds)
    - Other settings fields

    ## Response Fields

    - **message**: Success confirmation
    - **updated_fields**: List of updated field names
    - **current_llm_model**: Current LLM model
    - **note**: Persistence information

    ## Example Request

    ```json
    {
        "temperature": 0.8,
        "max_output_tokens": 3000,
        "response_format": "detailed"
    }
    ```

    ## Example Response

    ```json
    {
        "message": "Settings updated successfully",
        "updated_fields": ["temperature", "max_output_tokens", "response_format"],
        "current_llm_model": "gpt-4",
        "note": "Settings are stored in memory and persist until server restart. For permanent changes, update environment variables."
    }
    ```

    ## Settings Categories

    ### In-Memory Settings
    - llm_model
    - max_file_size_mb
    - theme
    - embedding_model

    ### Database Settings
    - temperature
    - max_output_tokens
    - response_format
    - context_window_size
    - response_timeout

    ## Validation

    - **max_file_size_mb**: 1-1000 MB
    - **search_results_limit**: 1-1000
    - **theme**: light/dark/system
    - **interface_density**: compact/comfortable/spacious
    - **temperature**: 0.0-2.0
    - **max_output_tokens**: Positive integer

    ## Persistence

    - **In-Memory**: Persists until server restart
    - **Database**: Persists permanently
    - **Permanent**: Update environment variables or .env

    ## Use Cases

    - Change LLM model
    - Adjust temperature
    - Update token limits
    - Change theme
    - Modify timeouts
    - Configure preferences

    ## Performance Notes

    - Fast update operation
    - Database updates for user preferences
    - In-memory updates for system settings
    - Immediate effect

    ## Notes

    - Returns 400 if no fields provided
    - Partial updates supported
    - Only provided fields modified
    - Changes affect new operations
    - Existing operations unchanged
    """
    try:
        settings = get_app_settings()

        memory_fields = update_settings_in_memory(settings, request)
        tracked_fields = track_non_persisted_fields(request)
        updated_fields = memory_fields + tracked_fields

        if has_conversation_defaults_update(request):
            server = get_server()
            if (
                server.service_container
                and server.service_container.conversation_service
            ):
                db_pool = server.service_container.conversation_service.db_pool
                db_fields = await update_conversation_defaults_in_db(db_pool, request)
                updated_fields.extend(db_fields)

        if not updated_fields:
            raise ValidationError("No settings provided to update")

        return UpdateSettingsResponse(
            message="Settings updated successfully",
            updated_fields=updated_fields,
            current_llm_model=settings.llm_model,
            note="Settings are stored in memory and persist until server restart. For permanent changes, update environment variables.",
        )

    except ValidationError:
        raise
    except Exception as e:
        raise InternalServerError("Update settings", e) from e
