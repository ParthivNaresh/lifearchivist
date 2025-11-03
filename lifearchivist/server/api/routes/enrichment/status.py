"""
Get enrichment status endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/status")
async def get_enrichment_status():
    """
    Get enrichment queue and worker status.

    Returns information about:
    - Whether enrichment is enabled
    - Worker status and health
    - Current processing state
    """
    server = get_server()

    if not server.background_tasks:
        return JSONResponse(
            content={
                "success": False,
                "enabled": False,
                "error": "Background enrichment not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        status = await server.background_tasks.get_status()
        return {
            "success": True,
            **status,
        }
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to get enrichment status: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
