"""
Context management for scoped logging with correlation IDs and request tracking.

Provides context managers and utilities for maintaining logging context
across async operations and request boundaries.
"""

import contextvars
import uuid
from contextlib import contextmanager
from typing import Any, Dict, Optional

from .structured import log_event

# Context variables for request-scoped data
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)
_operation_context: contextvars.ContextVar[Optional[Dict[str, Any]]] = (
    contextvars.ContextVar("operation_context", default=None)
)


def get_correlation_id() -> str:
    """
    Get the current correlation ID, generating one if none exists.

    Returns:
        Correlation ID string for tracking requests across components
    """
    correlation_id = _correlation_id.get()
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
        _correlation_id.set(correlation_id)
    return correlation_id


def set_correlation_id(correlation_id: str) -> None:
    """
    Set the correlation ID for the current context.

    Args:
        correlation_id: UUID string to use for request tracking
    """
    _correlation_id.set(correlation_id)


def get_operation_context() -> Dict[str, Any]:
    """
    Get the current operation context dictionary.

    Returns:
        Dictionary containing operation-scoped context data
    """
    context = _operation_context.get()
    return context.copy() if context is not None else {}
