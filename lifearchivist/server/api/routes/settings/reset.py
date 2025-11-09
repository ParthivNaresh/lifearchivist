"""
Reset settings endpoint.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from ..shared.exceptions import InternalServerError

router = APIRouter()


class ResetSettingsResponse(BaseModel):
    """Response from resetting settings."""

    message: str = Field(..., description="Success message")
    note: str = Field(..., description="Implementation note")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Settings reset to default values",
                "note": "Settings reset is currently a placeholder. Full implementation will be added in a future update.",
            }
        }


@router.post(
    "/reset",
    response_model=ResetSettingsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Reset settings failed: <error message>"}
                }
            },
        },
    },
)
async def reset_settings() -> ResetSettingsResponse:
    """
    Reset all settings to default values.

    Restores all user preferences and configuration to factory defaults.
    Currently a placeholder - full implementation pending.

    ## Response Fields

    - **message**: Success confirmation message
    - **note**: Implementation status note

    ## Example Response

    ```json
    {
        "message": "Settings reset to default values",
        "note": "Settings reset is currently a placeholder. Full implementation will be added in a future update."
    }
    ```

    ## What Will Be Reset (Future Implementation)

    ### User Preferences
    - LLM model and provider
    - Temperature and token limits
    - Response format
    - Context window size
    - Timeout settings

    ### Document Processing
    - Auto-extract dates
    - Text preview generation
    - Duplicate detection
    - File size limits

    ### UI Preferences
    - Theme
    - Interface density
    - Default locations

    ### Search Settings
    - Result limits
    - Search modes

    ## Use Cases

    - Restore defaults after testing
    - Fix misconfiguration
    - Start fresh
    - Troubleshoot issues
    - Reset after errors

    ## Important Warnings (Future)

    - **DESTRUCTIVE**: Cannot be undone
    - **ALL SETTINGS LOST**: Every preference reset
    - **NO BACKUP**: No automatic backup created
    - **IMMEDIATE**: Takes effect immediately

    ## Current Status

    - **Placeholder**: Not yet fully implemented
    - **Safe to call**: No actual changes made
    - **Future**: Will reset all preferences

    ## Notes

    - Currently returns success without changes
    - Full implementation planned
    - Will require confirmation in future
    - Documents and data not affected
    """
    try:
        return ResetSettingsResponse(
            message="Settings reset to default values",
            note="Settings reset is currently a placeholder. Full implementation will be added in a future update.",
        )

    except Exception as e:
        raise InternalServerError("Reset settings", e) from e
