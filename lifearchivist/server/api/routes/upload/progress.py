"""
Get upload progress endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

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
        return JSONResponse(
            content={
                "success": False,
                "error": "Invalid file_id format",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if not server.progress_manager:
        return JSONResponse(
            content={
                "success": False,
                "error": "Progress tracking not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        progress = await server.progress_manager.get_progress(file_id)

        if not progress:
            return JSONResponse(
                content={
                    "success": False,
                    "error": f"Progress not found for file_id: {file_id}",
                    "error_type": "NotFoundError",
                },
                status_code=404,
            )

        return {"success": True, **progress.to_dict()}

    except AttributeError as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Progress data format error: {str(e)}",
                "error_type": "DataError",
            },
            status_code=500,
        )
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to retrieve progress: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
