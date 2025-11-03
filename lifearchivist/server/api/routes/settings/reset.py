"""
Reset settings endpoint.
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/reset")
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
