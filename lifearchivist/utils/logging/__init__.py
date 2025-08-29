"""
Professional logging infrastructure for Life Archivist.

Provides decorators, context managers, and structured logging utilities
for production-grade observability and debugging.
"""

from .context import get_correlation_id, log_context
from .decorators import log_exceptions, log_execution_time, log_method
from .structured import StructuredLogger, log_event

__all__ = [
    "log_context",
    "get_correlation_id",
    "log_execution_time",
    "log_exceptions",
    "log_method",
    "log_event",
    "StructuredLogger",
]
