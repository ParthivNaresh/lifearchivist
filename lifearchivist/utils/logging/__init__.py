"""
Next-generation logging infrastructure for Life Archivist.

Simplified, high-performance logging with intelligent sampling and
single decorator that handles all use cases.
"""

from .context import get_correlation_id, set_correlation_id
from .smart_logger import (
    log_operation_error,
    log_operation_start,
    log_operation_success,
    track,
)
from .structured import StructuredLogger, log_event

__all__ = [
    # Primary API
    "track",
    "log_event",
    "get_correlation_id",
    "set_correlation_id",
    # Manual logging helpers
    "log_operation_start",
    "log_operation_success",
    "log_operation_error",
    # Advanced usage
    "StructuredLogger",
]
