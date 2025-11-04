"""
List folders endpoint.
"""

from fastapi import APIRouter

from lifearchivist.models.folder_watch import FolderListResponse

from ..constants import FolderWatchConstants
from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response
from .utils import folder_to_response, validate_folder_watcher

router = APIRouter()


@router.get("/folders", response_model=FolderListResponse)
async def list_folders(
    enabled_only: bool = FolderWatchConstants.DEFAULT_ENABLED_ONLY_FILTER,
):
    """
    List all watched folders.

    Args:
        enabled_only: If true, only return enabled folders

    Returns:
        List of watched folders with statistics

    Raises:
        503: Folder watcher not initialized
        500: Internal server error
    """
    server = get_server()
    service, error_response = validate_folder_watcher(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        folders = await service.list_folders(enabled_only=enabled_only)
        folder_responses = [folder_to_response(folder) for folder in folders]

        return FolderListResponse(
            success=True,
            folders=folder_responses,
            total=len(folder_responses),
        )

    except Exception as e:
        return internal_error_response("List folders", e)
