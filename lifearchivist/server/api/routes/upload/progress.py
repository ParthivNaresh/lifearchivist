"""
Get upload progress endpoint.
"""

from fastapi import APIRouter, Path, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .response_models import ProgressResponse

router = APIRouter()


@router.get(
    "/{file_id}/progress",
    response_model=ProgressResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {"example": {"detail": "Invalid file_id format"}}
            },
        },
        404: {
            "description": "Progress not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Progress not found: file_123"}
                }
            },
        },
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Progress tracking not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Get progress failed: <error>"}
                }
            },
        },
    },
)
async def get_upload_progress(
    file_id: str = Path(..., description="File identifier for progress tracking"),
) -> ProgressResponse:
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
        raise ValidationError("Invalid file_id format")

    if not server.progress_manager:
        raise ServiceUnavailableError("Progress tracking")

    try:
        progress = await server.progress_manager.get_progress(file_id)

        if not progress:
            raise ResourceNotFoundError("Progress", file_id)

        progress_dict = progress.to_dict()
        return ProgressResponse(
            session_id=file_id,
            progress=progress_dict.get("progress", 0.0),
            status=progress_dict.get("status", "unknown"),
            message=progress_dict.get("message"),
            completed=progress_dict.get("completed", False),
        )

    except (ValidationError, ResourceNotFoundError, ServiceUnavailableError):
        raise
    except AttributeError as e:
        raise InternalServerError(
            "Get progress", RuntimeError(f"Progress data format error: {str(e)}")
        ) from e
    except Exception as e:
        raise InternalServerError("Get progress", e) from e
