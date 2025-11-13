"""
Update folder endpoint.
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
from .request_models import UpdateFolderRequest
from .response_models import FolderResponse
from .utils import folder_to_response

router = APIRouter()


@router.patch(
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
                    "example": {"detail": "Update folder failed: <error message>"}
                }
            },
        },
    },
)
async def update_folder(
    request: UpdateFolderRequest,
    folder_id: str = PathParam(..., description="Unique folder UUID"),
) -> FolderResponse:
    """
    Update folder configuration (enable/disable watching).

    Allows toggling folder watching on or off without removing the folder configuration.
    This is useful for temporarily pausing monitoring while preserving statistics and settings.

    ## Path Parameters

    - **folder_id**: Unique UUID of the watched folder to update

    ## Request Body

    - **enabled**: Whether to enable (true) or disable (false) folder watching

    ## Response Fields

    Returns the updated folder with all current details:
    - **id**: Unique UUID
    - **path**: Absolute folder path
    - **enabled**: Updated enabled status
    - **created_at**: ISO timestamp when added
    - **status**: Current status (active/paused/error/stopped)
    - **health**: Health status
    - **is_active**: Whether actively watching
    - **success_rate**: File ingestion success rate
    - **stats**: Detailed statistics (preserved)

    ## Example Request (Enable)

    ```json
    {
        "enabled": true
    }
    ```

    ## Example Request (Disable)

    ```json
    {
        "enabled": false
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

    ## Enable Behavior

    When setting `enabled: true`:
    1. **Start Observer**: Watchdog observer starts monitoring the folder
    2. **Begin Watching**: New files are automatically detected
    3. **Queue Files**: Detected files are queued for ingestion
    4. **Update Status**: Status changes to "active"
    5. **Preserve Stats**: All existing statistics are preserved

    ## Disable Behavior

    When setting `enabled: false`:
    1. **Stop Observer**: Watchdog observer stops monitoring
    2. **Cancel Pending**: Pending file ingestions are cancelled
    3. **Release Resources**: Observer and handler resources are released
    4. **Update Status**: Status changes to "stopped"
    5. **Preserve Stats**: All statistics are preserved for later review

    ## Use Cases

    - Temporarily pause watching during maintenance
    - Stop watching while troubleshooting issues
    - Disable folder without losing statistics
    - Re-enable folder after adding files manually
    - Control resource usage by disabling unused folders

    ## Important Notes

    - **Statistics Preserved**: Disabling does NOT reset statistics
    - **Configuration Preserved**: Folder path and settings remain
    - **Pending Cancelled**: Disabling cancels pending ingestions
    - **Immediate Effect**: Changes take effect immediately
    - **Idempotent**: Setting same state is safe (no-op)
    - **No Path Change**: Cannot change folder path (remove and re-add instead)

    ## Comparison with Remove

    | Operation | Statistics | Configuration | Use Case |
    |-----------|-----------|---------------|----------|
    | **Update (disable)** | Preserved | Preserved | Temporary pause |
    | **Remove** | Deleted | Deleted | Permanent removal |

    ## Performance Notes

    - Fast operation (just state change)
    - Enabling may take a moment to start observer
    - Disabling is immediate
    - No file system scanning
    - Safe to call repeatedly

    ## Notes

    - Returns 404 if folder UUID doesn't exist
    - Currently only supports `enabled` field
    - Future: may support other configuration updates
    - Use remove endpoint to delete folder permanently
    - Use scan endpoint to process existing files after enabling
    """
    server = get_server()

    if not server.folder_watcher:
        raise ServiceUnavailableError("Folder watcher")

    try:
        folder = server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise ResourceNotFoundError("Folder", folder_id)

        if request.enabled is not None:
            if request.enabled:
                await server.folder_watcher.enable_folder(folder_id)
            else:
                await server.folder_watcher.disable_folder(folder_id)

        updated_folder = server.folder_watcher.get_folder(folder_id)
        if not updated_folder:
            raise InternalServerError(
                "Update folder",
                RuntimeError("Folder was updated but could not be retrieved"),
            )

        return folder_to_response(updated_folder)

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Update folder", e) from e
