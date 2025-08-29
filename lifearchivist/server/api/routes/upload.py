"""
File upload and ingestion endpoints.
"""

import json
import logging
import tempfile
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from lifearchivist.models import IngestRequest
from lifearchivist.utils.logging import log_context, log_event
from lifearchivist.utils.logging.structured import MetricsCollector

from ..dependencies import get_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/ingest")
async def ingest_document(request: IngestRequest):
    """Ingest a document from file path."""
    with log_context(
        operation="api_document_ingest",
        file_path=request.path,
        has_session_id=bool(request.session_id),
    ):

        metrics = MetricsCollector("api_document_ingest")
        metrics.start()

        server = get_server()

        # Extract session_id for progress tracking
        params = request.model_dump()
        session_id = params.pop("session_id", None)

        # Add session_id as a direct parameter for progress tracking
        if session_id:
            params["session_id"] = session_id

        metrics.add_metric("file_path", request.path)
        metrics.add_metric("has_session_id", bool(session_id))
        metrics.add_metric("param_count", len(params))

        log_event(
            "api_ingest_started",
            {
                "file_path": request.path,
                "has_session_id": bool(session_id),
                "params_keys": list(params.keys()),
            },
        )

        try:
            result = await server.execute_tool("file.import", params)

            if result["success"]:
                file_id = result["result"].get("file_id")
                metrics.add_metric("file_id", file_id)
                metrics.set_success(True)
                metrics.report("api_ingest_completed")

                log_event(
                    "api_ingest_successful",
                    {"file_id": file_id, "file_path": request.path},
                )
                return result["result"]
            else:
                error_msg = result["error"]
                metrics.set_error(RuntimeError(error_msg))
                metrics.report("api_ingest_failed")

                log_event(
                    "api_ingest_tool_failed",
                    {"error_message": error_msg, "file_path": request.path},
                )
                raise HTTPException(status_code=500, detail=error_msg)

        except HTTPException:
            raise
        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_ingest_failed")

            log_event(
                "api_ingest_exception",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "file_path": request.path,
                },
            )
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
    with log_context(
        operation="api_file_upload",
        filename=file.filename,
        content_type=file.content_type,
        has_session_id=bool(session_id),
    ):

        metrics = MetricsCollector("api_file_upload")
        metrics.start()

        server = get_server()
        temp_file_path = None

        metrics.add_metric("filename", file.filename)
        metrics.add_metric("content_type", file.content_type)
        metrics.add_metric("has_session_id", bool(session_id))

        log_event(
            "api_upload_started",
            {
                "filename": file.filename,
                "content_type": file.content_type,
                "has_session_id": bool(session_id),
            },
        )

        try:
            # Parse JSON strings
            try:
                tags_list = json.loads(tags)
                metadata_dict = json.loads(metadata)

                metrics.add_metric("tags_count", len(tags_list))
                metrics.add_metric("metadata_keys_count", len(metadata_dict))

                log_event(
                    "upload_json_parsed",
                    {
                        "tags_count": len(tags_list),
                        "metadata_keys": list(metadata_dict.keys()),
                    },
                )
            except json.JSONDecodeError as e:
                log_event(
                    "upload_json_parse_error",
                    {
                        "error_message": str(e),
                        "tags_preview": tags[:100] + "..." if len(tags) > 100 else tags,
                        "metadata_preview": (
                            metadata[:100] + "..." if len(metadata) > 100 else metadata
                        ),
                    },
                )
                metrics.set_error(e)
                metrics.report("api_upload_failed")
                raise HTTPException(
                    status_code=400, detail=f"Invalid JSON in tags or metadata: {e}"
                ) from None

            # Create temporary file
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=Path(file.filename).suffix
            ) as temp_file:
                temp_file_path = temp_file.name

                # Write uploaded content to temp file
                content = await file.read()
                temp_file.write(content)
                temp_file.flush()

                content_size = len(content)
                metrics.add_metric("file_size_bytes", content_size)

                log_event(
                    "temp_file_created",
                    {
                        "temp_path": temp_file.name,
                        "file_size_bytes": content_size,
                        "filename": file.filename,
                    },
                )

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

                log_event(
                    "file_import_started",
                    {
                        "temp_path": temp_file.name,
                        "original_filename": file.filename,
                        "has_session_id": bool(session_id),
                    },
                )

                result = await server.execute_tool("file.import", import_params)
                metrics.add_metric("tool_execution_completed", True)

                if result["success"]:
                    file_id = result["result"].get("file_id")
                    metrics.add_metric("file_id", file_id)
                    metrics.set_success(True)

                    log_event(
                        "api_upload_successful",
                        {
                            "file_id": file_id,
                            "original_filename": file.filename,
                            "file_size_bytes": content_size,
                        },
                    )

                    return result["result"]
                else:
                    error_msg = result["error"]
                    metrics.set_error(RuntimeError(error_msg))

                    log_event(
                        "file_import_tool_failed",
                        {"error_message": error_msg, "filename": file.filename},
                    )
                    raise HTTPException(status_code=500, detail=error_msg)

        except HTTPException:
            raise
        except Exception as e:
            metrics.set_error(e)
            log_event(
                "api_upload_exception",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "filename": file.filename,
                },
            )
            raise HTTPException(status_code=500, detail=str(e)) from None
        finally:
            # Clean up temp file
            if temp_file_path:
                try:
                    Path(temp_file_path).unlink()
                    log_event(
                        "temp_file_cleanup_successful", {"temp_path": temp_file_path}
                    )
                except Exception as cleanup_error:
                    log_event(
                        "temp_file_cleanup_failed",
                        {
                            "temp_path": temp_file_path,
                            "cleanup_error": str(cleanup_error),
                        },
                    )

            metrics.report("api_upload_completed")


class BulkIngestRequest(BaseModel):
    file_paths: List[str]
    folder_path: str = ""


@router.post("/bulk-ingest")
async def bulk_ingest_files(request: BulkIngestRequest):
    """Bulk ingest multiple files from file paths."""
    with log_context(
        operation="api_bulk_ingest",
        total_files=len(request.file_paths),
        folder_path=request.folder_path,
    ):

        metrics = MetricsCollector("api_bulk_ingest")
        metrics.start()

        server = get_server()
        file_paths = request.file_paths
        folder_path = request.folder_path

        metrics.add_metric("total_files", len(file_paths))
        metrics.add_metric("folder_path", folder_path)

        if not file_paths:
            log_event("bulk_ingest_no_files", {"folder_path": folder_path})
            metrics.set_error(ValueError("No file paths provided"))
            metrics.report("api_bulk_ingest_failed")
            raise HTTPException(status_code=400, detail="No file paths provided")

        log_event(
            "bulk_ingest_started",
            {"total_files": len(file_paths), "folder_path": folder_path},
        )

        results = []
        successful_count = 0
        failed_count = 0

        try:
            for i, file_path in enumerate(file_paths):
                log_event(
                    "bulk_ingest_file_processing",
                    {
                        "file_index": i + 1,
                        "total_files": len(file_paths),
                        "file_path": file_path,
                    },
                )

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
                        file_id = result["result"]["file_id"]

                        log_event(
                            "bulk_ingest_file_successful",
                            {
                                "file_path": file_path,
                                "file_id": file_id,
                                "progress": f"{i+1}/{len(file_paths)}",
                            },
                        )

                        results.append(
                            {
                                "file_path": file_path,
                                "success": True,
                                "file_id": file_id,
                                "status": result["result"]["status"],
                            }
                        )
                    else:
                        failed_count += 1
                        error_msg = result.get("error", "Unknown error")

                        log_event(
                            "bulk_ingest_file_failed",
                            {
                                "file_path": file_path,
                                "error_message": error_msg,
                                "progress": f"{i+1}/{len(file_paths)}",
                            },
                        )

                        results.append(
                            {
                                "file_path": file_path,
                                "success": False,
                                "error": error_msg,
                            }
                        )

                except Exception as e:
                    failed_count += 1

                    log_event(
                        "bulk_ingest_file_exception",
                        {
                            "file_path": file_path,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "progress": f"{i+1}/{len(file_paths)}",
                        },
                    )

                    results.append(
                        {"file_path": file_path, "success": False, "error": str(e)}
                    )

            # Record final metrics
            metrics.add_metric("successful_count", successful_count)
            metrics.add_metric("failed_count", failed_count)
            metrics.add_metric(
                "success_rate", successful_count / len(file_paths) if file_paths else 0
            )
            metrics.set_success(True)
            metrics.report("api_bulk_ingest_completed")

            log_event(
                "bulk_ingest_completed",
                {
                    "total_files": len(file_paths),
                    "successful_count": successful_count,
                    "failed_count": failed_count,
                    "success_rate": (
                        round(successful_count / len(file_paths) * 100, 1)
                        if file_paths
                        else 0
                    ),
                },
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
            metrics.set_error(e)
            metrics.report("api_bulk_ingest_failed")

            log_event(
                "bulk_ingest_exception",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "processed_files": successful_count + failed_count,
                    "total_files": len(file_paths),
                },
            )
            raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/upload/{file_id}/progress")
async def get_upload_progress(file_id: str):
    """Get upload progress for a specific file."""
    with log_context(operation="api_progress_check", file_id=file_id):

        metrics = MetricsCollector("api_progress_check")
        metrics.start()

        server = get_server()

        metrics.add_metric("file_id", file_id)

        log_event("progress_check_started", {"file_id": file_id})

        try:
            if not server.progress_manager:
                log_event(
                    "progress_manager_unavailable",
                    {"file_id": file_id, "reason": "progress_manager_disabled"},
                )
                metrics.set_error(RuntimeError("Progress manager not available"))
                metrics.report("api_progress_check_failed")
                raise HTTPException(
                    status_code=503, detail="Progress tracking not available"
                )

            progress = await server.progress_manager.get_progress(file_id)
            if not progress:
                log_event("progress_not_found", {"file_id": file_id})
                metrics.set_error(KeyError("Progress not found"))
                metrics.report("api_progress_check_failed")
                raise HTTPException(status_code=404, detail="Progress not found")

            progress_dict = progress.to_dict()
            metrics.add_metric("progress_stage", progress_dict.get("stage", "unknown"))
            metrics.add_metric(
                "progress_percentage", progress_dict.get("percentage", 0)
            )
            metrics.set_success(True)
            metrics.report("api_progress_check_completed")

            log_event(
                "progress_check_successful",
                {
                    "file_id": file_id,
                    "stage": progress_dict.get("stage", "unknown"),
                    "percentage": progress_dict.get("percentage", 0),
                },
            )

            return progress_dict

        except HTTPException:
            raise
        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_progress_check_failed")

            log_event(
                "progress_check_exception",
                {
                    "file_id": file_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise HTTPException(status_code=500, detail=str(e)) from None
