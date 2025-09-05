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


def add_context(**kwargs) -> None:
    """
    Add key-value pairs to the current operation context.

    Args:
        **kwargs: Key-value pairs to add to context
    """
    current_context = _operation_context.get() or {}
    updated_context = {**current_context, **kwargs}
    _operation_context.set(updated_context)


@contextmanager
def log_context(operation: str, correlation_id: Optional[str] = None, **context_data):
    """
    Context manager for scoped logging with automatic operation tracking.

    All log events within this context will automatically include the
    correlation ID and operation context.

    Args:
        operation: Name of the operation being performed
        correlation_id: Optional correlation ID (generates one if not provided)
        **context_data: Additional context data to include in all logs

    Example:
        async def process_file(self, path: str):
            with log_context(operation="file_processing", file_path=path):
                # All logs in here automatically include operation and file_path
                log_event("processing_started")
                result = await self.extract_text()
                log_event("text_extracted", word_count=len(result.split()))
    """
    # Set up correlation ID
    if correlation_id is None:
        correlation_id = get_correlation_id()
    else:
        set_correlation_id(correlation_id)

    # Save current context to restore later
    previous_context = get_operation_context()

    # Prepare operation context - inherit from previous context, then add new data
    operation_data = {
        **previous_context,  # Inherit from current context (including indent)
        "operation": operation,
        "correlation_id": correlation_id,
        **context_data,
    }

    try:
        # Set new context
        _operation_context.set(operation_data)
        yield correlation_id
    except Exception:
        raise
    finally:
        # Restore previous context
        _operation_context.set(previous_context)


class AsyncLogContext:
    """
    Async context manager for logging with automatic resource management.

    Useful for longer-running operations that need to maintain context
    across multiple await points.
    """

    def __init__(
        self, operation: str, correlation_id: Optional[str] = None, **context_data
    ):
        self.operation = operation
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.context_data = context_data
        self.start_time: Optional[float] = None
        self.previous_context: Optional[Dict[str, Any]] = None

    async def __aenter__(self):
        """Enter the async context."""
        import time

        self.start_time = time.perf_counter()

        # Set correlation ID
        set_correlation_id(self.correlation_id)

        # Prepare operation context
        operation_data = {
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            **self.context_data,
        }

        # Save current context
        self.previous_context = get_operation_context()

        # Set new context
        _operation_context.set(operation_data)

        # Log operation start
        log_event("async_operation_started", operation_data)

        return self.correlation_id

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context."""
        import time

        # Calculate execution time safely with proper type checking
        if self.start_time is not None:
            execution_time_ms = int((time.perf_counter() - self.start_time) * 1000)
        else:
            # Fallback for cases where start_time wasn't set
            execution_time_ms = 0

        operation_data = {
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            "execution_time_ms": execution_time_ms,
            **self.context_data,
        }

        if exc_type is None:
            # Successful completion
            log_event("async_operation_completed", {**operation_data, "success": True})
        else:
            # Failed completion
            log_event(
                "async_operation_failed",
                {
                    **operation_data,
                    "success": False,
                    "error_type": exc_type.__name__ if exc_type else "Unknown",
                    "error_message": str(exc_val) if exc_val else "Unknown error",
                },
            )

        # Restore previous context - always restore even if None to clear context
        _operation_context.set(self.previous_context)


def create_child_context(**additional_context) -> str:
    """
    Create a child context that inherits from the current context.

    Useful for sub-operations that need their own correlation ID
    but want to maintain parent context.

    Args:
        **additional_context: Additional context data for the child

    Returns:
        New correlation ID for the child context
    """
    parent_context = get_operation_context()
    parent_correlation_id = get_correlation_id()

    child_correlation_id = str(uuid.uuid4())
    child_context = {
        **parent_context,
        "parent_correlation_id": parent_correlation_id,
        "correlation_id": child_correlation_id,
        **additional_context,
    }

    _operation_context.set(child_context)
    set_correlation_id(child_correlation_id)

    return child_correlation_id


@contextmanager
def isolated_context(**context_data):
    """
    Create an isolated logging context that doesn't inherit from parent.

    Useful for background tasks or operations that should be tracked
    independently from the current request context.

    Args:
        **context_data: Context data for the isolated context
    """
    # Save current state
    previous_correlation = _correlation_id.get()
    previous_context = get_operation_context()

    try:
        # Create isolated context
        new_correlation_id = str(uuid.uuid4())
        _correlation_id.set(new_correlation_id)
        _operation_context.set({"correlation_id": new_correlation_id, **context_data})

        yield new_correlation_id

    finally:
        # Restore previous state
        _correlation_id.set(previous_correlation)
        _operation_context.set(previous_context)
