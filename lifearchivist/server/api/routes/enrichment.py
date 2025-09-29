"""
Enrichment queue status and management endpoints.
"""

from fastapi import APIRouter, HTTPException

from ..dependencies import get_server

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


@router.get("/status")
async def get_enrichment_status():
    """Get enrichment queue and worker status."""
    server = get_server()

    if not server.background_tasks:
        return {"enabled": False, "message": "Background enrichment not available"}

    try:
        status = await server.background_tasks.get_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/queue/stats")
async def get_queue_stats():
    """Get detailed queue statistics."""
    server = get_server()

    if not server.enrichment_queue:
        return {
            "status": "not_available",
            "message": "Enrichment queue not initialized",
        }

    try:
        stats = await server.enrichment_queue.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
