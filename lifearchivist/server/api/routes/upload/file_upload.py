"""
Upload file endpoint.
"""

import json
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    success_response,
    validation_error_response,
)

router = APIRouter()


@router.post("/")
async def upload_file(
    file: UploadFile = File(...),  # noqa: B008
    tags: str = Form("[]"),  # noqa: B008
    metadata: str = Form("{}"),  # noqa: B008
    session_id: Optional[str] = Form(None),  # noqa: B008
):
    """
    Upload and ingest a file with progress tracking.

    Accepts multipart form data with:
    - file: The file to upload
    - tags: JSON array of tags (default: [])
    - metadata: JSON object of metadata (default: {})
    - session_id: Optional session ID for progress tracking

    Process:
    1. Validates file and parses JSON parameters
    2. Saves file to temporary location
    3. Processes file through ingestion pipeline
    4. Cleans up temporary file
    5. Returns processing results
    """
    server = get_server()
    temp_file_path = None

    try:
        if not file.filename:
            return validation_error_response("No filename provided")

        try:
            tags_list = json.loads(tags)
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError as e:
            return validation_error_response(
                f"Invalid JSON in tags or metadata: {str(e)}"
            )

        if not isinstance(tags_list, list):
            return validation_error_response("Tags must be a JSON array")

        if not isinstance(metadata_dict, dict):
            return validation_error_response("Metadata must be a JSON object")

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=Path(file.filename).suffix
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

        if not result.get("success"):
            error_msg = result.get("error", "Upload failed")
            return internal_error_response("Upload file", RuntimeError(error_msg))

        return success_response(result["result"])

    except json.JSONDecodeError as e:
        return validation_error_response(f"JSON parsing error: {str(e)}")
    except Exception as e:
        return internal_error_response("Upload file", e)
    finally:
        if temp_file_path:
            try:
                Path(temp_file_path).unlink()
            except Exception:
                pass
