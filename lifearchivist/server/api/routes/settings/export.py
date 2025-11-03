"""
Export settings endpoint.
"""

from fastapi import APIRouter, HTTPException

from .get import get_settings

router = APIRouter()


@router.get("/export")
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
            "exported_at": "2025-01-06T14:30:00Z",
            "version": "0.1.0",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to export settings: {str(e)}"
        ) from None
