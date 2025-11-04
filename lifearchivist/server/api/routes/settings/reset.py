"""
Reset settings endpoint.
"""

from fastapi import APIRouter

from ..shared.responses import internal_error_response, success_response

router = APIRouter()


@router.post("/reset")
async def reset_settings():
    """
    Reset all settings to default values.

    Note: Currently a placeholder.
    Full implementation will restore all settings to factory defaults.
    """
    try:
        return success_response(
            {
                "message": "Settings reset to default values",
                "note": "Settings reset is currently a placeholder. Full implementation will be added in a future update.",
            }
        )

    except Exception as e:
        return internal_error_response("Reset settings", e)
