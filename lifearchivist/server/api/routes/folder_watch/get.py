"""
Get folder endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam

from lifearchivist.models.folder_watch import FolderResponse

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


@router.get("/folders/{folder_id}", response_model=FolderResponse)
async def get_folder(
    folder_id: str = PathParam(..., description=PathParamDescriptions.FOLDER_UUID),
):
    """
    Get details for a specific watched folder.

    Args:
        folder_id: Folder UUID

    Returns:
        Folder details with statistics

    Raises:
        404: Folder not found
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
        folder = await server.folder_watcher.get_folder(folder_id)

        if not folder:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=ErrorMessages.RESOURCE_NOT_FOUND.format(
                    resource=ResourceNames.FOLDER, identifier=folder_id
                ),
            )

        return folder_to_response(folder)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.OPERATION_FAILED.format(
                operation="get folder", error=str(e)
            ),
        ) from e
