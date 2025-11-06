"""
Get folder status endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status

from lifearchivist.models.folder_watch import FolderResponse

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .utils import folder_to_response

router = APIRouter()


@router.get(
    "/folders/{folder_id}/status",
    response_model=FolderResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Folder not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Folder not found: invalid-uuid"}
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
                    "example": {"detail": "Get folder status failed: <error message>"}
                }
            },
        },
    },
)
async def get_folder_status(
    folder_id: str = PathParam(..., description="Unique folder UUID"),
) -> FolderResponse:
    """
    Get detailed status and statistics for a specific watched folder.

    Returns comprehensive information about a watched folder including its current
    status, health, and detailed statistics about file processing.

    ## Path Parameters

    - **folder_id**: Unique UUID of the watched folder

    ## Response Fields

    - **id**: Unique UUID for this watched folder
    - **path**: Absolute folder path
    - **enabled**: Whether watching is currently enabled
    - **created_at**: ISO timestamp when folder was added
    - **status**: Current status (active/paused/error/stopped)
    - **health**: Health status (healthy/degraded/unhealthy/unreachable)
    - **is_active**: Whether actively watching for changes
    - **success_rate**: File ingestion success rate (0.0-1.0)
    - **stats**: Detailed statistics object containing:
      - files_detected: Total files detected by watchdog
      - files_ingested: Successfully processed and indexed
      - files_skipped: Skipped (duplicates)
      - files_failed: Failed to process
      - bytes_processed: Total bytes successfully processed
      - last_activity: Last file event timestamp
      - last_success: Last successful ingestion timestamp
      - last_failure: Last failure timestamp
      - error_count: Consecutive errors (resets on success)
      - last_error: Last error message

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
        "success_rate": 0.95,
        "stats": {
            "files_detected": 100,
            "files_ingested": 95,
            "files_skipped": 3,
            "files_failed": 5,
            "bytes_processed": 52428800,
            "last_activity": "2025-01-08T14:30:00Z",
            "last_success": "2025-01-08T14:30:00Z",
            "last_failure": "2025-01-08T13:15:00Z",
            "error_count": 0,
            "last_error": ""
        }
    }
    ```

    ## Use Cases

    - Monitor folder health and activity
    - Check file processing statistics
    - Diagnose issues with folder watching
    - Track ingestion success rates
    - View error history

    ## Notes

    - Returns 404 if folder UUID doesn't exist
    - Statistics are cumulative since folder was added
    - Health status is calculated from error metrics
    - Success rate is files_ingested / (files_ingested + files_failed)
    - Status reflects current watching state
    """
    server = get_server()

    if not server.folder_watcher:
        raise ServiceUnavailableError("Folder watcher")

    try:
        folder = await server.folder_watcher.get_folder(folder_id)

        if not folder:
            raise ResourceNotFoundError("Folder", folder_id)

        return folder_to_response(folder)

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Get folder status", e) from e
