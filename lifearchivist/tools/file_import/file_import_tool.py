"""
File management tools.
"""

import uuid
from pathlib import Path
from typing import Any, Dict

import magic

from lifearchivist.server.progress_manager import ProcessingStage
from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.tools.file_import.file_import_utils import (
    calculate_file_hash,
    create_document_metadata,
    create_duplicate_response,
    create_error_response,
    create_provenance_entry,
    create_success_response,
    is_text_extraction_supported,
    should_extract_dates,
    should_extract_embeddings,
)
from lifearchivist.utils.logging import log_event, track


class FileImportTool(BaseTool):
    """Tool for importing files into the vault."""

    def __init__(self, vault=None, llamaindex_service=None, progress_manager=None):
        super().__init__()
        self.vault = vault
        self.llamaindex_service = llamaindex_service
        self.progress_manager = progress_manager

    def _get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="file.import",
            description="Import file to vault",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path",
                    },
                    "mime_hint": {
                        "type": ["string", "null"],
                        "description": "Override auto-detection",
                    },
                    "tags": {"type": ["array", "null"], "items": {"type": "string"}},
                    "metadata": {"type": ["object", "null"]},
                    "session_id": {
                        "type": ["string", "null"],
                        "description": "WebSocket session ID for progress tracking",
                    },
                },
                "required": ["path"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "hash": {"type": "string"},
                    "size": {"type": "integer"},
                    "mime_type": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            async_tool=True,
            idempotent=True,
        )

    @track(
        operation="file_import",
        include_args=["path", "mime_hint", "session_id"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Import a file into the system."""
        path = kwargs.get("path")
        mime_hint = kwargs.get("mime_hint")
        tags = kwargs.get("tags", []) or []
        metadata = kwargs.get("metadata", {}) or {}
        session_id = kwargs.get("session_id")

        # Get original filename from metadata if provided (for uploads)
        original_filename = metadata.get("original_filename")
        display_path = original_filename if original_filename else str(path)

        if not path:
            raise ValueError("File path is required")

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not self.vault or not self.llamaindex_service:
            raise RuntimeError("Vault and LlamaIndex service dependencies not provided")

        # Get file stats
        stat = file_path.stat()
        file_size_bytes = stat.st_size

        # Log file analysis start
        log_event(
            "file_analysis_started",
            {
                "file_path": display_path,
                "file_size_bytes": file_size_bytes,
                "file_size_mb": round(file_size_bytes / (1024 * 1024), 2),
                "has_mime_hint": bool(mime_hint),
            },
        )

        # Calculate hash and detect MIME type
        file_hash = await calculate_file_hash(file_path)

        if mime_hint:
            mime_type = mime_hint
            log_event(
                "mime_type_override",
                {"file_hash": file_hash[:8], "mime_type": mime_type, "source": "hint"},
            )
        else:
            mime_type = magic.from_file(str(file_path), mime=True)
            log_event(
                "mime_type_detected",
                {"file_hash": file_hash[:8], "mime_type": mime_type, "source": "magic"},
            )

        # Use provided file_id or generate unique ID
        file_id = metadata.get("file_id") or str(uuid.uuid4())

        log_event(
            "file_processed",
            {
                "file_id": file_id,
                "file_hash": file_hash[:8],
                "mime_type": mime_type,
                "size_bytes": file_size_bytes,
                "original_filename": original_filename,
            },
        )

        # Initialize progress tracking
        if self.progress_manager and session_id:
            await self.progress_manager.start_progress(file_id, session_id)
            log_event(
                "progress_tracking_started",
                {"file_id": file_id, "session_id": session_id},
            )

        try:
            # Store file in vault first - this handles physical file deduplication
            vault_result = await self.vault.store_file(file_path, file_hash)

            log_event(
                "vault_storage_completed",
                {
                    "file_id": file_id,
                    "file_hash": file_hash[:8],
                    "vault_existed": vault_result["existed"],
                    "vault_path": vault_result.get("path", "unknown"),
                },
            )

            # Extract text content early to have it available for document creation
            extracted_text = await self._try_extract_text(
                file_id, file_path, mime_type, file_hash
            )

            word_count = len(extracted_text.split()) if extracted_text else 0

            log_event(
                "text_extraction_completed",
                {
                    "file_id": file_id,
                    "text_length": len(extracted_text),
                    "word_count": word_count,
                    "has_text": bool(extracted_text),
                },
            )

            # Check for duplicate using vault result AND LlamaIndex metadata check
            if vault_result["existed"]:
                log_event(
                    "duplicate_check_started",
                    {
                        "file_id": file_id,
                        "file_hash": file_hash[:8],
                        "vault_existed": True,
                    },
                )

                # Check LlamaIndex for existing document with this file hash
                existing_docs = (
                    await self.llamaindex_service.query_documents_by_metadata(
                        filters={"file_hash": file_hash}, limit=1
                    )
                )

                if existing_docs:
                    existing_doc = existing_docs[0]

                    log_event(
                        "duplicate_found",
                        {
                            "file_id": file_id,
                            "existing_doc_id": existing_doc.get("document_id"),
                            "file_hash": file_hash[:8],
                        },
                    )

                    # For duplicates, clean up progress tracking without sending completion
                    if self.progress_manager and session_id:
                        await self.progress_manager.cleanup_progress(file_id)

                    return create_duplicate_response(
                        existing_doc, file_hash, stat, mime_type, display_path
                    )

            # Create document in LlamaIndex with full content immediately to prevent race conditions
            doc_metadata = create_document_metadata(
                file_id=file_id,
                file_hash=file_hash,
                original_path=display_path,
                mime_type=mime_type,
                stat=stat,
                text=extracted_text,
                custom_metadata=metadata,
            )

            log_event(
                "document_creation_started",
                {
                    "file_id": file_id,
                    "metadata_fields": len(doc_metadata),
                    "content_length": len(extracted_text),
                },
            )

            success = await self.llamaindex_service.add_document(
                document_id=file_id, content=extracted_text, metadata=doc_metadata
            )

            if not success:
                log_event(
                    "document_creation_failed",
                    {
                        "file_id": file_id,
                        "error": "LlamaIndex add_document returned False",
                    },
                )
                return {
                    "success": False,
                    "error": f"Failed to create document {file_id} in LlamaIndex",
                    "original_path": display_path,
                }

            log_event(
                "document_created",
                {
                    "file_id": file_id,
                    "document_id": file_id,
                    "content_length": len(extracted_text),
                    "word_count": word_count,
                },
            )

            # Process additional metadata asynchronously (dates, tags) without blocking the main flow
            if extracted_text:
                await self._try_extract_content_dates(file_id, extracted_text)

            # Update status to ready in LlamaIndex metadata
            await self.llamaindex_service.update_document_metadata(
                file_id, {"status": "ready"}, merge_mode="update"
            )

            log_event(
                "document_status_updated", {"file_id": file_id, "status": "ready"}
            )

            # Complete progress tracking
            if self.progress_manager and session_id:
                await self.progress_manager.complete_progress(
                    file_id,
                    metadata={
                        "original_filename": original_filename,
                        "file_size": stat.st_size,
                        "mime_type": mime_type,
                    },
                )
                log_event(
                    "progress_tracking_completed",
                    {"file_id": file_id, "session_id": session_id},
                )

            # Log provenance in LlamaIndex metadata
            provenance_entry = create_provenance_entry(
                action="import",
                agent="file_import_tool",
                tool="file.import",
                params={"original_path": str(file_path)},
                result={
                    "vault_path": vault_result["path"],
                    "existed": vault_result["existed"],
                },
            )
            await self.llamaindex_service.update_document_metadata(
                file_id, {"provenance": [provenance_entry]}, merge_mode="update"
            )

            log_event(
                "file_import_success",
                {
                    "file_id": file_id,
                    "file_hash": file_hash[:8],
                    "mime_type": mime_type,
                    "size_bytes": file_size_bytes,
                    "word_count": word_count,
                    "vault_existed": vault_result["existed"],
                },
            )

            return create_success_response(
                file_id, file_hash, stat, mime_type, display_path, vault_result
            )

        except Exception as e:
            log_event(
                "file_import_error",
                {
                    "file_id": file_id if "file_id" in locals() else "unknown",
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "file_path": display_path,
                },
            )

            # Report error to progress tracking if we have a file_id
            if self.progress_manager and session_id and "file_id" in locals():
                try:
                    await self.progress_manager.error_progress(
                        file_id, str(e), ProcessingStage.UPLOAD
                    )
                except Exception as progress_error:
                    log_event(
                        "progress_error_failed",
                        {
                            "file_id": file_id,
                            "original_error": str(e),
                            "progress_error": str(progress_error),
                        },
                    )
                    raise progress_error

            # Update document metadata to failed status if document exists
            if self.llamaindex_service and "file_id" in locals():
                try:
                    await self.llamaindex_service.update_document_metadata(
                        file_id,
                        {"status": "failed", "error_message": str(e)},
                        merge_mode="update",
                    )
                except Exception as metadata_error:
                    log_event(
                        "metadata_update_failed",
                        {
                            "file_id": file_id,
                            "original_error": str(e),
                            "metadata_error": str(metadata_error),
                        },
                    )
                    raise metadata_error

            return create_error_response(e, display_path)

    @track(
        operation="text_extraction",
        include_args=["file_id", "mime_type"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _try_extract_text(
        self, file_id: str, file_path: Path, mime_type: str, file_hash: str
    ) -> str:
        """Try to extract text from the imported file."""
        if is_text_extraction_supported(mime_type):
            log_event(
                "text_extraction_supported",
                {
                    "file_id": file_id,
                    "mime_type": mime_type,
                    "file_hash": file_hash[:8],
                },
            )

            from lifearchivist.tools.extract.extract_tools import ExtractTextTool

            extract_tool = ExtractTextTool(vault=self.vault)
            result = await extract_tool.execute(
                file_id=file_id,
                file_path=file_path,
                mime_type=mime_type,
                file_hash=file_hash,
            )

            extracted_text = result.get("text", "")

            log_event(
                "text_extracted",
                {
                    "file_id": file_id,
                    "text_length": len(extracted_text),
                    "word_count": len(extracted_text.split()) if extracted_text else 0,
                    "extraction_success": bool(extracted_text),
                },
            )

            return str(extracted_text)
        else:
            log_event(
                "text_extraction_skipped",
                {
                    "file_id": file_id,
                    "mime_type": mime_type,
                    "reason": "unsupported_mime_type",
                },
            )
            return ""

    @track(operation="embedding_generation")
    async def _try_generate_embeddings(self, file_id: str, text: str):
        """Try to generate embeddings and chunks for the document."""
        if not should_extract_embeddings(text):
            return

    @track(
        operation="date_extraction",
        include_args=["file_id"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _try_extract_content_dates(self, file_id: str, text: str):
        """Try to extract content dates from document text."""
        if not should_extract_dates(text):
            log_event(
                "date_extraction_skipped",
                {
                    "file_id": file_id,
                    "text_length": len(text),
                    "reason": "should_extract_dates_returned_false",
                },
            )
            return

        log_event(
            "date_extraction_started",
            {
                "file_id": file_id,
                "text_length": len(text),
                "word_count": len(text.split()),
            },
        )

        from lifearchivist.schemas.tool_schemas import ContentDateExtractionInput
        from lifearchivist.tools.date_extract.date_extraction_tool import (
            ContentDateExtractionTool,
        )

        date_tool = ContentDateExtractionTool(
            llamaindex_service=self.llamaindex_service
        )
        input_data = ContentDateExtractionInput(document_id=file_id, text_content=text)

        result = await date_tool.execute(input_data=input_data)
        extracted_date = result.get("extracted_date", "")
        dates_found = result.get("total_dates_found", 0)

        log_event(
            "date_extraction_completed",
            {
                "file_id": file_id,
                "extracted_date": extracted_date,
                "dates_found": dates_found,
                "extraction_success": dates_found > 0,
            },
        )

        return result
