"""
List folders endpoint.
"""

from fastapi import APIRouter, HTTPException

from lifearchivist.models.folder_watch import FolderListResponse

from ..constants import (
    ErrorMessages,
    FolderWatchConstants,
    HTTPStatus,
    ServiceNames,
)
from ..shared.dependencies import get_server
from .utils import folder_to_response

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

    if not server.folder_watcher:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=ErrorMessages.SERVICE_NOT_INITIALIZED.format(
                service=ServiceNames.FOLDER_WATCHER
            ),
        )

    try:
        folders = await server.folder_watcher.list_folders(enabled_only=enabled_only)
        folder_responses = [folder_to_response(folder) for folder in folders]

        return FolderListResponse(
            success=True,
            folders=folder_responses,
            total=len(folder_responses),
        )

    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="list folders", error=str(e)
            ),
        ) from e
