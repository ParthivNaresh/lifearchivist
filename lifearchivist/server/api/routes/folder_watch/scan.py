"""
Scan folder endpoint.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam

from lifearchivist.models.folder_watch import FolderScanResponse

from ..constants import (
    ErrorMessages,
    FolderWatchConstants,
    HTTPStatus,
    PathParamDescriptions,
    ResourceNames,
    ServiceNames,
    SuccessMessages,
)
from ..shared.dependencies import get_server

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/folders/{folder_id}/scan", response_model=FolderScanResponse)
async def scan_folder(
    folder_id: str = PathParam(..., description=PathParamDescriptions.FOLDER_UUID),
):
    """
    Manually trigger a scan of a specific folder.

    Args:
        folder_id: Folder UUID

    Returns:
        Scan results (files found and queued)

    Raises:
        404: Folder not found
        400: Folder not enabled or not accessible
        503: Folder watcher not initialized
        500: Internal server error

    Notes:
        - Scans recursively for all supported file types
        - Respects deduplication (won't re-ingest existing files)
        - Files are queued with debounce delay
        - Folder must be enabled to scan
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
        folder = await server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=ErrorMessages.RESOURCE_NOT_FOUND.format(
                    resource=ResourceNames.FOLDER, identifier=folder_id
                ),
            )

        if not folder.enabled:
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=ErrorMessages.RESOURCE_MUST_BE_ENABLED.format(
                    resource=ResourceNames.FOLDER, action="scan"
                ),
            )

        if not folder.path.exists() or not folder.path.is_dir():
            raise HTTPException(
                status_code=HTTPStatus.BAD_REQUEST,
                detail=ErrorMessages.PATH_NOT_ACCESSIBLE.format(
                    path_type=ResourceNames.FOLDER, path=folder.path
                ),
            )

        files_found = []
        for ext in server.folder_watcher.SUPPORTED_EXTENSIONS:
            files_found.extend(folder.path.rglob(f"*{ext}"))

        files_found = [
            f
            for f in files_found
            if not any(
                f.name.startswith(prefix)
                for prefix in FolderWatchConstants.HIDDEN_FILE_PREFIXES
            )
        ]

        files_queued = 0
        files_failed = 0
        for file_path in files_found:
            try:
                await server.folder_watcher.schedule_ingestion(folder_id, file_path)
                files_queued += 1
            except Exception as e:
                logger.warning(
                    f"Failed to queue file {file_path.name} for ingestion: {e}"
                )
                files_failed += 1

        return FolderScanResponse(
            success=True,
            folder_id=folder_id,
            folder_path=str(folder.path),
            files_found=len(files_found),
            files_queued=files_queued,
            files_failed=files_failed,
            message=SuccessMessages.SCAN_COMPLETED.format(
                resource="folder", count=files_queued
            ),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="scan folder", error=str(e)
            ),
        ) from e
