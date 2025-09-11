"""
File upload and ingestion endpoints.
"""

import json
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from lifearchivist.models import IngestRequest

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/ingest")
async def ingest_document(request: IngestRequest):
    """Ingest a document from file path."""

    server = get_server()

    # Extract session_id for progress tracking
    params = request.model_dump()
    session_id = params.pop("session_id", None)

    # Add session_id as a direct parameter for progress tracking
    if session_id:
        params["session_id"] = session_id

    try:
        result = await server.execute_tool("file.import", params)

        if result["success"]:
            return result["result"]
        else:
            error_msg = result["error"]
            raise HTTPException(status_code=500, detail=error_msg)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),  # noqa: B008  # FastAPI dependency injection pattern
    tags: str = Form("[]"),  # noqa: B008  # FastAPI dependency injection pattern
    metadata: str = Form("{}"),  # noqa: B008  # FastAPI dependency injection pattern
    session_id: Optional[str] = Form(
        None
    ),  # noqa: B008  # FastAPI dependency injection pattern
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
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON in tags or metadata: {e}"
            ) from None

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename or "").suffix
        ) as temp_file:
            temp_file_path = temp_file.name

            # Write uploaded content to temp file
            content = await file.read()
            temp_file.write(content)
            temp_file.flush()

            # Import the temporary file with progress tracking
            import_params = {
                "path": temp_file.name,
                "tags": tags_list,
                "metadata": {
                    **metadata_dict,
                    "original_filename": file.filename,
                },
                "session_id": session_id,
            }
            result = await server.execute_tool("file.import", import_params)

            if result["success"]:
                return result["result"]
            else:
                error_msg = result["error"]
                raise HTTPException(status_code=500, detail=error_msg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
    finally:
        # Clean up temp file
        if temp_file_path:
            try:
                Path(temp_file_path).unlink()
            except Exception as cleanup_error:
                raise cleanup_error


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
        raise HTTPException(status_code=400, detail="No file paths provided")

    results = []
    successful_count = 0
    failed_count = 0

    try:
        for _, file_path in enumerate(file_paths):
            try:
                # Use the file import tool
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
                    file_id = tool_result.get("file_id")
                    results.append(
                        {
                            "file_path": file_path,
                            "success": True,
                            "file_id": file_id,
                            "status": tool_result.get("status", "unknown"),
                        }
                    )
                else:
                    failed_count += 1
                    error_msg = result.get("error", "Unknown error")

                    results.append(
                        {
                            "file_path": file_path,
                            "success": False,
                            "error": error_msg,
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
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/upload/{file_id}/progress")
async def get_upload_progress(file_id: str):
    """Get upload progress for a specific file."""
    server = get_server()
    try:
        if not server.progress_manager:
            raise HTTPException(
                status_code=503, detail="Progress tracking not available"
            )

        progress = await server.progress_manager.get_progress(file_id)
        if not progress:
            raise HTTPException(status_code=404, detail="Progress not found")

        progress_dict = progress.to_dict()
        return progress_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
