"""
Content extraction tool.
"""

import mimetypes
from pathlib import Path
from typing import Any, Dict

from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.tools.extract.extract_utils import (
    _extract_text_by_type,
    _get_extraction_method,
)
from lifearchivist.utils.logging import log_event, track


class ExtractTextTool(BaseTool):
    """Tool for extracting text from documents."""

    def __init__(self, vault):
        super().__init__()
        self.vault = vault

    def _get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="extract.text",
            description="Extract text from file",
            input_schema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "Document ID"},
                    "file_path": {
                        "type": "string",
                        "description": "Path to file (optional)",
                    },
                    "mime_type": {
                        "type": "string",
                        "description": "MIME type (optional)",
                    },
                    "file_hash": {
                        "type": "string",
                        "description": "File hash (optional)",
                    },
                },
                "required": ["file_id"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "metadata": {"type": "object"},
                },
            },
            async_tool=True,
            idempotent=True,
        )

    @track(
        operation="mime_type_detection",
        include_args=["file_id"],
        track_performance=True,
        emit_events=False,  # Silent operation - will log specific events manually
    )
    async def _resolve_file_info(
        self, file_id: str, file_path: str, mime_type: str, file_hash: str
    ) -> tuple[Path, str]:
        """Resolve file path and MIME type from provided parameters."""
        if file_path:
            # Direct file path provided
            actual_file_path = Path(file_path)

            if not mime_type:
                detected_mime_type = mimetypes.guess_type(str(actual_file_path))[0]
                if detected_mime_type:
                    log_event(
                        "mime_type_detected",
                        {
                            "file_id": file_id,
                            "mime_type": detected_mime_type,
                            "detection_method": "file_extension",
                        },
                    )
                    mime_type = detected_mime_type
                else:
                    log_event(
                        "mime_type_detection_failed",
                        {
                            "file_id": file_id,
                            "file_path": str(actual_file_path),
                        },
                    )
                    raise ValueError(
                        f"Could not detect MIME type for {actual_file_path}"
                    )
        else:
            # Use vault with file hash
            if not file_hash or not mime_type:
                raise ValueError(
                    "Either file_path or both file_hash and mime_type must be provided"
                )

            # Determine file extension from mime type
            extension = mimetypes.guess_extension(mime_type)
            if not extension:
                raise ValueError(
                    f"Could not determine extension from mime_type: {mime_type}"
                )

            if extension.startswith("."):
                extension = extension[1:]

            actual_file_path = await self.vault.get_file_path(file_hash, extension)

        # Verify file exists
        if not actual_file_path or not actual_file_path.exists():
            log_event(
                "file_not_found",
                {
                    "file_id": file_id,
                    "file_path": str(actual_file_path) if actual_file_path else "None",
                    "file_hash": file_hash,
                },
            )
            raise ValueError(f"File not found: {actual_file_path}")

        return actual_file_path, mime_type

    @track(
        operation="text_extraction_pipeline",
        include_args=["file_id"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Extract text from a document."""
        file_id = kwargs.get("file_id")
        file_path = kwargs.get("file_path")
        mime_type = kwargs.get("mime_type")
        file_hash = kwargs.get("file_hash")

        if not file_id:
            raise ValueError("File ID is required")

        # Resolve file path and MIME type
        actual_file_path, resolved_mime_type = await self._resolve_file_info(
            file_id, file_path, mime_type, file_hash
        )

        # Get file size for logging
        file_size = actual_file_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # Check if extraction is supported for this MIME type
        try:
            extraction_method = _get_extraction_method(resolved_mime_type)
            log_event(
                "text_extraction_supported",
                {
                    "file_id": file_id,
                    "mime_type": resolved_mime_type,
                    "extraction_method": extraction_method,
                    "file_size_mb": round(file_size_mb, 2),
                },
            )
        except ValueError as e:
            log_event(
                "text_extraction_skipped",
                {
                    "file_id": file_id,
                    "mime_type": resolved_mime_type,
                    "reason": "unsupported_format",
                },
            )
            raise ValueError(
                f"Text extraction not supported for {resolved_mime_type}"
            ) from e

        # Extract text using the appropriate method
        extracted_text = await _extract_text_by_type(
            actual_file_path, resolved_mime_type
        )

        # Calculate extraction metrics
        word_count = len(extracted_text.split()) if extracted_text else 0
        char_count = len(extracted_text) if extracted_text else 0
        has_text = bool(extracted_text and extracted_text.strip())

        log_event(
            "text_extraction_completed",
            {
                "file_id": file_id,
                "word_count": word_count,
                "has_text": has_text,
                "extraction_method": extraction_method,
            },
        )

        return {
            "text": extracted_text,
            "metadata": {
                "extraction_method": extraction_method,
                "word_count": word_count,
                "char_count": char_count,
                "language": "en",
                "file_size": file_size,
                "mime_type": resolved_mime_type,
            },
        }
