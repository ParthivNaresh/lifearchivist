"""
Update settings endpoint.
"""

from fastapi import APIRouter, HTTPException

from lifearchivist.config import get_settings as get_app_settings

from ..shared.dependencies import get_server
from ..utils import (
    has_conversation_defaults_update,
    track_non_persisted_fields,
    update_conversation_defaults_in_db,
    update_settings_in_memory,
)
from .models import SettingsUpdateRequest

router = APIRouter()


@router.put("/")
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
