"""
Get aggregate status endpoint.
"""

from fastapi import APIRouter

from lifearchivist.models.folder_watch import AggregateStatusResponse

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response
from .utils import folder_to_response, validate_folder_watcher

router = APIRouter()


@router.get("/status", response_model=AggregateStatusResponse)
async def get_aggregate_status():
    """
    Get aggregate status across all watched folders.

    Returns:
        System-wide statistics and folder summaries

    Raises:
        503: Folder watcher not initialized
        500: Internal server error

    Notes:
        - Includes totals for all folders combined
        - Lists individual folder details
        - Shows supported file extensions
        - Displays concurrency settings
    """
    server = get_server()
    service, error_response = validate_folder_watcher(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        aggregate = await service.get_aggregate_status()
        folders = await service.list_folders()
        folder_responses = [folder_to_response(folder) for folder in folders]

        return AggregateStatusResponse(
            success=True,
            total_folders=aggregate["total_folders"],
            active_folders=aggregate["active_folders"],
            total_pending=aggregate["total_pending"],
            total_detected=aggregate["total_detected"],
            total_ingested=aggregate["total_ingested"],
            total_failed=aggregate["total_failed"],
            total_bytes_processed=aggregate["total_bytes_processed"],
            folders=folder_responses,
            supported_extensions=aggregate["supported_extensions"],
            ingestion_concurrency=aggregate["ingestion_concurrency"],
        )

    except Exception as e:
        return internal_error_response("Get status", e)
