"""
Add folder endpoint.
"""

from pathlib import Path

from fastapi import APIRouter

from lifearchivist.models.folder_watch import AddFolderRequest, FolderResponse

from ..constants import ErrorMessages, HTTPStatus, ResourceNames
from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, validation_error_response
from .utils import folder_to_response, validate_folder_watcher

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
    service, error_response = validate_folder_watcher(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        folder_path = Path(request.folder_path).expanduser().resolve()
    except Exception as e:
        return validation_error_response(
            ErrorMessages.INVALID_PATH.format(path_type="folder", error=str(e))
        )

    try:
        folder_id = await service.add_folder(
            path=folder_path,
            enabled=request.enabled,
        )

        folder = await service.get_folder(folder_id)
        if not folder:
            return internal_error_response(
                "Add folder",
                RuntimeError(
                    ErrorMessages.RESOURCE_ADDED_NOT_RETRIEVED.format(
                        resource=ResourceNames.FOLDER
                    )
                ),
            )

        return folder_to_response(folder)

    except ValueError as e:
        return validation_error_response(str(e))
    except Exception as e:
        return internal_error_response("Add folder", e)
