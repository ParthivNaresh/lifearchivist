"""
Enrichment queue status and management endpoints.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..dependencies import get_server

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


@router.get("/status")
async def get_enrichment_status():
    """Get enrichment queue and worker status."""
    server = get_server()

    if not server.background_tasks:
        return JSONResponse(
            content={
                "enabled": False,
                "message": "Background enrichment not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        status = await server.background_tasks.get_status()
        return status
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )


@router.get("/queue/stats")
async def get_queue_stats():
    """Get detailed queue statistics."""
    server = get_server()

    if not server.enrichment_queue:
        return JSONResponse(
            content={
                "status": "not_available",
                "message": "Enrichment queue not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        stats = await server.enrichment_queue.get_stats()
        return stats
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )
