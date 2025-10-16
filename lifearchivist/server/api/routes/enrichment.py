"""
Enrichment queue status and management endpoints.

These endpoints provide visibility into the background enrichment system,
including worker status, queue statistics, and processing metrics.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..dependencies import get_server

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


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


@router.get("/queue/stats")
async def get_queue_stats():
    """
    Get detailed queue statistics.

    Returns metrics about:
    - Queue size and pending items
    - Processing rates
    - Success/failure counts
    - Average processing times
    """
    server = get_server()

    if not server.enrichment_queue:
        return JSONResponse(
            content={
                "success": False,
                "status": "not_available",
                "error": "Enrichment queue not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        stats = await server.enrichment_queue.get_stats()
        return {
            "success": True,
            **stats,
        }
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to get queue stats: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
