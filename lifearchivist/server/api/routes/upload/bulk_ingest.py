"""
Bulk ingest files endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ValidationError
from .constants import MAX_BULK_FILES
from .request_models import BulkIngestRequest
from .response_models import BulkIngestResponse

router = APIRouter()


@router.post(
    "/bulk-ingest",
    response_model=BulkIngestResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {"example": {"detail": "No file paths provided"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Bulk ingestion failed: <error>"}
                }
            },
        },
    },
)
async def bulk_ingest_files(request: BulkIngestRequest) -> BulkIngestResponse:
    """
    Bulk ingest multiple files from file paths.

    Processes multiple files in sequence:
    - Validates each file path
    - Imports each file independently
    - Continues processing even if individual files fail
    - Returns detailed results for each file

    Useful for:
    - Folder imports
    - Batch processing
    - Migration of existing documents

    Note: Files are processed sequentially, not in parallel.
    For large batches, consider using multiple requests.
    """
    server = get_server()
    file_paths = request.file_paths
    folder_path = request.folder_path

    if not file_paths:
        raise ValidationError("No file paths provided")

    if len(file_paths) > MAX_BULK_FILES:
        raise ValidationError(
            f"Too many files. Maximum {MAX_BULK_FILES} files per request."
        )

    results = []
    successful_count = 0
    failed_count = 0

    try:
        for file_path in file_paths:
            try:
                result = await server.execute_tool(
                    "file.import",
                    {
                        "path": file_path,
                        "tags": [],
                        "metadata": {
                            "source": "bulk_folder_upload",
                            "folder_path": folder_path,
                        },
                    },
                )

                if result.get("success"):
                    successful_count += 1
                    tool_result = result.get("result", {})
                    results.append(
                        {
                            "file_path": file_path,
                            "success": True,
                            "file_id": tool_result.get("file_id"),
                            "status": tool_result.get("status", "unknown"),
                        }
                    )
                else:
                    failed_count += 1
                    results.append(
                        {
                            "file_path": file_path,
                            "success": False,
                            "error": result.get("error", "Unknown error"),
                        }
                    )

            except Exception as e:
                failed_count += 1
                results.append(
                    {
                        "file_path": file_path,
                        "success": False,
                        "error": f"Processing error: {str(e)}",
                    }
                )

        return BulkIngestResponse(
            success=True,
            total_files=len(file_paths),
            successful=successful_count,
            failed=failed_count,
            results=results,
        )

    except ValidationError:
        raise
    except Exception as e:
        raise InternalServerError("Bulk ingestion", e) from e
