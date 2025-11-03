"""
Update folder endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam

from lifearchivist.models.folder_watch import FolderResponse, UpdateFolderRequest

from ..constants import (
    ErrorMessages,
    HTTPStatus,
    PathParamDescriptions,
    ResourceNames,
    ServiceNames,
)
from ..shared.dependencies import get_server
from .utils import folder_to_response

router = APIRouter()


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

        return folder_to_response(folder)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="update folder", error=str(e)
            ),
        ) from e
