"""
Upload file endpoint.
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Optional

import aiofiles
import aiofiles.os
from fastapi import APIRouter, File, Form, UploadFile, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ValidationError
from .response_models import FileUploadResponse

router = APIRouter()


class FileUploadHandler:
    """Handles file upload and processing workflow."""

    def __init__(
        self,
        server,
        file: UploadFile,
        tags: str,
        metadata: str,
        session_id: Optional[str],
    ):
        self.server = server
        self.file = file
        self.tags = tags
        self.metadata = metadata
        self.session_id = session_id
        self.temp_file_path: Optional[str] = None

    def validate_file(self) -> None:
        """Validate the uploaded file."""
        if not self.file.filename:
            raise ValidationError("No filename provided")

    def parse_json_parameters(self) -> tuple[list, dict]:
        """Parse and validate JSON parameters."""
        try:
            tags_list = json.loads(self.tags)
            metadata_dict = json.loads(self.metadata)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in tags or metadata: {str(e)}") from e

        if not isinstance(tags_list, list):
            raise ValidationError("Tags must be a JSON array")

        if not isinstance(metadata_dict, dict):
            raise ValidationError("Metadata must be a JSON object")

        return tags_list, metadata_dict

    async def save_to_temp_file(self, content: bytes) -> str:
        """Save uploaded content to a temporary file asynchronously."""
        if not self.file.filename:
            raise ValidationError("Filename is required")

        suffix = Path(self.file.filename).suffix
        fd, temp_path = tempfile.mkstemp(suffix=suffix)

        try:
            async with aiofiles.open(temp_path, "wb") as temp_file:
                await temp_file.write(content)
                await temp_file.flush()
                # Use os.fsync directly since aiofiles.os doesn't have fsync
                os.fsync(temp_file.fileno())
        finally:
            os.close(fd)

        return temp_path

    async def process_file(
        self, tags_list: list, metadata_dict: dict, content: bytes
    ) -> None:
        """Process the uploaded file through the ingestion pipeline."""
        import_params = {
            "path": self.temp_file_path,
            "tags": tags_list,
            "metadata": {
                **metadata_dict,
                "original_filename": self.file.filename,
            },
            "session_id": self.session_id,
        }

        result = await self.server.execute_tool("file.import", import_params)

        if not result.get("success"):
            error_msg = result.get("error", "Upload failed")
            raise InternalServerError("Upload file", RuntimeError(error_msg))

    async def cleanup_temp_file(self) -> None:
        """Clean up the temporary file asynchronously."""
        if self.temp_file_path:
            try:
                await aiofiles.os.remove(self.temp_file_path)
            except Exception:
                pass

    def create_response(self, content_size: int) -> FileUploadResponse:
        """Create the upload response."""
        if not self.file.filename or not self.temp_file_path:
            raise ValidationError("Missing filename or file path")

        return FileUploadResponse(
            success=True,
            filename=self.file.filename,
            file_path=self.temp_file_path,
            file_size=content_size,
            mime_type=self.file.content_type,
        )


@router.post(
    "/",
    response_model=FileUploadResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {"example": {"detail": "No filename provided"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Upload file failed: <error>"}
                }
            },
        },
    },
)
async def upload_file(
    file: UploadFile = File(...),  # noqa: B008
    tags: str = Form("[]"),  # noqa: B008
    metadata: str = Form("{}"),  # noqa: B008
    session_id: Optional[str] = Form(None),  # noqa: B008
) -> FileUploadResponse:
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
    handler = FileUploadHandler(server, file, tags, metadata, session_id)

    try:
        handler.validate_file()
        tags_list, metadata_dict = handler.parse_json_parameters()

        content = await file.read()
        handler.temp_file_path = await handler.save_to_temp_file(content)

        await handler.process_file(tags_list, metadata_dict, content)

        return handler.create_response(len(content))

    except (ValidationError, InternalServerError):
        raise
    except json.JSONDecodeError as e:
        raise ValidationError(f"JSON parsing error: {str(e)}") from e
    except Exception as e:
        raise InternalServerError("Upload file", e) from e
    finally:
        await handler.cleanup_temp_file()
