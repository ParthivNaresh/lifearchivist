"""
Add folder endpoint.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from lifearchivist.models.folder_watch import AddFolderRequest, FolderResponse

from ..constants import (
    ErrorMessages,
    HTTPStatus,
    ResourceNames,
    ServiceNames,
)
from ..shared.dependencies import get_server
from .utils import folder_to_response

router = APIRouter()


@router.post("/folders", response_model=FolderResponse, status_code=HTTPStatus.CREATED)
async def add_folder(request: AddFolderRequest):
    """
    Add a new folder to watch.

    Args:
        request: Folder path and configuration

    Returns:
        Created folder details with UUID

    Raises:
        400: Invalid folder path or already watched
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
        folder_path = Path(request.folder_path).expanduser().resolve()
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ErrorMessages.INVALID_PATH.format(path_type="folder", error=str(e)),
        ) from e

    try:
        folder_id = await server.folder_watcher.add_folder(
            path=folder_path,
            enabled=request.enabled,
        )

        folder = await server.folder_watcher.get_folder(folder_id)
        if not folder:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=ErrorMessages.RESOURCE_ADDED_NOT_RETRIEVED.format(
                    resource=ResourceNames.FOLDER
                ),
            )

        return folder_to_response(folder)

    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="add folder", error=str(e)
            ),
        ) from e
