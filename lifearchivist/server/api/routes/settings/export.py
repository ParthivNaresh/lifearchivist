"""
Export settings endpoint.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from ..shared.exceptions import InternalServerError
from .get import get_settings

router = APIRouter()

SETTINGS_VERSION = "0.1.0"


class ExportSettingsResponse(BaseModel):
    """Response from exporting settings."""

    success: bool = Field(default=True, description="Whether export succeeded")
    settings: Dict[str, Any] = Field(..., description="Exported settings data")
    exported_at: str = Field(..., description="ISO timestamp of export")
    version: str = Field(..., description="Settings schema version")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "settings": {
                    "llm_model": "gpt-4",
                    "temperature": 0.7,
                },
                "exported_at": "2025-01-08T14:30:00Z",
                "version": "0.1.0",
            }
        }


@router.get(
    "/export",
    response_model=ExportSettingsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Failed to export settings: <error message>"}
                }
            },
        },
    },
)
async def export_settings() -> ExportSettingsResponse:
    """
    Export current settings as JSON.

    Returns all current settings in a portable JSON format suitable for backup,
    sharing, or version control.

    ## Response Fields

    - **success**: Whether export succeeded
    - **settings**: Complete settings object
    - **exported_at**: ISO timestamp of export
    - **version**: Settings schema version

    ## Example Response

    ```json
    {
        "success": true,
        "settings": {
            "llm_model": "gpt-4",
            "llm_provider": "openai",
            "temperature": 0.7,
            "max_output_tokens": 2000,
            "response_format": "markdown",
            "context_window_size": 10,
            "response_timeout": 30
        },
        "exported_at": "2025-01-08T14:30:00Z",
        "version": "0.1.0"
    }
    ```

    ## Use Cases

    - Backup configuration
    - Share settings between installations
    - Version control preferences
    - Migrate settings to new instance
    - Document configuration

    ## Export Contents

    Includes all user preferences:
    - LLM model and provider settings
    - Temperature and token limits
    - Response formatting preferences
    - Context window configuration
    - Timeout settings
    - All other user preferences

    ## Import

    Exported settings can be imported via:
    - Settings import endpoint
    - Manual configuration
    - Deployment scripts

    ## Version

    - Schema version included for compatibility
    - Future versions may have different schemas
    - Version helps with migration

    ## Performance Notes

    - Fast operation (just reads current settings)
    - No heavy computation
    - Safe to call frequently
    - Minimal overhead

    ## Notes

    - Returns current settings snapshot
    - Timestamp indicates export time
    - Settings are user-specific
    - No sensitive data included
    """
    try:
        current_settings = await get_settings()

        return ExportSettingsResponse(
            success=True,
            settings=current_settings.dict(),
            exported_at=datetime.utcnow().isoformat() + "Z",
            version=SETTINGS_VERSION,
        )

    except Exception as e:
        raise InternalServerError("Export settings", e) from e
