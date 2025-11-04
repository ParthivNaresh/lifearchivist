"""
Remove folder endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam

from ..constants import PathParamDescriptions, ResourceNames, SuccessMessages
from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    not_found_response,
    success_response,
)
from .utils import validate_folder_watcher

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
    service, error_response = validate_folder_watcher(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        removed = await service.remove_folder(folder_id)

        if not removed:
            return not_found_response(ResourceNames.FOLDER, folder_id)

        return success_response(
            {
                "message": SuccessMessages.RESOURCE_REMOVED.format(
                    resource=ResourceNames.FOLDER
                ),
                "folder_id": folder_id,
            }
        )

    except Exception as e:
        return internal_error_response("Remove folder", e)
