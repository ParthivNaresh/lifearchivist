"""
List folders endpoint.
"""

from fastapi import APIRouter, Query, status

from lifearchivist.models.folder_watch import FolderListResponse

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .utils import folder_to_response

router = APIRouter()


@router.get(
    "/folders",
    response_model=FolderListResponse,
    status_code=status.HTTP_200_OK,
    responses={
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
                    "example": {"detail": "List folders failed: <error message>"}
                }
            },
        },
    },
)
async def list_folders(
    enabled_only: bool = Query(
        default=False, description="Filter to only return enabled folders"
    ),
) -> FolderListResponse:
    """
    List all watched folders with their current status and statistics.

    Returns a list of all folders registered with the folder watcher service,
    optionally filtered to show only enabled folders.

    ## Query Parameters

    - **enabled_only**: If true, only return folders where enabled=true (default: false)

    ## Response Fields

    - **success**: Whether the request succeeded (always true for 200 responses)
    - **folders**: Array of folder objects, each containing:
      - id: Unique UUID
      - path: Absolute folder path
      - enabled: Whether watching is enabled
      - created_at: ISO timestamp when added
      - status: Current status (active/paused/error/stopped)
      - health: Health status (healthy/degraded/unhealthy/unreachable)
      - is_active: Whether actively watching
      - success_rate: File ingestion success rate (0.0-1.0)
      - stats: Detailed statistics
    - **total**: Total number of folders returned

    ## Example Response (All Folders)

    ```json
    {
        "success": true,
        "folders": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "path": "/Users/username/Documents/ToIngest",
                "enabled": true,
                "created_at": "2025-01-08T12:00:00Z",
                "status": "active",
                "health": "healthy",
                "is_active": true,
                "success_rate": 0.98,
                "stats": {...}
            },
            {
                "id": "223e4567-e89b-12d3-a456-426614174001",
                "path": "/Users/username/Downloads",
                "enabled": false,
                "created_at": "2025-01-07T10:00:00Z",
                "status": "stopped",
                "health": "healthy",
                "is_active": false,
                "success_rate": 1.0,
                "stats": {...}
            }
        ],
        "total": 2
    }
    ```

    ## Example Response (Enabled Only)

    ```
    GET /folders?enabled_only=true
    ```

    ```json
    {
        "success": true,
        "folders": [
            {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "path": "/Users/username/Documents/ToIngest",
                "enabled": true,
                "created_at": "2025-01-08T12:00:00Z",
                "status": "active",
                "health": "healthy",
                "is_active": true,
                "success_rate": 0.98,
                "stats": {...}
            }
        ],
        "total": 1
    }
    ```

    ## Use Cases

    - View all registered folders
    - Check which folders are currently enabled
    - Monitor overall folder watching status
    - Get aggregate statistics across folders
    - Verify folder configuration

    ## Notes

    - Returns empty array if no folders are registered
    - Folders are returned in no guaranteed order
    - Use enabled_only=true to see only active folders
    - Each folder includes full statistics
    - Total count reflects filtered results
    """
    server = get_server()

    if not server.folder_watcher:
        raise ServiceUnavailableError("Folder watcher")

    try:
        folders = await server.folder_watcher.list_folders(enabled_only=enabled_only)
        folder_responses = [folder_to_response(folder) for folder in folders]

        return FolderListResponse(
            success=True,
            folders=folder_responses,
            total=len(folder_responses),
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("List folders", e) from e
