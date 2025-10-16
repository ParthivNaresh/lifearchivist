"""
Folder watching API endpoints.

Provides endpoints for managing automatic folder watching and ingestion.
"""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..dependencies import get_server

router = APIRouter(prefix="/api/folder-watch", tags=["folder-watch"])


class StartWatchRequest(BaseModel):
    """Request to start watching a folder."""

    folder_path: str = Field(
        description="Absolute path to folder to watch",
        examples=["/Users/username/Documents"],
    )


class FolderWatchStatus(BaseModel):
    """Status of folder watching service."""

    enabled: bool = Field(description="Whether folder watching is enabled")
    watched_path: Optional[str] = Field(
        None, description="Path currently being watched"
    )
    pending_files: int = Field(description="Number of files pending ingestion")
    supported_extensions: list[str] = Field(
        description="List of supported file extensions"
    )
    debounce_seconds: float = Field(description="Debounce delay in seconds")


@router.get("/status", response_model=FolderWatchStatus)
async def get_folder_watch_status():
    """
    Get current status of folder watching service.

    Returns:
        Current status including enabled state, watched path, and statistics
    """
    server = get_server()

    if not server.folder_watcher:
        return JSONResponse(
            content={
                "success": False,
                "error": "Folder watcher not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        status = server.folder_watcher.get_status()
        return {
            "success": True,
            **status,
        }
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to get status: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.post("/start")
async def start_folder_watch(request: StartWatchRequest):
    """
    Start watching a folder for new documents.

    Args:
        request: Folder path to watch

    Returns:
        Success status and watched folder information

    Notes:
        - Only one folder can be watched at a time (MVP limitation)
        - Folder must exist and be readable
        - Watches recursively (includes subdirectories)
        - Automatically ingests supported file types
    """
    server = get_server()

    if not server.folder_watcher:
        return JSONResponse(
            content={
                "success": False,
                "error": "Folder watcher not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    # Validate folder path
    folder_path = Path(request.folder_path).expanduser().resolve()

    if not folder_path.exists():
        return JSONResponse(
            content={
                "success": False,
                "error": f"Folder does not exist: {folder_path}",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if not folder_path.is_dir():
        return JSONResponse(
            content={
                "success": False,
                "error": f"Path is not a directory: {folder_path}",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    try:
        # Start watching
        success = await server.folder_watcher.start(folder_path)

        if success:
            return {
                "success": True,
                "message": "Folder watching started",
                "watched_path": str(folder_path),
                "recursive": True,
                "supported_extensions": list(
                    server.folder_watcher.SUPPORTED_EXTENSIONS
                ),
            }
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "error": "Failed to start folder watching",
                    "error_type": "ServiceError",
                },
                status_code=500,
            )

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to start folder watching: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.post("/stop")
async def stop_folder_watch():
    """
    Stop watching the current folder.

    Returns:
        Success status

    Notes:
        - Cancels all pending file ingestions
        - Safe to call even if not currently watching
    """
    server = get_server()

    if not server.folder_watcher:
        return JSONResponse(
            content={
                "success": False,
                "error": "Folder watcher not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        await server.folder_watcher.stop()

        return {
            "success": True,
            "message": "Folder watching stopped",
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to stop folder watching: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.post("/scan")
async def scan_folder_now():
    """
    Manually trigger a scan of the watched folder.

    Returns:
        Number of files found and queued for ingestion

    Notes:
        - Only works if folder watching is currently enabled
        - Scans for all supported file types
        - Respects deduplication (won't re-ingest existing files)
    """
    server = get_server()

    if not server.folder_watcher:
        return JSONResponse(
            content={
                "success": False,
                "error": "Folder watcher not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    if not server.folder_watcher.enabled:
        return JSONResponse(
            content={
                "success": False,
                "error": "Folder watching is not enabled",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    try:
        watched_path = server.folder_watcher.watched_path
        if not watched_path:
            return JSONResponse(
                content={
                    "success": False,
                    "error": "No folder is being watched",
                    "error_type": "ValidationError",
                },
                status_code=400,
            )

        # Scan folder for supported files
        files_found = []
        for ext in server.folder_watcher.SUPPORTED_EXTENSIONS:
            files_found.extend(watched_path.rglob(f"*{ext}"))

        # Filter out hidden/temp files
        files_found = [
            f
            for f in files_found
            if not f.name.startswith(".") and not f.name.startswith("~")
        ]

        # Schedule each file for ingestion
        for file_path in files_found:
            await server.folder_watcher.schedule_ingestion(file_path)

        return {
            "success": True,
            "message": "Manual scan completed",
            "files_found": len(files_found),
            "watched_path": str(watched_path),
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to scan folder: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
