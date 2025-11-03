"""
Bulk ingest files endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from .models import BulkIngestRequest

router = APIRouter()


@router.post("/bulk-ingest")
async def bulk_ingest_files(request: BulkIngestRequest):
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
        return JSONResponse(
            content={
                "success": False,
                "error": "No file paths provided",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if len(file_paths) > 1000:
        return JSONResponse(
            content={
                "success": False,
                "error": "Too many files. Maximum 1000 files per request.",
                "error_type": "ValidationError",
            },
            status_code=400,
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

        return {
            "success": True,
            "total_files": len(file_paths),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "success_rate": (
                round(successful_count / len(file_paths) * 100, 2) if file_paths else 0
            ),
            "folder_path": folder_path,
            "results": results,
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Bulk ingestion failed: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
