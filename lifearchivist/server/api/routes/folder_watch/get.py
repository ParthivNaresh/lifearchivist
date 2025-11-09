"""
Get folder endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .response_models import FolderResponse
from .utils import folder_to_response

router = APIRouter()


@router.get(
    "/folders/{folder_id}",
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
                    "example": {"detail": "Get folder failed: <error message>"}
                }
            },
        },
    },
)
async def get_folder(
    folder_id: str = PathParam(..., description="Unique folder UUID"),
) -> FolderResponse:
    """
    Get details and statistics for a specific watched folder.

    Retrieves comprehensive information about a watched folder including its
    configuration, current status, health metrics, and processing statistics.

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
    - **stats**: Detailed statistics object

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
        "success_rate": 0.98,
        "stats": {
            "files_detected": 50,
            "files_ingested": 49,
            "files_skipped": 0,
            "files_failed": 1,
            "bytes_processed": 26214400,
            "last_activity": "2025-01-08T14:00:00Z",
            "last_success": "2025-01-08T14:00:00Z",
            "last_failure": "2025-01-08T12:30:00Z",
            "error_count": 0,
            "last_error": ""
        }
    }
    ```

    ## Use Cases

    - Retrieve folder configuration
    - Check current watching status
    - View processing statistics
    - Monitor folder health
    - Verify folder exists

    ## Notes

    - Returns 404 if folder UUID doesn't exist
    - All statistics are cumulative since folder was added
    - Health status is automatically calculated from error metrics
    - Status reflects whether folder is actively being watched
    - Use this endpoint to verify folder was added successfully
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
        raise InternalServerError("Get folder", e) from e
