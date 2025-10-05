"""
File upload and ingestion endpoints.
"""

import json
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lifearchivist.models import IngestRequest

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/ingest")
async def ingest_document(request: IngestRequest):
    """Ingest a document from file path."""
    server = get_server()

    params = request.model_dump()
    session_id = params.pop("session_id", None)

    if session_id:
        params["session_id"] = session_id

    try:
        result = await server.execute_tool("file.import", params)

        if not result["success"]:
            error_msg = result.get("error", "Import failed")
            return JSONResponse(
                content={
                    "success": False,
                    "error": error_msg,
                    "error_type": "ImportError",
                },
                status_code=500,
            )

        return result["result"]

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),  # noqa: B008
    tags: str = Form("[]"),  # noqa: B008
    metadata: str = Form("{}"),  # noqa: B008
    session_id: Optional[str] = Form(None),  # noqa: B008
):
    """Upload and ingest a file with progress tracking."""
    server = get_server()
    temp_file_path = None

    try:
        # Parse JSON strings
        try:
            tags_list = json.loads(tags)
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError as e:
            return JSONResponse(
                content={
                    "success": False,
                    "error": f"Invalid JSON in tags or metadata: {str(e)}",
                    "error_type": "ValidationError",
                },
                status_code=400,
            )

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename or "").suffix
        ) as temp_file:
            temp_file_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()

            import os

            os.fsync(temp_file.fileno())

        import_params = {
            "path": temp_file_path,
            "tags": tags_list,
            "metadata": {
                **metadata_dict,
                "original_filename": file.filename,
            },
            "session_id": session_id,
        }
        result = await server.execute_tool("file.import", import_params)

        if not result["success"]:
            error_msg = result.get("error", "Upload failed")
            return JSONResponse(
                content={
                    "success": False,
                    "error": error_msg,
                    "error_type": "UploadError",
                },
                status_code=500,
            )

        return result["result"]

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )
    finally:
        if temp_file_path:
            try:
                Path(temp_file_path).unlink()
            except Exception:
                pass


class BulkIngestRequest(BaseModel):
    file_paths: List[str]
    folder_path: str = ""


@router.post("/bulk-ingest")
async def bulk_ingest_files(request: BulkIngestRequest):
    """Bulk ingest multiple files from file paths."""
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
                    {"file_path": file_path, "success": False, "error": str(e)}
                )

        return {
            "success": True,
            "total_files": len(file_paths),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "folder_path": folder_path,
            "results": results,
        }

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )


@router.get("/upload/{file_id}/progress")
async def get_upload_progress(file_id: str):
    """Get upload progress for a specific file."""
    server = get_server()

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
                    "error": "Progress not found",
                    "error_type": "NotFoundError",
                },
                status_code=404,
            )

        return progress.to_dict()

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )
