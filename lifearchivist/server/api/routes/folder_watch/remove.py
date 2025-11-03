"""
Remove folder endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam

from ..constants import (
    ErrorMessages,
    HTTPStatus,
    PathParamDescriptions,
    ResourceNames,
    ServiceNames,
    SuccessMessages,
)
from ..shared.dependencies import get_server

router = APIRouter()


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
