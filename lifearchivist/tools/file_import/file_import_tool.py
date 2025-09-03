"""
File management tools.
"""

import logging
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
from lifearchivist.utils.logging import log_context, log_event, log_method
from lifearchivist.utils.logging.structured import MetricsCollector

logger = logging.getLogger(__name__)


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
                        "type": "string",
                        "description": "Override auto-detection",
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "metadata": {"type": "object"},
                    "session_id": {
                        "type": "string",
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

    @log_method(operation_name="file_import", include_args=True, include_result=True)
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

        # Use structured logging context for the entire import operation
        with log_context(
            operation="file_import", file_path=display_path, original_path=str(path)
        ) as correlation_id:

            # Initialize metrics collector
            metrics = MetricsCollector("file_import")
            metrics.start()

            # Get file stats
            stat = file_path.stat()
            file_size_bytes = stat.st_size

            metrics.add_metric("file_size_bytes", file_size_bytes)

            # Calculate hash and detect MIME type
            file_hash = await calculate_file_hash(file_path)

            if mime_hint:
                mime_type = mime_hint
            else:
                mime_type = magic.from_file(str(file_path), mime=True)

            metrics.add_metric("mime_type", mime_type)

            # Use provided file_id or generate unique ID
            file_id = metadata.get("file_id") or str(uuid.uuid4())

            # Log the import start with rich context
            log_event(
                "file_import_started",
                {
                    "file_id": file_id,
                    "file_hash": file_hash,
                    "file_size_bytes": file_size_bytes,
                    "mime_type": mime_type,
                    "has_session": session_id is not None,
                },
            )

            # Initialize progress tracking
            if self.progress_manager and session_id:
                await self.progress_manager.start_progress(file_id, session_id)

            try:
                # Store file in vault first - this handles physical file deduplication
                vault_result = await self.vault.store_file(file_path, file_hash)

                metrics.add_metric("vault_existed", vault_result["existed"])

                # Extract text content early to have it available for document creation
                extracted_text = await self._try_extract_text(
                    file_id, file_path, mime_type, file_hash
                )

                word_count = len(extracted_text.split()) if extracted_text else 0
                metrics.add_metric("word_count", word_count)
                metrics.add_metric(
                    "text_length", len(extracted_text) if extracted_text else 0
                )

                # Check for duplicate using vault result AND LlamaIndex metadata check
                if vault_result["existed"]:
                    log_event(
                        "duplicate_detected_vault",
                        {"file_hash": file_hash, "checking_llamaindex": True},
                    )

                    # Check LlamaIndex for existing document with this file hash
                    existing_docs = (
                        await self.llamaindex_service.query_documents_by_metadata(
                            filters={"file_hash": file_hash}, limit=1
                        )
                    )

                    if existing_docs:
                        log_event(
                            "duplicate_confirmed_llamaindex",
                            {
                                "file_hash": file_hash,
                                "existing_document_id": existing_docs[0]["document_id"],
                            },
                        )

                        # For duplicates, clean up progress tracking without sending completion
                        if self.progress_manager and session_id:
                            await self.progress_manager.cleanup_progress(file_id)

                        existing_doc = existing_docs[0]
                        existing_metadata = existing_doc["metadata"]

                        metrics.set_success(True)
                        metrics.add_metric("duplicate_resolved", True)
                        metrics.report("file_import_completed")

                        return create_duplicate_response(
                            existing_doc, file_hash, stat, mime_type, display_path
                        )
                    else:
                        log_event(
                            "vault_duplicate_not_in_llamaindex",
                            {"file_hash": file_hash, "proceeding_with_indexing": True},
                        )
                else:
                    log_event(
                        "new_file_processing",
                        {"file_hash": file_hash, "is_new_file": True},
                    )

                # Create document in LlamaIndex with full content immediately to prevent race conditions
                log_event(
                    "llamaindex_document_creation_started",
                    {"file_id": file_id, "text_available": bool(extracted_text)},
                )

                doc_metadata = create_document_metadata(
                    file_id=file_id,
                    file_hash=file_hash,
                    original_path=display_path,
                    mime_type=mime_type,
                    stat=stat,
                    text=extracted_text,
                    custom_metadata=metadata,
                )

                success = await self.llamaindex_service.add_document(
                    document_id=file_id, content=extracted_text, metadata=doc_metadata
                )

                if not success:
                    metrics.set_error(
                        RuntimeError("Failed to create document in LlamaIndex")
                    )
                    metrics.report("file_import_failed")
                    return {
                        "success": False,
                        "error": f"Failed to create document {file_id} in LlamaIndex",
                        "original_path": display_path,
                    }

                log_event(
                    "llamaindex_document_created", {"file_id": file_id, "success": True}
                )

                metrics.increment("documents_created")

                # Process additional metadata asynchronously (dates, tags) without blocking the main flow
                if extracted_text:
                    await self._try_extract_content_dates(file_id, extracted_text)
                    metrics.increment("date_extractions_attempted")

                # Update status to ready in LlamaIndex metadata
                await self.llamaindex_service.update_document_metadata(
                    file_id, {"status": "ready"}, merge_mode="update"
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

                # Report successful completion with full metrics
                metrics.set_success(True)
                metrics.add_metric("document_ready", True)
                metrics.report("file_import_completed")

                log_event(
                    "file_import_successful",
                    {
                        "file_id": file_id,
                        "vault_path": vault_result["path"],
                        "word_count": word_count,
                        "execution_time_ms": metrics.metrics.get("duration_ms", 0),
                    },
                )

                return create_success_response(
                    file_id, file_hash, stat, mime_type, display_path, vault_result
                )

            except Exception as e:
                # Report error metrics and structured logging
                metrics.set_error(e)
                metrics.report("file_import_failed")

                log_event(
                    "file_import_error",
                    {
                        "file_path": display_path,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "has_file_id": "file_id" in locals(),
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
                            "progress_tracking_error",
                            {
                                "original_error": str(e),
                                "progress_error": str(progress_error),
                            },
                        )

                # Update document metadata to failed status if document exists
                if self.llamaindex_service and "file_id" in locals():
                    try:
                        await self.llamaindex_service.update_document_metadata(
                            file_id,
                            {"status": "failed", "error_message": str(e)},
                            merge_mode="update",
                        )
                        log_event(
                            "document_status_updated",
                            {"file_id": file_id, "status": "failed"},
                        )
                    except Exception as metadata_error:
                        log_event(
                            "metadata_cleanup_failed",
                            {"file_id": file_id, "cleanup_error": str(metadata_error)},
                        )

                return create_error_response(e, display_path)

    @log_method(
        operation_name="text_extraction", include_args=True, include_result=True
    )
    async def _try_extract_text(
        self, file_id: str, file_path: Path, mime_type: str, file_hash: str
    ) -> str:
        """Try to extract text from the imported file."""
        if is_text_extraction_supported(mime_type):
            from lifearchivist.tools.extract.extract_tools import ExtractTextTool

            extract_tool = ExtractTextTool(vault=self.vault)
            result = await extract_tool.execute(
                file_id=file_id,
                file_path=file_path,
                mime_type=mime_type,
                file_hash=file_hash,
            )

            extracted_text = result.get("text", "")
            word_count = result.get("metadata", {}).get("word_count", 0)
            extraction_method = result.get("metadata", {}).get(
                "extraction_method", "unknown"
            )

            log_event(
                "text_extraction_successful",
                {
                    "file_id": file_id,
                    "word_count": word_count,
                    "extraction_method": extraction_method,
                    "text_length": len(extracted_text),
                },
            )
            return extracted_text
        else:
            log_event(
                "text_extraction_unsupported",
                {"file_id": file_id, "mime_type": mime_type},
            )
            return ""

    @log_method(operation_name="embedding_generation")
    async def _try_generate_embeddings(self, file_id: str, text: str):
        """Try to generate embeddings and chunks for the document."""
        if not should_extract_embeddings(text):
            log_event(
                "embedding_generation_skipped",
                {
                    "file_id": file_id,
                    "reason": "text_too_short",
                    "text_length": len(text.strip()),
                },
            )
            return

        # Skip embedding generation - LlamaIndex handles this internally
        log_event(
            "embedding_generation_delegated",
            {"file_id": file_id, "handler": "llamaindex", "text_length": len(text)},
        )

    @log_method(operation_name="date_extraction")
    async def _try_extract_content_dates(self, file_id: str, text: str):
        """Try to extract content dates from document text."""
        if not should_extract_dates(text):
            log_event(
                "date_extraction_skipped",
                {
                    "file_id": file_id,
                    "reason": "text_too_short",
                    "text_length": len(text.strip()),
                },
            )
            return

        from lifearchivist.schemas.tool_schemas import ContentDateExtractionInput
        from lifearchivist.tools.date_extract.date_extraction_tool import (
            ContentDateExtractionTool,
        )

        date_tool = ContentDateExtractionTool(
            llamaindex_service=self.llamaindex_service
        )
        input_data = ContentDateExtractionInput(document_id=file_id, text_content=text)

        result = await date_tool.execute(input_data)
        dates_count = result.total_dates_found

        log_event(
            "date_extraction_completed",
            {
                "file_id": file_id,
                "dates_found": dates_count,
                "extraction_successful": dates_count > 0,
            },
        )
