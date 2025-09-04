"""
Structured logging utilities for professional event-based logging.

Provides structured event logging, JSON formatting, and utilities
for creating searchable, queryable log entries.
"""

import json
import logging
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
        log_entry: Dict[str, Any] = {
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
            exception_info = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": (
                    self.formatException(record.exc_info) if record.exc_info else None
                ),
            }
            log_entry["exception"] = exception_info

        # Add process/thread info
        process_info = {
            "pid": record.process,
            "thread_id": record.thread,
            "thread_name": record.threadName,
        }
        log_entry["process"] = process_info

        # Add source location
        source_info = {
            "file": record.filename,
            "function": record.funcName,
            "line": record.lineno,
        }
        log_entry["source"] = source_info

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


class MetricsCollector:
    """
    Utility class for collecting and aggregating metrics during operation execution.

    Useful for operations that need to track multiple metrics and report them
    as a single structured event.
    """

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.metrics: Dict[str, Any] = {}
        self.start_time: Optional[float] = None

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

        if self.start_time is not None:
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
            message_content = record.getMessage()
            extras = []

            data = getattr(record, "structured_data", None)
            if data:
                # Lookup strategy: map keys -> formatter functions
                strategies = {
                    "duration_ms": lambda v: f"⏱️ {v}ms | {message_content}",
                    "operation": lambda v: f"op={v}",
                    "success": lambda v: "✅" if v else "❌",
                    "error": lambda v: f"error={v} ❌",
                }

                if "duration_ms" in data:
                    message_content = strategies["duration_ms"](data["duration_ms"])

                for key, fn in strategies.items():
                    if key != "duration_ms" and key in data:
                        extras.append(fn(data[key]))

                # Add any remaining keys not in strategies
                for key, value in data.items():
                    if key not in strategies:
                        extras.append(f"{key}={value}")

            # Build clean message with emoji timing prefix when present
            extras_str = " | ".join(extras)
            return f"{timestamp} | {record.levelname:5} | {message_content}" + (
                f" | {extras_str}" if extras_str else ""
            )

    return DevelopmentFormatter()
