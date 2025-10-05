"""
File import tool.
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
)
from lifearchivist.utils.logging import log_event, track


class FileImportTool(BaseTool):
    """Tool for importing files into the vault."""

    def __init__(
        self,
        vault=None,
        llamaindex_service=None,
        progress_manager=None,
        enrichment_queue=None,
        theme_classifier=None,
    ):
        super().__init__()
        self.vault = vault
        self.llamaindex_service = llamaindex_service
        self.progress_manager = progress_manager
        self.enrichment_queue = enrichment_queue
        # Use provided classifier or create a new one
        if theme_classifier is None:
            from lifearchivist.tools.theme_classifier.theme_classifier import (
                ThemeClassifier,
            )

            self.theme_classifier = ThemeClassifier()
        else:
            self.theme_classifier = theme_classifier

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
        operation="file_import_pipeline",
        include_args=["path", "session_id"],
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
        file_size_mb = round(file_size_bytes / (1024 * 1024), 2)

        # Calculate hash and detect MIME type
        file_hash = await self._analyze_file(file_path, display_path)

        if mime_hint:
            mime_type = mime_hint
        else:
            mime_type = magic.from_file(str(file_path), mime=True)

        # Use provided file_id or generate unique ID
        file_id = metadata.get("file_id") or str(uuid.uuid4())

        # Log import start with all context (single comprehensive event)
        log_event(
            "file_import_started",
            {
                "file_id": file_id,
                "file_path": display_path,
                "file_hash": file_hash[:8],
                "mime_type": mime_type,
                "mime_source": "hint" if mime_hint else "detected",
                "size_bytes": file_size_bytes,
                "size_mb": file_size_mb,
                "tags_count": len(tags),
                "has_session": bool(session_id),
            },
        )

        # Initialize progress tracking
        if self.progress_manager and session_id:
            await self.progress_manager.start_progress(file_id, session_id)

        try:
            # Store file in vault first - this handles physical file deduplication
            vault_result = await self.vault.store_file(file_path, file_hash)

            # Check for duplicate using vault result AND LlamaIndex metadata check
            if vault_result["existed"]:
                duplicate_doc = await self._check_for_duplicate(file_id, file_hash)
                if duplicate_doc:
                    # Send completion message for duplicates BEFORE cleanup
                    if self.progress_manager and session_id:
                        # Send a completion message indicating this is a duplicate
                        await self.progress_manager.complete_progress(
                            file_id,
                            metadata={
                                "original_filename": original_filename,
                                "file_size": stat.st_size,
                                "mime_type": mime_type,
                                "status": "duplicate",
                                "message": "File already exists in archive",
                                "existing_doc_id": duplicate_doc.get("document_id"),
                            },
                        )
                        # Now clean up the progress tracking
                        # Note: We may want to keep this for a bit to ensure the message is delivered
                        # await self.progress_manager.cleanup_progress(file_id)

                    # Log duplicate found (important business event)
                    log_event(
                        "duplicate_file_detected",
                        {
                            "file_id": file_id,
                            "existing_doc_id": duplicate_doc.get("document_id"),
                            "file_hash": file_hash[:8],
                            "file_path": display_path,
                        },
                    )

                    return create_duplicate_response(
                        duplicate_doc, file_hash, stat, mime_type, display_path
                    )

            # Extract text content early to have it available for document creation
            extracted_text = await self._try_extract_text(
                file_id, file_path, mime_type, file_hash
            )

            theme_result = {}
            if extracted_text:
                theme_result = await self._classify_themes(
                    file_id, extracted_text, display_path
                )
                if theme_result:
                    # Classify subthemes if we have a primary theme
                    theme = theme_result.get("theme")
                    if theme and theme != "Unclassified":
                        subtheme_result = await self._classify_subthemes(
                            file_id, extracted_text, theme, original_filename
                        )
                        if subtheme_result:
                            theme_result.update(subtheme_result)

            # Create and store document in LlamaIndex
            doc_metadata = create_document_metadata(
                file_id=file_id,
                file_hash=file_hash,
                original_path=display_path,
                mime_type=mime_type,
                stat=stat,
                text=extracted_text,
                custom_metadata=metadata,
            )

            # Add themes to metadata if classified
            if theme_result:
                doc_metadata.update({"classifications": theme_result})

            # Add tags to document metadata if provided
            if tags:
                doc_metadata["tags"] = tags

            await self._create_document(file_id, extracted_text, doc_metadata)

            # Queue enrichment tasks instead of processing synchronously
            if extracted_text and self.enrichment_queue:
                await self._queue_enrichment_tasks(file_id, extracted_text)

            # Finalize document
            await self._finalize_document(file_id, file_path, vault_result)

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

            # Log successful import with comprehensive metrics (important business event)
            word_count = len(extracted_text.split()) if extracted_text else 0
            log_event(
                "file_import_completed",
                {
                    "file_id": file_id,
                    "file_hash": file_hash[:8],
                    "file_path": display_path,
                    "mime_type": mime_type,
                    "size_bytes": file_size_bytes,
                    "word_count": word_count,
                    "text_extracted": bool(extracted_text),
                    "tags_count": len(tags),
                    "vault_existed": vault_result["existed"],
                },
            )

            return create_success_response(
                file_id, file_hash, stat, mime_type, display_path, vault_result
            )

        except Exception as e:
            await self._handle_import_error(e, file_id, display_path, session_id or "")
            return create_error_response(e, display_path)

    @track(
        operation="file_analysis",
        include_args=["display_path"],
        track_performance=True,
    )
    async def _analyze_file(self, file_path: Path, display_path: str) -> str:
        """Analyze file and calculate hash."""
        file_hash = await calculate_file_hash(file_path)
        return file_hash

    @track(
        operation="duplicate_detection",
        include_args=["file_id"],
        track_performance=True,
    )
    async def _check_for_duplicate(
        self, file_id: str, file_hash: str
    ) -> Dict[str, Any] | None:
        """Check for duplicate documents in LlamaIndex."""
        # Check LlamaIndex for existing document with this file hash
        existing_docs_result = (
            await self.llamaindex_service.query_documents_by_metadata(
                filters={"file_hash": file_hash}, limit=1
            )
        )

        # Unwrap the Result
        if existing_docs_result.is_success():
            existing_docs = existing_docs_result.unwrap()
            if existing_docs:
                return existing_docs[0]  # type: ignore[no-any-return]

        return None

    @track(
        operation="document_creation",
        include_args=["file_id"],
        track_performance=True,
    )
    async def _create_document(
        self, file_id: str, extracted_text: str, doc_metadata: Dict[str, Any]
    ):
        """Create document in LlamaIndex."""
        result = await self.llamaindex_service.add_document(
            document_id=file_id, content=extracted_text, metadata=doc_metadata
        )

        if result.is_failure():
            log_event(
                "document_indexing_failed",
                {
                    "file_id": file_id,
                    "error": result.error,
                    "error_type": result.error_type,
                },
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to create document {file_id}: {result.error}")

    @track(
        operation="document_finalization",
        include_args=["file_id"],
        track_performance=True,
    )
    async def _finalize_document(
        self, file_id: str, file_path: Path, vault_result: Dict[str, Any]
    ):
        """Finalize document with status update and provenance."""
        # Update status to ready in LlamaIndex metadata
        status_result = await self.llamaindex_service.update_document_metadata(
            file_id, {"status": "ready"}, merge_mode="update"
        )

        if status_result.is_failure():
            log_event(
                "document_finalization_warning",
                {
                    "file_id": file_id,
                    "step": "status_update",
                    "error": status_result.error,
                },
                level=logging.WARNING,
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
        provenance_result = await self.llamaindex_service.update_document_metadata(
            file_id, {"provenance": [provenance_entry]}, merge_mode="update"
        )

        if provenance_result.is_failure():
            log_event(
                "document_finalization_warning",
                {
                    "file_id": file_id,
                    "step": "provenance_update",
                    "error": provenance_result.error,
                },
                level=logging.WARNING,
            )

    async def _handle_import_error(
        self, error: Exception, file_id: str, display_path: str, session_id: str
    ):
        """Handle import errors with proper cleanup and logging."""
        # Log the main error (important for debugging)
        log_event(
            "file_import_failed",
            {
                "file_id": file_id if file_id else "unknown",
                "error_type": type(error).__name__,
                "error_message": str(error),
                "file_path": display_path,
            },
            level=logging.ERROR,
        )

        # Report error to progress tracking if we have a file_id
        if self.progress_manager and session_id and file_id:
            try:
                await self.progress_manager.error_progress(
                    file_id, str(error), ProcessingStage.UPLOAD
                )
            except Exception as progress_error:
                # Log secondary failures at DEBUG level to reduce noise
                log_event(
                    "cleanup_error",
                    {
                        "file_id": file_id,
                        "cleanup_type": "progress_tracking",
                        "error": str(progress_error),
                    },
                    level=logging.DEBUG,
                )

        # Update document metadata to failed status if document exists
        if self.llamaindex_service and file_id:
            try:
                await self.llamaindex_service.update_document_metadata(
                    file_id,
                    {"status": "failed", "error_message": str(error)},
                    merge_mode="update",
                )
            except Exception as metadata_error:
                # Log secondary failures at DEBUG level to reduce noise
                log_event(
                    "cleanup_error",
                    {
                        "file_id": file_id,
                        "cleanup_type": "metadata_update",
                        "error": str(metadata_error),
                    },
                    level=logging.DEBUG,
                )

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
            from lifearchivist.tools.extract.extract_tool import ExtractTextTool

            extract_tool = ExtractTextTool(vault=self.vault)
            result = await extract_tool.execute(
                file_id=file_id,
                file_path=file_path,
                mime_type=mime_type,
                file_hash=file_hash,
            )

            extracted_text = result.get("text", "")

            # Only log if extraction had notable results or issues
            word_count = len(extracted_text.split()) if extracted_text else 0
            if word_count == 0:
                log_event(
                    "text_extraction_empty",
                    {
                        "file_id": file_id,
                        "mime_type": mime_type,
                        "extraction_method": self._get_extraction_method(mime_type),
                    },
                    level=logging.WARNING,
                )

            return str(extracted_text)
        else:
            # Log at DEBUG level since this is expected for many file types
            log_event(
                "text_extraction_skipped",
                {
                    "file_id": file_id,
                    "mime_type": mime_type,
                    "reason": "unsupported_format",
                },
                level=logging.DEBUG,
            )
            return ""

    def _get_extraction_method(self, mime_type: str) -> str:
        """Get extraction method name for logging."""
        if mime_type.startswith("text/"):
            return "text_file"
        elif mime_type == "application/pdf":
            return "pypdf"
        elif (
            mime_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            return "python_docx"
        else:
            return "unknown"

    @track(
        operation="theme_classification",
        include_args=["file_id"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _classify_themes(
        self, file_id: str, text: str, display_path: str = ""
    ) -> Dict[str, Any] | None:
        """Classify document themes using the shared ProductionThemeClassifier."""
        try:
            theme, confidence, pattern_or_phrase, classification = (
                self.theme_classifier.classify(
                    text=text,
                    filename=display_path,
                )
            )

            theme_details = {
                "theme": theme,
                "match_tier": classification,
                "match_pattern": pattern_or_phrase,
                "confidence": confidence,
            }

            match classification:
                case "primary":
                    theme_details["confidence_level"] = "Very High"
                case "secondary":
                    theme_details["confidence_level"] = "High"
                case "tertiary" if confidence >= 0.5:
                    theme_details["confidence_level"] = "Medium"
                case "tertiary" if confidence < 0.5:
                    theme_details["confidence_level"] = "Low"
                case _:
                    theme_details["confidence_level"] = "None"

            log_event(
                "document_themes_classified",
                {**theme_details},
            )
            return theme_details

        except Exception as e:
            log_event(
                "theme_classification_error",
                {
                    "file_id": file_id,
                    "error": str(e),
                },
                level=logging.WARNING,
            )
            return None

    @track(
        operation="subtheme_classification",
        include_args=["file_id", "primary_theme"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _classify_subthemes(
        self, file_id: str, text: str, primary_theme: str, filename: str = None
    ) -> Dict[str, Any] | None:
        """Classify document subthemes based on primary theme."""
        try:
            from lifearchivist.tools.subtheme_classifier.models import SubthemeResult
            from lifearchivist.tools.subtheme_classifier.subtheme_classifier import (
                SubthemeClassifier,
            )

            # Create subtheme classifier instance
            classifier = SubthemeClassifier()

            # Check if this theme supports subtheme classification
            if primary_theme not in classifier.get_supported_themes():
                log_event(
                    "subtheme_classification_skipped",
                    {
                        "file_id": file_id,
                        "primary_theme": primary_theme,
                        "reason": "theme_not_supported",
                    },
                    level=logging.DEBUG,
                )
                return None

            # Prepare metadata for classification
            metadata = {"filename": filename} if filename else {}

            # Classify subthemes
            result: SubthemeResult = classifier.classify(
                text=text, primary_theme=primary_theme, metadata=metadata
            )

            if result.subthemes:
                subtheme_metadata = {
                    "subthemes": result.subthemes,
                    "primary_subtheme": result.primary_subtheme,
                    "subclassifications": result.subclassifications,
                    "primary_subclassification": result.primary_subclassification,
                    "subclassification_confidence": result.subclassification_confidence,
                    "confidence_scores": result.confidence_scores,
                    "category_mapping": result.category_mapping,
                    "matched_patterns": result.matched_patterns,
                    "subclassification_method": result.subclassification_method,
                }

                log_event(
                    "document_subthemes_classified",
                    {
                        "file_id": file_id,
                        "primary_theme": primary_theme,
                        "primary_subtheme": result.primary_subtheme,
                        "subthemes_count": len(result.subthemes),
                        "classification_method": result.subclassification_method,
                        "primary_pattern": (
                            result.matched_patterns.get(result.primary_subtheme, "")
                            if result.primary_subtheme
                            else ""
                        ),
                    },
                )

                return subtheme_metadata
            else:
                log_event(
                    "document_subthemes_not_detected",
                    {
                        "file_id": file_id,
                        "primary_theme": primary_theme,
                    },
                    level=logging.DEBUG,
                )
                return None

        except Exception as e:
            # Log error but don't fail the import
            log_event(
                "subtheme_classification_error",
                {
                    "file_id": file_id,
                    "primary_theme": primary_theme,
                    "error": str(e),
                },
                level=logging.WARNING,
            )
            return None

    @track(
        operation="queue_enrichment_tasks",
        include_args=["file_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _queue_enrichment_tasks(self, file_id: str, text: str):
        """Queue background enrichment tasks for the document."""
        tasks_queued = []

        # TODO: ENABLE OR REMOVE DATE EXTRACTION
        enable_date_extraction = False

        if enable_date_extraction and should_extract_dates(text):
            success = await self.enrichment_queue.enqueue_task(
                task_type="date_extraction",
                document_id=file_id,
                data={"text": text},
                priority=0,
            )

            if success:
                tasks_queued.append("date_extraction")

                await self.llamaindex_service.update_document_metadata(
                    file_id, {"enrichment_status": "queued"}, merge_mode="update"
                )

        if tasks_queued:
            log_event(
                "enrichment_tasks_queued",
                {
                    "file_id": file_id,
                    "tasks": tasks_queued,
                    "text_length": len(text),
                },
            )
        else:
            log_event(
                "enrichment_tasks_skipped",
                {
                    "file_id": file_id,
                    "reason": "no_suitable_content",
                },
                level=logging.DEBUG,
            )
