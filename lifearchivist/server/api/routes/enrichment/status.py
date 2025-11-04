"""
Get enrichment status endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from .utils import validate_background_tasks

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
    service, error_response = validate_background_tasks(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        status = await service.get_status()
        return success_response(status)
    except Exception as e:
        return internal_error_response("Get enrichment status", e)
