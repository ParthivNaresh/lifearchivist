"""
Content extraction tools.
"""

import mimetypes
from pathlib import Path
from typing import Any, Dict

from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.tools.extract.extract_utils import (
    _extract_text_by_type,
    _get_extraction_method,
)
from lifearchivist.utils.logging import track


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
        operation="text_extraction"
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Extract text from a document."""
        file_id = kwargs.get("file_id")
        file_path = kwargs.get("file_path")
        mime_type = kwargs.get("mime_type")
        file_hash = kwargs.get("file_hash")

        if not file_id:
            raise ValueError("File ID is required")

        try:
            if file_path:
                # Direct file path provided
                actual_file_path = Path(file_path)

                if not mime_type:
                    mime_type = mimetypes.guess_type(str(actual_file_path))[0]
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

            # Verify file exists
            if not actual_file_path or not actual_file_path.exists():
                raise ValueError(f"File not found: {actual_file_path}")

            # Get file size before extraction
            file_size = actual_file_path.stat().st_size
            # Extract text using the appropriate method
            extracted_text = await _extract_text_by_type(
                actual_file_path, str(mime_type)
            )
            # Calculate extraction metrics
            word_count = len(extracted_text.split()) if extracted_text else 0
            text_length = len(extracted_text) if extracted_text else 0
            extraction_method = _get_extraction_method(str(mime_type))
            # Calculate extraction efficiency
            if file_size > 0:
                chars_per_byte = text_length / file_size
                words_per_kb = (
                    (word_count * 1024) / file_size if file_size > 0 else 0
                )

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
            raise ValueError(f"Text extraction failed for {file_id}: {e}") from None
