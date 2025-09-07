"""
Next-generation logging infrastructure for Life Archivist.

Simplified, high-performance logging with intelligent sampling and
single decorator that handles all use cases.
"""

from .smart_logger import track, log_operation_start, log_operation_success, log_operation_error
from .context import get_correlation_id, set_correlation_id
from .structured import log_event, StructuredLogger

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
