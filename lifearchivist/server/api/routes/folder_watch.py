"""
Multi-folder watching API endpoints.

Provides RESTful endpoints for managing multiple watched folders
and automatic document ingestion.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam

from lifearchivist.models.folder_watch import (
    AddFolderRequest,
    AggregateStatusResponse,
    FolderListResponse,
    FolderResponse,
    FolderScanResponse,
    UpdateFolderRequest,
    WatchedFolder,
)

from ..dependencies import get_server
from .constants import (
    ErrorMessages,
    FolderWatchConstants,
    HTTPStatus,
    PathParamDescriptions,
    ResourceNames,
    ServiceNames,
    SuccessMessages,
)

router = APIRouter(prefix="/api/folder-watch", tags=["folder-watch"])
logger = logging.getLogger(__name__)


def _folder_to_response(folder: WatchedFolder) -> FolderResponse:
    """
    Convert WatchedFolder to FolderResponse.

    Centralizes the conversion logic to avoid duplication.

    Args:
        folder: WatchedFolder instance

    Returns:
        FolderResponse for API
    """
    return FolderResponse(
        id=folder.id,
        path=str(folder.path),
        enabled=folder.enabled,
        created_at=folder.created_at.isoformat(),
        status=folder.status.value,
        health=folder.stats.get_health_status().value,
        is_active=folder.is_active(),
        success_rate=folder.stats.get_success_rate(),
        stats=folder.stats.to_dict(),
    )


@router.post("/folders", response_model=FolderResponse, status_code=HTTPStatus.CREATED)
async def add_folder(request: AddFolderRequest):
    """
    Add a new folder to watch.

    Args:
        request: Folder path and configuration

    Returns:
        Created folder details with UUID

    Raises:
        400: Invalid folder path or already watched
        503: Folder watcher not initialized
        500: Internal server error
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
        folder_path = Path(request.folder_path).expanduser().resolve()
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ErrorMessages.INVALID_PATH.format(path_type="folder", error=str(e)),
        ) from e

    try:
        folder_id = await server.folder_watcher.add_folder(
            path=folder_path,
            enabled=request.enabled,
        )

        folder = await server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=ErrorMessages.RESOURCE_ADDED_NOT_RETRIEVED.format(
                    resource=ResourceNames.FOLDER
                ),
            )

        return _folder_to_response(folder)

    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="add folder", error=str(e)
            ),
        ) from e


@router.get("/folders", response_model=FolderListResponse)
async def list_folders(
    enabled_only: bool = FolderWatchConstants.DEFAULT_ENABLED_ONLY_FILTER,
):
    """
    List all watched folders.

    Args:
        enabled_only: If true, only return enabled folders

    Returns:
        List of watched folders with statistics

    Raises:
        503: Folder watcher not initialized
        500: Internal server error
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
        folders = await server.folder_watcher.list_folders(enabled_only=enabled_only)
        folder_responses = [_folder_to_response(folder) for folder in folders]

        return FolderListResponse(
            success=True,
            folders=folder_responses,
            total=len(folder_responses),
        )

    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="list folders", error=str(e)
            ),
        ) from e


@router.get("/folders/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str = PathParam(..., description=PathParamDescriptions.FOLDER_UUID),
):
    """
    Get details for a specific watched folder.

    Args:
        folder_id: Folder UUID

    Returns:
        Folder details with statistics

    Raises:
        404: Folder not found
        503: Folder watcher not initialized
        500: Internal server error
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

        return _folder_to_response(folder)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="get folder", error=str(e)
            ),
        ) from e


@router.delete("/folders/{folder_id}")
async def remove_folder(
    folder_id: str = PathParam(..., description=PathParamDescriptions.FOLDER_UUID),
):
    """
    Remove a watched folder.

    Args:
        folder_id: Folder UUID

    Returns:
        Success confirmation

    Raises:
        404: Folder not found
        503: Folder watcher not initialized
        500: Internal server error

    Notes:
        - Stops watching if currently active
        - Cancels all pending file ingestions for this folder
        - Removes folder configuration from persistence
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
        removed = await server.folder_watcher.remove_folder(folder_id)

        if not removed:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=ErrorMessages.RESOURCE_NOT_FOUND.format(
                    resource=ResourceNames.FOLDER, identifier=folder_id
                ),
            )

        return {
            "success": True,
            "message": SuccessMessages.RESOURCE_REMOVED.format(
                resource=ResourceNames.FOLDER
            ),
            "folder_id": folder_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="remove folder", error=str(e)
            ),
        ) from e


@router.patch("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    request: UpdateFolderRequest,
    folder_id: str = PathParam(..., description=PathParamDescriptions.FOLDER_UUID),
):
    """
    Update folder configuration.

    Args:
        folder_id: Folder UUID
        request: Update parameters (enabled status)

    Returns:
        Updated folder details

    Raises:
        404: Folder not found
        503: Folder watcher not initialized
        500: Internal server error

    Notes:
        - Currently only supports enabling/disabling watching
        - Enabling starts the observer immediately
        - Disabling stops the observer and cancels pending ingestions
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

        if request.enabled is not None:
            if request.enabled:
                await server.folder_watcher.enable_folder(folder_id)
            else:
                await server.folder_watcher.disable_folder(folder_id)

        return _folder_to_response(folder)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="update folder", error=str(e)
            ),
        ) from e


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
        folder_responses = [_folder_to_response(folder) for folder in folders]

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


@router.get("/folders/{folder_id}/status", response_model=FolderResponse)
async def get_folder_status(
    folder_id: str = PathParam(..., description=PathParamDescriptions.FOLDER_UUID),
):
    """
    Get detailed status for a specific folder.

    Args:
        folder_id: Folder UUID

    Returns:
        Folder status with detailed statistics

    Raises:
        404: Folder not found
        503: Folder watcher not initialized
        500: Internal server error

    Notes:
        - Alias for GET /folders/{folder_id}
        - Provided for semantic clarity
    """
    return await get_folder(folder_id)
