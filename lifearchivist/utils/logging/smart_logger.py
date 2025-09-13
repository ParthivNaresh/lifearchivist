"""
Next-generation logging system - single decorator handles everything.

Replaces @log_method, log_context, MetricsCollector, and manual log_event calls
with one intelligent decorator that adapts to usage patterns.
"""

import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from .context import get_correlation_id
from .structured import log_event

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


class LogConfig:
    """Global configuration for smart logging."""

    # Performance settings
    SAMPLE_RATES = {
        "high_frequency": 0.1,  # Only log 10% of high-freq operations
        "medium_frequency": 0.5,  # Log 50% of medium-freq operations
        "low_frequency": 1.0,  # Log all low-freq operations
    }

    # Argument filtering
    SENSITIVE_KEYS = {"password", "token", "secret", "key", "api_key", "auth"}
    LARGE_CONTENT_KEYS = {"content", "text", "data", "body"}
    MAX_ARG_LENGTH = 100

    # Operation categorization
    HIGH_FREQUENCY_OPS = {
        "query",
        "search",
        "retrieve",
        "get",
        "list",
        "check",
        "validate",
    }

    CRITICAL_OPS = {"add_document", "delete", "update", "create", "initialize", "setup"}


def track(
    operation: Optional[str] = None,
    level: int = logging.INFO,
    frequency: str = "low_frequency",  # high_frequency, medium_frequency, low_frequency
    include_args: Union[bool, List[str]] = True,
    include_result: bool = True,
    track_performance: bool = True,
    emit_events: bool = True,  # Set to False for silent operations
):
    """
    Single decorator that intelligently handles all logging needs.

    Args:
        operation: Operation name (auto-detected from function if None)
        level: Log level for this operation
        frequency: Sampling frequency category
        include_args: True for all args, List[str] for specific args, False for none
        include_result: Whether to log return value info
        track_performance: Whether to track timing metrics
        emit_events: Whether to emit log events (False for silent mode)

    Examples:
        @track()  # Basic tracking with defaults
        @track(frequency="high_frequency")  # Sampled logging for hot paths
        @track(include_args=["document_id"], track_performance=True)  # Selective args
        @track(emit_events=False)  # Silent mode - only log on errors
    """

    def decorator(func: F) -> F:
        op_name = operation or _get_operation_name(func)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Early exit for sampled operations
            if not _should_log(op_name, frequency):
                return await func(*args, **kwargs)

            tracker = BaseOperationTracker(
                operation=op_name,
                level=level,
                include_args=include_args,
                include_result=include_result,
                track_performance=track_performance,
                emit_events=emit_events,
                args=args,
                kwargs=kwargs,
            )

            tracker.on_enter()
            try:
                result = await func(*args, **kwargs)
                tracker.set_result(result)
                tracker.on_exit(None, None, None)
                return result
            except Exception as e:
                tracker.on_exit(type(e), e, None)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not _should_log(op_name, frequency):
                return func(*args, **kwargs)

            tracker = BaseOperationTracker(
                operation=op_name,
                level=level,
                include_args=include_args,
                include_result=include_result,
                track_performance=track_performance,
                emit_events=emit_events,
                args=args,
                kwargs=kwargs,
            )

            tracker.on_enter()
            try:
                result = func(*args, **kwargs)
                tracker.set_result(result)
                tracker.on_exit(None, None, None)
                return result
            except Exception as e:
                tracker.on_exit(type(e), e, None)
                raise

        if asyncio.iscoroutinefunction(func):
            return cast(F, async_wrapper)
        else:
            return cast(F, sync_wrapper)

    return decorator


class BaseOperationTracker:
    """Base tracker that handles all logging for an operation."""

    def __init__(
        self,
        operation: str,
        level: int,
        include_args: Union[bool, List[str]],
        include_result: bool,
        track_performance: bool,
        emit_events: bool,
        args: tuple,
        kwargs: dict,
    ):
        self.operation = operation
        self.level = level
        self.include_args = include_args
        self.include_result = include_result
        self.track_performance = track_performance
        self.emit_events = emit_events
        self.args = args
        self.kwargs = kwargs

        # Runtime state
        self.start_time: Optional[float] = None
        self.correlation_id: Optional[str] = None
        self.result: Any = None
        self.metrics: Dict[str, Any] = {}

    def on_enter(self) -> None:
        """Called when entering the tracked operation."""
        if self.track_performance:
            self.start_time = time.perf_counter()

        self.correlation_id = get_correlation_id()

        # Build operation context
        context = self._build_start_context()

        # Emit start event only if requested and not high-frequency
        if self.emit_events and self.level <= logging.INFO:
            log_event("operation_started", context, self.level)

    def on_exit(
        self, exc_type: Optional[type], exc_val: Optional[Exception], exc_tb: Any
    ) -> None:
        """Called when exiting the tracked operation."""
        # Calculate metrics
        if self.track_performance and self.start_time:
            duration_ms = int((time.perf_counter() - self.start_time) * 1000)
            self.metrics["duration_ms"] = duration_ms

        # Build final context
        context = self._build_exit_context(exc_type, exc_val)

        # Emit completion event
        if self.emit_events:
            event_name = (
                "operation_completed" if exc_type is None else "operation_failed"
            )
            event_level = self.level if exc_type is None else logging.ERROR
            log_event(event_name, context, event_level)

    def set_result(self, result: Any) -> None:
        """Set the operation result for logging."""
        self.result = result

    def add_metric(self, key: str, value: Any) -> None:
        """Add a custom metric to the operation."""
        self.metrics[key] = value

    def _build_start_context(self) -> Dict[str, Any]:
        """Build context for operation start."""
        context = {
            "operation": self.operation,
            "correlation_id": self.correlation_id,
        }

        # Add safe arguments
        if self.include_args:
            safe_args = _extract_safe_args(self.args, self.kwargs, self.include_args)
            context.update(safe_args)

        return context

    def _build_exit_context(
        self, exc_type: Optional[type], exc_val: Optional[Exception]
    ) -> Dict[str, Any]:
        """Build context for operation exit."""
        context = {
            "operation": self.operation,
            "correlation_id": self.correlation_id,
            "success": exc_type is None,
            **self.metrics,
        }

        # Add result info if requested and successful
        if self.include_result and exc_type is None and self.result is not None:
            context.update(_extract_result_info(self.result))

        # Add error info if failed
        if exc_type is not None:
            context.update(
                {
                    "error_type": exc_type.__name__,
                    "error_message": str(exc_val) if exc_val else "",
                }
            )

        return context


class OperationTracker(BaseOperationTracker):
    """Async context manager that handles all logging for an operation."""

    async def __aenter__(self):
        self.on_enter()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.on_exit(exc_type, exc_val, exc_tb)


class SyncOperationTracker(BaseOperationTracker):
    """Synchronous context manager that handles all logging for an operation."""

    def __enter__(self):
        self.on_enter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.on_exit(exc_type, exc_val, exc_tb)


# Utility functions


def _get_operation_name(func: Callable) -> str:
    """Extract operation name from function."""
    if hasattr(func, "__qualname__"):
        return func.__qualname__.replace(".", "_").lower()
    return func.__name__.lower()


def _should_log(operation: str, frequency: str) -> bool:
    """Determine if operation should be logged based on sampling."""
    import random

    sample_rate = LogConfig.SAMPLE_RATES.get(frequency, 1.0)

    # Always log critical operations
    if any(critical in operation.lower() for critical in LogConfig.CRITICAL_OPS):
        return True

    # Sample based on frequency
    return random.random() < sample_rate


def _extract_safe_args(
    args: tuple, kwargs: dict, include_spec: Union[bool, List[str]]
) -> Dict[str, Any]:
    """Extract safe arguments for logging."""
    safe_args: Dict[str, Any] = {}

    # Handle include specification
    if include_spec is True:
        # Include all safe arguments
        include_keys = set(kwargs.keys())
    elif isinstance(include_spec, list):
        # Include only specified keys
        include_keys = set(include_spec)
    else:
        # Include nothing
        return safe_args

    # Process kwargs
    for key, value in kwargs.items():
        if key not in include_keys:
            continue

        safe_args[f"arg_{key}"] = _sanitize_value(key, value)

    return safe_args


def _sanitize_value(key: str, value: Any) -> Any:
    """Sanitize a single value for logging."""
    # Handle sensitive data
    if any(sensitive in key.lower() for sensitive in LogConfig.SENSITIVE_KEYS):
        return "[REDACTED]"

    # Handle large content
    if key.lower() in LogConfig.LARGE_CONTENT_KEYS and isinstance(value, str):
        if len(value) > LogConfig.MAX_ARG_LENGTH:
            return f"<{len(value)} chars>"
        else:
            return value[: LogConfig.MAX_ARG_LENGTH]

    # Handle safe types
    if isinstance(value, (str, int, float, bool, type(None))):
        if isinstance(value, str) and len(value) > LogConfig.MAX_ARG_LENGTH:
            return f"{value[:LogConfig.MAX_ARG_LENGTH]}..."
        else:
            return value
    else:
        return f"<{type(value).__name__}>"


def _extract_result_info(result: Any) -> Dict[str, Any]:
    """Extract safe information about the result."""
    result_info: Dict[str, Any] = {"result_type": type(result).__name__}

    if isinstance(result, (list, tuple)):
        result_info["result_length"] = len(result)
    elif isinstance(result, dict):
        result_info["result_keys_count"] = len(result.keys())
        if "success" in result:
            result_info["operation_success"] = result["success"]
    elif isinstance(result, str):
        result_info["result_length"] = len(result)
    elif isinstance(result, bool):
        result_info["result_value"] = result

    return result_info


# Convenience functions for manual logging


def log_operation_start(operation: str, **context):
    """Manually log operation start."""
    context.update(
        {
            "operation": operation,
            "correlation_id": get_correlation_id(),
        }
    )
    log_event("operation_started", context)


def log_operation_success(operation: str, duration_ms: Optional[int] = None, **context):
    """Manually log operation success."""
    context.update(
        {
            "operation": operation,
            "correlation_id": get_correlation_id(),
            "success": True,
        }
    )
    if duration_ms is not None:
        context["duration_ms"] = duration_ms
    log_event("operation_completed", context)


def log_operation_error(
    operation: str, error: Exception, duration_ms: Optional[int] = None, **context
):
    """Manually log operation error."""
    context.update(
        {
            "operation": operation,
            "correlation_id": get_correlation_id(),
            "success": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }
    )
    if duration_ms is not None:
        context["duration_ms"] = duration_ms
    log_event("operation_failed", context, logging.ERROR)
