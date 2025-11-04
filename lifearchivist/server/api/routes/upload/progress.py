"""
Get upload progress endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    not_found_response,
    service_unavailable_response,
    success_response,
    validation_error_response,
)

router = APIRouter()


@router.get("/{file_id}/progress")
async def get_upload_progress(file_id: str):
    """
    Get upload progress for a specific file.

    Returns real-time progress information including:
    - Current processing stage
    - Percentage complete
    - Status (pending, processing, completed, failed)
    - Error messages if failed
    - Timestamps

    Used by frontend for:
    - Progress bars
    - Status updates
    - Error handling

    Progress is tracked via Redis and expires after completion.
    """
    server = get_server()

    if not file_id or len(file_id) < 3:
        return validation_error_response("Invalid file_id format")

    if not server.progress_manager:
        return service_unavailable_response("Progress tracking")

    try:
        progress = await server.progress_manager.get_progress(file_id)

        if not progress:
            return not_found_response("Progress", file_id)

        return success_response(progress.to_dict())

    except AttributeError as e:
        return internal_error_response(
            "Get progress", RuntimeError(f"Progress data format error: {str(e)}")
        )
    except Exception as e:
        return internal_error_response("Get progress", e)
