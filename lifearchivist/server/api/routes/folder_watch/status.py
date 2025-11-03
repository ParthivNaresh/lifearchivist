"""
Get aggregate status endpoint.
"""

from fastapi import APIRouter, HTTPException

from lifearchivist.models.folder_watch import AggregateStatusResponse

from ..constants import (
    ErrorMessages,
    HTTPStatus,
    ServiceNames,
)
from ..shared.dependencies import get_server
from .utils import folder_to_response

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

    if not server.folder_watcher:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=ErrorMessages.SERVICE_NOT_INITIALIZED.format(
                service=ServiceNames.FOLDER_WATCHER
            ),
        )

    try:
        aggregate = await server.folder_watcher.get_aggregate_status()
        folders = await server.folder_watcher.list_folders()
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
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="get status", error=str(e)
            ),
        ) from e
