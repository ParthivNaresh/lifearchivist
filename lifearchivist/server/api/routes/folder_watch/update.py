"""
Update folder endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam

from lifearchivist.models.folder_watch import FolderResponse, UpdateFolderRequest

from ..constants import PathParamDescriptions, ResourceNames
from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, not_found_response
from .utils import folder_to_response, validate_folder_watcher

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
    service, error_response = validate_folder_watcher(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        folder = await service.get_folder(folder_id)
        if not folder:
            return not_found_response(ResourceNames.FOLDER, folder_id)

        if request.enabled is not None:
            if request.enabled:
                await service.enable_folder(folder_id)
            else:
                await service.disable_folder(folder_id)

        return folder_to_response(folder)

    except Exception as e:
        return internal_error_response("Update folder", e)
