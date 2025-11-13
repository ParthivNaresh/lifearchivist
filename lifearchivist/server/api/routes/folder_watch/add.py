"""
Add folder endpoint.
"""

from pathlib import Path

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ServiceUnavailableError,
    ValidationError,
)
from .request_models import AddFolderRequest
from .response_models import FolderResponse
from .utils import folder_to_response

router = APIRouter()


@router.post(
    "/folders",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "Invalid folder path or already watched",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid folder path: /invalid/path"}
                }
            },
        },
        503: {
            "description": "Folder watcher service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Folder watcher not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Add folder failed: <error message>"}
                }
            },
        },
    },
)
async def add_folder(request: AddFolderRequest) -> FolderResponse:
    """
    Add a new folder to watch for automatic document ingestion.

    Registers a folder path with the folder watcher service. When enabled, the service
    will automatically detect and ingest new documents added to this folder.

    ## Request Body

    - **folder_path**: Absolute path to the folder to watch (supports ~ expansion)
    - **enabled**: Whether to start watching immediately (default: true)

    ## Response Fields

    - **id**: Unique UUID for this watched folder
    - **path**: Resolved absolute folder path
    - **enabled**: Whether watching is currently enabled
    - **created_at**: ISO timestamp when folder was added
    - **status**: Current status (active/paused/error/stopped)
    - **health**: Health status (healthy/degraded/unhealthy/unreachable)
    - **is_active**: Whether actively watching for changes
    - **success_rate**: File ingestion success rate (0.0-1.0)
    - **stats**: Detailed statistics (files detected, ingested, failed, etc.)

    ## Example Request

    ```json
    {
        "folder_path": "~/Documents/ToIngest",
        "enabled": true
    }
    ```

    ## Example Response

    ```json
    {
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "path": "/Users/username/Documents/ToIngest",
        "enabled": true,
        "created_at": "2025-01-08T12:00:00Z",
        "status": "active",
        "health": "healthy",
        "is_active": true,
        "success_rate": 1.0,
        "stats": {
            "files_detected": 0,
            "files_ingested": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "bytes_processed": 0,
            "last_activity": null,
            "last_success": null,
            "last_failure": null,
            "error_count": 0,
            "last_error": ""
        }
    }
    ```

    ## Behavior

    - Path is expanded (~ becomes home directory) and resolved to absolute path
    - Folder must exist and be accessible
    - Cannot add the same folder twice (returns 400)
    - If enabled=true, watching starts immediately
    - If enabled=false, folder is registered but not actively watched
    - Supports all document types configured in the system

    ## Notes

    - Returns 201 Created on success
    - Folder path is validated and must exist
    - Duplicate folders are rejected (400 error)
    - Watching can be enabled/disabled later via update endpoint
    - Statistics start at zero and accumulate over time
    - Health status is initially "healthy"
    """
    server = get_server()

    if not server.folder_watcher:
        raise ServiceUnavailableError("Folder watcher")

    if not request.folder_path or not request.folder_path.strip():
        raise ValidationError("Folder path cannot be empty")

    try:
        folder_path = Path(request.folder_path).expanduser().resolve()
    except Exception as e:
        raise ValidationError(f"Invalid folder path: {str(e)}") from e

    try:
        folder_id = await server.folder_watcher.add_folder(
            path=folder_path,
            enabled=request.enabled,
        )

        folder = server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise InternalServerError(
                "Add folder",
                RuntimeError("Folder was added but could not be retrieved"),
            )

        return folder_to_response(folder)

    except ValueError as e:
        raise ValidationError(str(e)) from e
    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Add folder", e) from e
