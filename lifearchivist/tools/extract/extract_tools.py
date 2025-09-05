"""
Content extraction tools.
"""

import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict

from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.tools.extract.extract_utils import (
    _extract_text_by_type,
    _get_extraction_method,
)
from lifearchivist.utils.logging import log_context, log_method
from lifearchivist.utils.logging.structured import MetricsCollector

logger = logging.getLogger(__name__)


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

    @log_method(
        operation_name="text_extraction",
        include_args=True,
        include_result=True,
        indent=2,
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Extract text from a document."""
        file_id = kwargs.get("file_id")
        file_path = kwargs.get("file_path")
        mime_type = kwargs.get("mime_type")
        file_hash = kwargs.get("file_hash")

        if not file_id:
            raise ValueError("File ID is required")

        with log_context(
            operation="text_extraction",
            file_id=file_id,
            mime_type=mime_type or "unknown",
            has_file_path=bool(file_path),
            has_file_hash=bool(file_hash),
        ):

            metrics = MetricsCollector("text_extraction")
            metrics.start()

            metrics.add_metric("file_id", file_id)
            metrics.add_metric("has_file_path", bool(file_path))
            metrics.add_metric("has_file_hash", bool(file_hash))
            metrics.add_metric("initial_mime_type", mime_type or "unknown")

            try:
                if file_path:
                    # Direct file path provided
                    actual_file_path = Path(file_path)

                    if not mime_type:
                        mime_type = mimetypes.guess_type(str(actual_file_path))[0]

                    metrics.add_metric("file_path_provided", True)
                    metrics.add_metric("detected_mime_type", mime_type or "unknown")
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

                    actual_file_path = await self.vault.get_file_path(
                        file_hash, extension
                    )
                    metrics.add_metric("file_path_provided", False)
                    metrics.add_metric("extension_detected", extension)

                # Verify file exists
                if not actual_file_path or not actual_file_path.exists():
                    raise ValueError(f"File not found: {actual_file_path}")

                # Get file size before extraction
                file_size = actual_file_path.stat().st_size
                metrics.add_metric("file_size_bytes", file_size)

                # Extract text using the appropriate method
                extracted_text = await _extract_text_by_type(
                    actual_file_path, str(mime_type)
                )

                # Calculate extraction metrics
                word_count = len(extracted_text.split()) if extracted_text else 0
                text_length = len(extracted_text) if extracted_text else 0
                extraction_method = _get_extraction_method(str(mime_type))

                metrics.add_metric("word_count", word_count)
                metrics.add_metric("text_length", text_length)
                metrics.add_metric("extraction_method", extraction_method)

                # Calculate extraction efficiency
                if file_size > 0:
                    chars_per_byte = text_length / file_size
                    words_per_kb = (
                        (word_count * 1024) / file_size if file_size > 0 else 0
                    )
                    metrics.add_metric("chars_per_byte", round(chars_per_byte, 3))
                    metrics.add_metric("words_per_kb", round(words_per_kb, 1))

                metrics.set_success(True)
                metrics.report("text_extraction_completed")

                return {
                    "text": extracted_text,
                    "metadata": {
                        "extraction_method": extraction_method,
                        "word_count": word_count,
                        "language": "en",
                        "file_size": file_size,
                    },
                }

            except Exception as e:
                metrics.set_error(e)
                metrics.report("text_extraction_failed")

                raise ValueError(f"Text extraction failed for {file_id}: {e}") from None
