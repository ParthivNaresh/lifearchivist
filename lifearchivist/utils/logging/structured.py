"""
Structured logging utilities for professional event-based logging.

Provides structured event logging, JSON formatting, and utilities
for creating searchable, queryable log entries.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Get logger for this module
logger = logging.getLogger(__name__)


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging that creates searchable log entries.

    Outputs logs in JSON format with consistent field names and data types
    for easy parsing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add structured data if present
        if hasattr(record, "structured_data") and record.structured_data:
            log_entry.update(record.structured_data)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": (
                    self.formatException(record.exc_info) if record.exc_info else None
                ),
            }

        # Add process/thread info
        log_entry["process"] = {
            "pid": record.process,
            "thread_id": record.thread,
            "thread_name": record.threadName,
        }

        # Add source location
        log_entry["source"] = {
            "file": record.filename,
            "function": record.funcName,
            "line": record.lineno,
        }

        return json.dumps(log_entry, default=str, separators=(",", ":"))


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

    Example:
        log_event("document_processed", {
            "document_id": "123",
            "processing_time_ms": 1500,
            "word_count": 500
        })
    """
    structured_logger = get_structured_logger()
    structured_logger.event(event_name, data, level)


def log_performance(operation: str, duration_ms: int, **metrics):
    """
    Convenience function for logging performance metrics.

    Args:
        operation: Name of the operation
        duration_ms: Duration in milliseconds
        **metrics: Additional performance metrics
    """
    structured_logger = get_structured_logger()
    structured_logger.performance(operation, duration_ms, metrics)


def log_business_event(
    event_type: str, entity_id: Optional[str] = None, **business_data
):
    """
    Log business/domain events for analytics and monitoring.

    Args:
        event_type: Type of business event (e.g., 'document_ingested', 'search_performed')
        entity_id: ID of the primary entity involved
        **business_data: Business-specific data
    """
    event_data = {
        "business_event": True,
        "event_type": event_type,
    }

    if entity_id:
        event_data["entity_id"] = entity_id

    event_data.update(business_data)

    log_event("business_event", event_data)


class MetricsCollector:
    """
    Utility class for collecting and aggregating metrics during operation execution.

    Useful for operations that need to track multiple metrics and report them
    as a single structured event.
    """

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.metrics: Dict[str, Any] = {}
        self.start_time = None

    def start(self):
        """Start timing the operation."""
        import time

        self.start_time = time.perf_counter()

    def add_metric(self, name: str, value: Any):
        """Add a metric to the collector."""
        self.metrics[name] = value

    def increment(self, name: str, amount: int = 1):
        """Increment a counter metric."""
        self.metrics[name] = self.metrics.get(name, 0) + amount

    def set_success(self, success: bool = True):
        """Set the success status."""
        self.metrics["success"] = success

    def set_error(self, error: Exception):
        """Set error information."""
        self.metrics.update(
            {
                "success": False,
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        )

    def report(self, event_name: Optional[str] = None):
        """Report all collected metrics as a structured event."""
        import time

        if self.start_time:
            duration_ms = int((time.perf_counter() - self.start_time) * 1000)
            self.metrics["duration_ms"] = duration_ms

        event_name = event_name or f"{self.operation_name}_metrics"
        log_event(event_name, self.metrics)


def create_development_formatter() -> logging.Formatter:
    """
    Create a human-readable formatter for development environments.

    Returns a formatter that outputs clean, readable logs for development
    while still including structured data.
    """

    class DevelopmentFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            # Format timestamp
            timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[
                :-3
            ]

            # Check for structured data to build components
            # correlation_info = ""
            operation_info = ""
            status_info = ""
            message_content = record.getMessage()
            error_info = ""
            data = None

            if hasattr(record, "structured_data") and record.structured_data:
                data = record.structured_data

                # Add timing prefix with emoji for performance logs
                if "duration_ms" in data:
                    message_content = f"⏱️  {data['duration_ms']}ms | {message_content}"

                # if "correlation_id" in data:
                #     short_id = data["correlation_id"][:8]
                #     correlation_info = f" | {short_id}"

                if "operation" in data:
                    operation_info = f" | {data['operation']}"

                # Add success/failure indicator
                if "success" in data:
                    status = "✅" if data["success"] else "❌"
                    status_info = f" | {status}"

                if "error" in data:
                    error_info = f" | {data['error']} ❌"

            # Build clean message with emoji timing prefix when present
            message = f"{timestamp} | {record.levelname:5} | {message_content}{operation_info}{status_info}{error_info}"

            return message

    return DevelopmentFormatter()


def setup_structured_logging(
    level: str = "INFO", use_json: bool = True, logger_name: str = "lifearchivist"
) -> logging.Logger:
    """
    Set up structured logging with appropriate formatter.

    Args:
        level: Log level string
        use_json: Whether to use JSON formatting (vs development formatting)
        logger_name: Name of the logger to configure

    Returns:
        Configured logger instance
    """
    log_level = getattr(logging, level.upper())

    # Get or create logger
    structured_logger = logging.getLogger(logger_name)
    structured_logger.setLevel(log_level)

    # Remove existing handlers
    for handler in structured_logger.handlers[:]:
        structured_logger.removeHandler(handler)

    # Create handler with appropriate formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = create_development_formatter()

    handler.setFormatter(formatter)
    structured_logger.addHandler(handler)

    # Don't propagate to avoid duplication
    structured_logger.propagate = False

    return structured_logger
