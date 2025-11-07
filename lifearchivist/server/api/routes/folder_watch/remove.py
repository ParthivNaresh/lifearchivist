"""
Remove folder endpoint.
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
from .response_models import RemoveFolderResponse

router = APIRouter()


@router.delete(
    "/folders/{folder_id}",
    response_model=RemoveFolderResponse,
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
                    "example": {"detail": "Remove folder failed: <error message>"}
                }
            },
        },
    },
)
async def remove_folder(
    folder_id: str = PathParam(..., description="Unique folder UUID"),
) -> RemoveFolderResponse:
    """
    Remove a watched folder and stop all monitoring.

    Completely removes a folder from the folder watcher service. This stops all
    file monitoring, cancels pending ingestions, and removes the folder configuration.

    ## Path Parameters

    - **folder_id**: Unique UUID of the watched folder to remove

    ## Response Fields

    - **message**: Success confirmation message
    - **folder_id**: UUID of the removed folder

    ## Example Response

    ```json
    {
        "message": "Folder removed successfully",
        "folder_id": "123e4567-e89b-12d3-a456-426614174000"
    }
    ```

    ## Removal Process

    1. **Stop Watching**: If folder is actively being watched, stop the observer
    2. **Cancel Pending**: Cancel all pending file ingestions for this folder
    3. **Clean Resources**: Release all resources (handlers, observers, etc.)
    4. **Remove Config**: Delete folder configuration from persistent storage
    5. **Return Confirmation**: Confirm successful removal

    ## Use Cases

    - Remove folder that's no longer needed
    - Clean up after testing
    - Stop watching a folder temporarily (use update endpoint to disable instead)
    - Remove misconfigured folder
    - Free up system resources

    ## Important Notes

    - **Permanent Operation**: Folder configuration is permanently deleted
    - **Statistics Lost**: All accumulated statistics are deleted
    - **Pending Files**: Any pending ingestions are cancelled
    - **Active Watching**: Stops immediately if currently watching
    - **No Undo**: Cannot be undone - folder must be re-added
    - **Documents Remain**: Already ingested documents are NOT deleted from the vault

    ## Alternative

    If you want to temporarily stop watching without losing configuration:
    - Use `PATCH /folders/{folder_id}` with `{"enabled": false}` instead
    - This preserves statistics and allows easy re-enabling

    ## Notes

    - Returns 404 if folder UUID doesn't exist
    - Returns 200 OK on successful removal
    - Idempotent: removing non-existent folder returns 404
    - Safe to call even if folder is actively watching
    - All cleanup is automatic
    """
    server = get_server()

    if not server.folder_watcher:
        raise ServiceUnavailableError("Folder watcher")

    try:
        removed = await server.folder_watcher.remove_folder(folder_id)

        if not removed:
            raise ResourceNotFoundError("Folder", folder_id)

        return RemoveFolderResponse(
            message="Folder removed successfully",
            folder_id=folder_id,
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Remove folder", e) from e
