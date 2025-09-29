"""
Structured logging utilities for professional event-based logging.

Provides structured event logging and utilities for creating searchable,
queryable log entries with human-readable development formatting.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Get logger for this module
logger = logging.getLogger(__name__)


# StructuredFormatter removed - only using DevelopmentFormatter for human-readable logs


class StructuredLogger:
    """
    Professional structured logger that creates consistent, searchable log events.

    Provides methods for logging structured events with consistent field names
    and automatic context injection.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def event(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        level: int = logging.INFO,
    ):
        """
        Log a structured event with optional data.

        Args:
            event_name: Name of the event (e.g., 'document_processed')
            data: Dictionary of structured data to include
            level: Log level (defaults to INFO)
        """
        from .context import get_correlation_id, get_operation_context

        # Build structured log entry
        structured_data = {
            "event": event_name,
            "correlation_id": get_correlation_id(),
        }

        # Add operation context
        operation_context = get_operation_context()
        if operation_context:
            structured_data.update(operation_context)

        # Add custom data
        if data:
            structured_data.update(data)

        # Create log record with structured data
        record = self.logger.makeRecord(
            self.logger.name, level, "(structured)", 0, event_name, (), None
        )
        record.structured_data = structured_data

        self.logger.handle(record)

    def success(self, event_name: str, data: Optional[Dict[str, Any]] = None):
        """Log a successful operation."""
        success_data = {"success": True}
        if data:
            success_data.update(data)
        self.event(event_name, success_data, logging.INFO)

    def failure(
        self, event_name: str, error: Exception, data: Optional[Dict[str, Any]] = None
    ):
        """Log a failed operation with error details."""
        failure_data = {
            "success": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
        if data:
            failure_data.update(data)
        self.event(event_name, failure_data, logging.ERROR)

    def performance(
        self, operation: str, duration_ms: int, data: Optional[Dict[str, Any]] = None
    ):
        """Log performance metrics."""
        perf_data = {
            "operation": operation,
            "duration_ms": duration_ms,
            "performance_event": True,
        }
        if data:
            perf_data.update(data)
        self.event("performance_metric", perf_data)


# Global structured logger instance
_global_logger: Optional[StructuredLogger] = None


def get_structured_logger(name: str = "lifearchivist") -> StructuredLogger:
    """Get or create a structured logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = StructuredLogger(name)
    return _global_logger


def log_event(
    event_name: str, data: Optional[Dict[str, Any]] = None, level: int = logging.INFO
):
    """
    Convenience function for logging structured events.

    Args:
        event_name: Name of the event
        data: Optional structured data
        level: Log level

    Example::

        log_event("document_processed", {
            "document_id": "123",
            "processing_time_ms": 1500,
            "word_count": 500
        })
    """
    structured_logger = get_structured_logger()
    structured_logger.event(event_name, data, level)


def create_development_formatter() -> logging.Formatter:
    """
    Create a human-readable formatter for development environments.

    Returns a formatter that outputs clean, readable logs for development
    while still including structured data with intelligent event-based formatting.
    """

    class DevelopmentFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[
                :-3
            ]

            data: Optional[dict] = getattr(record, "structured_data", None)

            # Handle non-structured logs (fallback)
            if not data:
                return f"{timestamp} | {record.levelname:5} | {record.getMessage()}"

            # Route to appropriate formatter based on event type
            event = data.get("event", "")
            operation = data.get("operation", "")

            if event == "operation_started":
                message_content = self._format_operation_start(operation)
            elif event == "operation_completed":
                message_content = self._format_operation_success(data, operation)
            elif event == "operation_failed":
                message_content = self._format_operation_error(data, operation)
            elif event in ["file_processed", "document_indexed", "user_action"]:
                message_content = self._format_business_event(data, event)
            elif event in ["system_startup", "service_ready", "health_check"]:
                message_content = self._format_system_event(data, event)
            else:
                message_content = self._format_generic_event(data, event)

            return f"{timestamp} | {record.levelname:5} | {message_content}"

        def _format_operation_start(self, operation: str) -> str:
            """Format operation start events."""
            if not operation:
                return "🚀 operation started"
            return f"🚀 {operation} started"

        def _format_operation_success(self, data: dict, operation: str) -> str:
            """Format successful operation completion events."""
            duration_ms = data.get("duration_ms", 0)

            if duration_ms < 50:
                duration_emoji = "⚡"
            elif duration_ms > 2000:
                duration_emoji = "🐌"
            else:
                duration_emoji = "⏱️"

            if duration_ms >= 1000:
                duration_str = f"{duration_ms/1000:.1f}s"
            else:
                duration_str = f"{duration_ms}ms"

            # Add operation-specific context
            context = self._get_operation_context(data, operation)

            base_message = f"{duration_emoji} {duration_str} {operation}"
            return f"{base_message}{context}" if context else base_message

        def _format_operation_error(self, data: dict, operation: str) -> str:
            """Format failed operation events."""
            duration_ms = data.get("duration_ms", 0)
            error_type = data.get("error_type", "Error")
            error_message = data.get("error_message", "")

            # Format duration if available
            duration_part = ""
            if duration_ms > 0:
                if duration_ms >= 1000:
                    duration_part = f" {duration_ms/1000:.1f}s"
                else:
                    duration_part = f" {duration_ms}ms"

            # Truncate long error messages
            if len(error_message) > 60:
                error_message = error_message[:57] + "..."

            return (
                f"❌{duration_part} {operation} failed ({error_type}: {error_message})"
            )

        def _format_business_event(self, data: dict, event: str) -> str:
            """Format business/application events."""
            if event == "file_processed":
                file_id = data.get("file_id", "unknown")
                processing_time = data.get("processing_time", 0)
                return f"📄 file_processed (id={file_id}, {processing_time}s)"
            elif event == "document_indexed":
                doc_id = data.get("document_id", "unknown")
                chunks = data.get("chunks", 0)
                return f"📄 document_indexed (id={doc_id}, {chunks} chunks)"
            elif event == "user_action":
                action = data.get("action", "unknown")
                return f"👤 user_action ({action})"
            else:
                return f"📋 {event}"

        def _format_system_event(self, data: dict, event: str) -> str:
            """Format system-level events."""
            if event == "service_ready":
                service = data.get("service", "unknown")
                status = data.get("status", "unknown")
                return f"✅ {service} service ready ({status})"
            elif event == "system_startup":
                return "🚀 system startup"
            elif event == "health_check":
                status = data.get("status", "unknown")
                return f"💚 health_check ({status})"
            else:
                return f"⚙️ {event}"

        def _format_generic_event(self, data: dict, event: str) -> str:
            """Format generic/unknown events with contextual information."""
            if not event:
                return "📝 log_event"

            # Add specific context for common business events
            context = self._get_business_event_context(data, event)

            if context:
                return f"📝 {event}: {context}"
            else:
                return f"📝 {event}"

        def _get_business_event_context(self, data: dict, event: str) -> str:
            """Get contextual information for business events."""
            # File analysis events
            if event == "mime_type_detected":
                mime_type = data.get("mime_type", "unknown")
                detection_method = data.get("detection_method", "unknown")
                return f"{mime_type} ({detection_method})"
            elif event == "mime_type_detection_failed":
                file_path = data.get("file_path", "unknown")
                return f"failed for {Path(file_path).name if file_path != 'unknown' else 'unknown file'}"
            elif event == "mime_type_override":
                mime_type = data.get("mime_type", "unknown")
                return f"{mime_type} (hint)"
            elif event == "file_not_found":
                file_path = data.get("file_path", "unknown")
                file_hash = data.get("file_hash", "")
                if file_hash:
                    return f"{Path(file_path).name if file_path != 'None' else 'unknown'} (hash: {file_hash[:8]}...)"
                else:
                    return f"{Path(file_path).name if file_path != 'None' else 'unknown file'}"

            # Text extraction events
            elif event == "text_extracted":
                text_length = data.get("text_length", 0)
                if text_length > 1000:
                    return f"{text_length/1000:.1f}k chars"
                else:
                    return f"{text_length} chars"
            elif event == "text_extraction_skipped":
                reason = data.get("reason", "unknown")
                return f"skipped ({reason})"
            elif event == "text_extraction_supported":
                mime_type = data.get("mime_type", "unknown")
                return f"{mime_type} supported"

            # Date extraction events
            elif event == "date_extraction_completed":
                dates_found = data.get("dates_found", 0)
                if dates_found > 0:
                    extracted_date = data.get("extracted_date", "unknown")
                    return f"{dates_found} dates found: {extracted_date}"
                else:
                    return "No dates found"
            elif event == "date_extraction_skipped":
                reason = data.get("reason", "unknown")
                return f"skipped ({reason})"
            elif event == "date_extraction_started":
                word_count = data.get("word_count", 0)
                return f"{word_count} words to analyze"

            # LLM debugging events
            elif event == "llm_prompt_created":
                text_length = data.get("text_length", 0)
                prompt_length = data.get("prompt_length", 0)
                return f"text: {text_length} chars, prompt: {prompt_length} chars"
            elif event == "llm_response_received":
                response = data.get("response", "")
                response_length = data.get("response_length", 0)
                if response and response != "None":
                    return f"'{response}' ({response_length} chars)"
                else:
                    return "empty response"
            elif event == "text_truncated_for_llm":
                original_length = data.get("original_length", 0)
                truncated_length = data.get("truncated_length", 0)
                truncation_ratio = data.get("truncation_ratio", 0)
                return f"{original_length} → {truncated_length} chars ({truncation_ratio:.1%} kept)"

            # Query context events
            elif event == "query_context_used":
                num_chunks = data.get("num_chunks", 0)
                total_chars = data.get("total_context_chars", 0)
                question = data.get("question", "")[:50]
                context_preview = data.get("context_preview", "")

                # Format the context preview nicely
                if total_chars > 1000:
                    size_str = f"{total_chars/1000:.1f}k chars"
                else:
                    size_str = f"{total_chars} chars"

                # Show a snippet of the context
                if context_preview and len(context_preview) > 100:
                    context_snippet = context_preview[:100] + "..."
                else:
                    context_snippet = context_preview

                return f"\n🔍 Query: '{question}...'\n📚 Context: {num_chunks} chunks, {size_str}\n📄 Preview: {context_snippet}"

            elif event == "estimated_llm_prompt":
                prompt_length = data.get("prompt_length", 0)
                prompt_preview = data.get("prompt_preview", "")[:200]
                return f"Prompt ({prompt_length} chars): {prompt_preview}..."

            # Document events
            elif event == "document_created":
                word_count = data.get("word_count", 0)
                return f"{word_count} words indexed"
            elif event == "document_creation_started":
                content_length = data.get("content_length", 0)
                metadata_fields = data.get("metadata_fields", 0)
                return f"{content_length} chars, {metadata_fields} fields"
            elif event == "document_creation_failed":
                error = data.get("error", "unknown error")
                return str(error)
            elif event == "document_status_updated":
                status = data.get("status", "unknown")
                return f"status={status}"

            # File processing events
            elif event == "file_import_started":
                file_size = data.get("file_size")
                has_mime_hint = data.get("has_mime_hint", False)
                mime_type = data.get("mime_type")
                has_session = data.get("has_session", False)
                context_parts = [f"{mime_type}", f"{file_size}MB"]
                if has_mime_hint:
                    context_parts.append("with hint")
                if has_session:
                    context_parts.append("tracked")
                return " ".join(context_parts)
            elif event == "file_analysis_started":
                file_size_mb = data.get("file_size_mb", 0)
                return f"{file_size_mb}MB file"
            elif event == "file_hash_calculated":
                file_hash = data.get("file_hash", "unknown")
                return f"hash: {file_hash}"
            elif event == "file_processed":
                size_bytes = data.get("size_bytes", 0)
                mime_type = data.get("mime_type", "unknown")
                if size_bytes > 1024 * 1024:
                    size_str = f"{size_bytes / (1024*1024):.1f}MB"
                elif size_bytes > 1024:
                    size_str = f"{size_bytes / 1024:.1f}KB"
                else:
                    size_str = f"{size_bytes}B"
                return f"{size_str} {mime_type}"

            # Vault events
            elif event == "vault_storage_completed":
                vault_existed = data.get("vault_existed", False)
                return "existed" if vault_existed else "new file"

            # Duplicate detection events
            elif event == "duplicate_found":
                existing_doc_id = data.get("existing_doc_id", "unknown")
                return f"existing doc: {existing_doc_id[:8]}..."
            elif event == "duplicate_check_started":
                return "checking for duplicates"

            # Progress tracking events
            elif event == "progress_tracking_started":
                session_id = data.get("session_id", "unknown")
                return f"session: {session_id[:8]}..."
            elif event == "progress_tracking_completed":
                session_id = data.get("session_id", "unknown")
                return f"session: {session_id[:8]}... completed"

            # Tagging events
            elif event == "tags_applied":
                tags_count = data.get("tags_count", 0)
                tags = data.get("tags", [])
                if tags_count > 5:
                    return (
                        f"{tags_count} tags: {', '.join(tags)} + {tags_count - 5} more"
                    )
                else:
                    return f"{tags_count} tags: {', '.join(tags)}"

            # Success/completion events
            elif event == "file_import_success":
                word_count = data.get("word_count", 0)
                vault_existed = data.get("vault_existed", False)
                status = "duplicate" if vault_existed else "new"
                return f"{word_count} words, {status}"
            elif event == "text_extraction_completed":
                word_count = data.get("word_count", 0)
                has_text = data.get("has_text", False)
                if has_text:
                    return f"{word_count} words extracted"
                else:
                    return "no text found"

            # Error events
            elif event == "file_import_error":
                error_type = data.get("error_type", "Error")
                return f"{error_type}"
            elif event == "progress_error_failed":
                return "progress tracking failed"
            elif event == "metadata_update_failed":
                return "metadata update failed"

            # Default: return empty string for no context
            return ""

        def _get_operation_context(self, data: dict, operation: str) -> str:
            """Get operation-specific context information."""
            context_parts = []

            # File operations context
            if operation in ["file_storage", "file_import", "file_deletion"]:
                context_parts.extend(self._get_file_context(data))

            # Document operations context
            elif operation in [
                "document_addition",
                "document_analysis",
                "text_extraction",
            ]:
                context_parts.extend(self._get_document_context(data))

            # Query operations context
            elif operation in [
                "metadata_query",
                "document_retrieval",
                "llamaindex_query",
            ]:
                context_parts.extend(self._get_query_context(data))

            # Cleanup operations context
            elif operation in [
                "temp_file_cleanup",
                "vault_file_clearing",
                "data_cleanup",
            ]:
                context_parts.extend(self._get_cleanup_context(data))

            # System operations context
            elif operation in [
                "vault_initialization",
                "llama_index_setup",
                "query_engine_setup",
            ]:
                context_parts.extend(self._get_system_context(data))

            return f" ({', '.join(context_parts)})" if context_parts else ""

        def _get_file_context(self, data: dict) -> list:
            """Get context for file operations."""
            context = []

            # File size (from result data or direct field)
            size_bytes = data.get("size_bytes", 0)
            if size_bytes > 1024 * 1024:
                context.append(f"{size_bytes / (1024*1024):.1f}MB")
            elif size_bytes > 1024:
                context.append(f"{size_bytes / 1024:.1f}KB")
            elif size_bytes > 0:
                context.append(f"{size_bytes}B")

            # File existence/status
            if "existed" in data:
                existed = data.get("existed", False)
                context.append("existed" if existed else "new")

            # Boolean result (for operations like delete)
            if "result_value" in data:
                result = data.get("result_value")
                if isinstance(result, bool):
                    context.append("success" if result else "not_found")

            return context

        def _get_document_context(self, data: dict) -> list:
            """Get context for document operations."""
            context = []

            # Content length
            if "result_length" in data:
                length = data.get("result_length", 0)
                if length > 1000:
                    context.append(f"{length/1000:.1f}k chars")
                else:
                    context.append(f"{length} chars")

            # Result keys (for metadata operations)
            if "result_keys_count" in data:
                keys = data.get("result_keys_count", 0)
                context.append(f"{keys} fields")

            # Success status
            if "operation_success" in data:
                success = data.get("operation_success")
                if success is False:
                    context.append("failed")

            return context

        def _get_query_context(self, data: dict) -> list:
            """Get context for query operations."""
            context = []

            # Result count
            if "result_length" in data:
                count = data.get("result_length", 0)
                context.append(f"{count} results")

            # Result keys count (for metadata queries)
            if "result_keys_count" in data:
                count = data.get("result_keys_count", 0)
                context.append(f"{count} matches")

            return context

        def _get_cleanup_context(self, data: dict) -> list:
            """Get context for cleanup operations."""
            context = []

            # Files cleaned
            if "result_keys_count" in data:
                files = data.get("result_keys_count", 0)
                context.append(f"{files} files")

            # Bytes freed
            if "result_length" in data:
                bytes_freed = data.get("result_length", 0)
                if bytes_freed > 1024 * 1024:
                    context.append(f"{bytes_freed / (1024*1024):.1f}MB freed")
                elif bytes_freed > 1024:
                    context.append(f"{bytes_freed / 1024:.1f}KB freed")
                elif bytes_freed > 0:
                    context.append(f"{bytes_freed}B freed")

            return context

        def _get_system_context(self, data: dict) -> list:
            """Get context for system operations."""
            context = []

            # Success status
            if "operation_success" in data:
                success = data.get("operation_success")
                if success is True:
                    context.append("ready")
                elif success is False:
                    context.append("failed")

            return context

    return DevelopmentFormatter()
