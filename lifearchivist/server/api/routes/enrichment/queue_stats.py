"""
Get queue statistics endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from .utils import validate_enrichment_queue

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
    service, error_response = validate_enrichment_queue(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        stats = await service.get_stats()
        return success_response(stats)
    except Exception as e:
        return internal_error_response("Get queue stats", e)
