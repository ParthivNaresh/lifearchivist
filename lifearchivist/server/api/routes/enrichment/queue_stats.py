"""
Get queue statistics endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

router = APIRouter()


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
