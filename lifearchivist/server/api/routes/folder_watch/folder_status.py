"""
Get folder status endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam

from lifearchivist.models.folder_watch import FolderResponse

from ..constants import PathParamDescriptions
from .get import get_folder

router = APIRouter()


@router.get("/folders/{folder_id}/status", response_model=FolderResponse)
async def get_folder_status(
    folder_id: str = PathParam(..., description=PathParamDescriptions.FOLDER_UUID),
):
    """
    Get detailed status for a specific folder.

    Args:
        folder_id: Folder UUID

    Returns:
        Folder status with detailed statistics

    Raises:
        404: Folder not found
        503: Folder watcher not initialized
        500: Internal server error

    Notes:
        - Alias for GET /folders/{folder_id}
        - Provided for semantic clarity
    """
    return await get_folder(folder_id)
