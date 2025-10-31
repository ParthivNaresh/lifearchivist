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

router = APIRouter(prefix="/api/folder-watch", tags=["folder-watch"])
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


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


# ============================================================================
# Folder Management Endpoints
# ============================================================================


@router.post("/folders", response_model=FolderResponse, status_code=201)
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
            status_code=503,
            detail="Folder watcher service not initialized",
        )

    # Validate and normalize path
    try:
        folder_path = Path(request.folder_path).expanduser().resolve()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid folder path: {str(e)}",
        ) from e

    try:
        # Add folder to watcher
        folder_id = await server.folder_watcher.add_folder(
            path=folder_path,
            enabled=request.enabled,
        )

        # Get folder details
        folder = await server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise HTTPException(
                status_code=500,
                detail="Folder was added but could not be retrieved",
            )

        return _folder_to_response(folder)

    except ValueError as e:
        # Validation errors (duplicate, limit reached, etc.)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add folder: {str(e)}",
        ) from e


@router.get("/folders", response_model=FolderListResponse)
async def list_folders(enabled_only: bool = False):
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
            status_code=503,
            detail="Folder watcher service not initialized",
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
            status_code=500,
            detail=f"Failed to list folders: {str(e)}",
        ) from e


@router.get("/folders/{folder_id}", response_model=FolderResponse)
async def get_folder(folder_id: str = PathParam(..., description="Folder UUID")):
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
            status_code=503,
            detail="Folder watcher service not initialized",
        )

    try:
        folder = await server.folder_watcher.get_folder(folder_id)

        if not folder:
            raise HTTPException(
                status_code=404,
                detail=f"Folder not found: {folder_id}",
            )

        return _folder_to_response(folder)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get folder: {str(e)}",
        ) from e


@router.delete("/folders/{folder_id}")
async def remove_folder(folder_id: str = PathParam(..., description="Folder UUID")):
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
            status_code=503,
            detail="Folder watcher service not initialized",
        )

    try:
        removed = await server.folder_watcher.remove_folder(folder_id)

        if not removed:
            raise HTTPException(
                status_code=404,
                detail=f"Folder not found: {folder_id}",
            )

        return {
            "success": True,
            "message": "Folder removed successfully",
            "folder_id": folder_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove folder: {str(e)}",
        ) from e


@router.patch("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    request: UpdateFolderRequest,
    folder_id: str = PathParam(..., description="Folder UUID"),
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
            status_code=503,
            detail="Folder watcher service not initialized",
        )

    try:
        # Check if folder exists
        folder = await server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise HTTPException(
                status_code=404,
                detail=f"Folder not found: {folder_id}",
            )

        # Update enabled status if provided
        if request.enabled is not None:
            if request.enabled:
                await server.folder_watcher.enable_folder(folder_id)
            else:
                await server.folder_watcher.disable_folder(folder_id)

        # Return updated folder details (in-memory state is already updated)
        return _folder_to_response(folder)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update folder: {str(e)}",
        ) from e


# ============================================================================
# Folder Operations
# ============================================================================


@router.post("/folders/{folder_id}/scan", response_model=FolderScanResponse)
async def scan_folder(folder_id: str = PathParam(..., description="Folder UUID")):
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
            status_code=503,
            detail="Folder watcher service not initialized",
        )

    try:
        # Get folder
        folder = await server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise HTTPException(
                status_code=404,
                detail=f"Folder not found: {folder_id}",
            )

        # Check if folder is enabled
        if not folder.enabled:
            raise HTTPException(
                status_code=400,
                detail="Folder must be enabled to scan",
            )

        # Check if folder path still exists
        if not folder.path.exists() or not folder.path.is_dir():
            raise HTTPException(
                status_code=400,
                detail=f"Folder path no longer accessible: {folder.path}",
            )

        # Scan folder for supported files
        files_found = []
        for ext in server.folder_watcher.SUPPORTED_EXTENSIONS:
            files_found.extend(folder.path.rglob(f"*{ext}"))

        # Filter out hidden/temp files
        files_found = [
            f
            for f in files_found
            if not f.name.startswith(".") and not f.name.startswith("~")
        ]

        # Schedule each file for ingestion
        files_queued = 0
        failed_files = 0
        for file_path in files_found:
            try:
                await server.folder_watcher.schedule_ingestion(folder_id, file_path)
                files_queued += 1
            except Exception as e:
                # Log error but continue with other files
                logger.warning(
                    f"Failed to queue file {file_path.name} for ingestion: {e}"
                )
                failed_files += 1

        return FolderScanResponse(
            success=True,
            folder_id=folder_id,
            folder_path=str(folder.path),
            files_found=len(files_found),
            files_queued=files_queued,
            message=f"Scanned folder and queued {files_queued} files for ingestion",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan folder: {str(e)}",
        ) from e


# ============================================================================
# Status Endpoints
# ============================================================================


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
            status_code=503,
            detail="Folder watcher service not initialized",
        )

    try:
        # Get aggregate stats
        aggregate = await server.folder_watcher.get_aggregate_status()

        # Get individual folder details
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
            status_code=500,
            detail=f"Failed to get status: {str(e)}",
        ) from e


@router.get("/folders/{folder_id}/status", response_model=FolderResponse)
async def get_folder_status(folder_id: str = PathParam(..., description="Folder UUID")):
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
