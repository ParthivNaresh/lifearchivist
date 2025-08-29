"""
Professional logging decorators for automatic method instrumentation.

Provides decorators that automatically log method execution, timing,
exceptions, and other cross-cutting concerns without cluttering business logic.
"""

import asyncio
import functools
import logging
import time
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar

from .context import get_correlation_id
from .structured import log_event

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


def log_execution_time(
    operation_name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
) -> Callable[[F], F]:
    """
    Decorator to automatically log method execution time and basic metrics.

    Args:
        operation_name: Custom operation name (defaults to class.method)
        include_args: Whether to log method arguments (be careful with sensitive data)
        include_result: Whether to log return value size/type info
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            method_name = operation_name or f"{func.__qualname__}"

            # Extract context info
            correlation_id = get_correlation_id()

            # Build context
            context = {
                "method": method_name,
                "correlation_id": correlation_id,
                "args_count": len(args),
                "kwargs_count": len(kwargs),
            }

            if include_args:
                # Only log safe arguments (avoid logging sensitive data)
                safe_args = _extract_safe_args(args, kwargs)
                context.update(safe_args)

            # Log method start
            log_event("method_started", context)

            try:
                result = await func(*args, **kwargs)
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                success_context = {
                    **context,
                    "execution_time_ms": execution_time_ms,
                    "success": True,
                }

                if include_result and result is not None:
                    success_context.update(_extract_result_info(result))

                log_event("method_completed", success_context)
                return result

            except Exception as e:
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                error_context = {
                    **context,
                    "execution_time_ms": execution_time_ms,
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

                log_event("method_failed", error_context)
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            method_name = operation_name or f"{func.__qualname__}"

            correlation_id = get_correlation_id()

            context = {
                "method": method_name,
                "correlation_id": correlation_id,
                "args_count": len(args),
                "kwargs_count": len(kwargs),
            }

            if include_args:
                safe_args = _extract_safe_args(args, kwargs)
                context.update(safe_args)

            log_event("method_started", context)

            try:
                result = func(*args, **kwargs)
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                success_context = {
                    **context,
                    "execution_time_ms": execution_time_ms,
                    "success": True,
                }

                if include_result and result is not None:
                    success_context.update(_extract_result_info(result))

                log_event("method_completed", success_context)
                return result

            except Exception as e:
                execution_time_ms = int((time.perf_counter() - start_time) * 1000)

                error_context = {
                    **context,
                    "execution_time_ms": execution_time_ms,
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

                log_event("method_failed", error_context)
                raise

        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_exceptions(
    reraise: bool = True,
    include_stack_trace: bool = True,
    operation_name: Optional[str] = None,
) -> Callable[[F], F]:
    """
    Decorator to automatically log exceptions with full context.

    Args:
        reraise: Whether to reraise the exception after logging
        include_stack_trace: Whether to include full stack trace in logs
        operation_name: Custom operation name for logging
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            method_name = operation_name or f"{func.__qualname__}"

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_context = {
                    "method": method_name,
                    "correlation_id": get_correlation_id(),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

                if include_stack_trace:
                    error_context["stack_trace"] = traceback.format_exc()

                # Extract additional context from exception if available
                if hasattr(e, "__dict__"):
                    safe_attrs = {
                        k: v
                        for k, v in e.__dict__.items()
                        if not k.startswith("_")
                        and isinstance(v, (str, int, float, bool))
                    }
                    if safe_attrs:
                        error_context["exception_details"] = safe_attrs

                log_event("exception_caught", error_context)

                if reraise:
                    raise
                return None

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            method_name = operation_name or f"{func.__qualname__}"

            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = {
                    "method": method_name,
                    "correlation_id": get_correlation_id(),
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }

                if include_stack_trace:
                    error_context["stack_trace"] = traceback.format_exc()

                if hasattr(e, "__dict__"):
                    safe_attrs = {
                        k: v
                        for k, v in e.__dict__.items()
                        if not k.startswith("_")
                        and isinstance(v, (str, int, float, bool))
                    }
                    if safe_attrs:
                        error_context["exception_details"] = safe_attrs

                log_event("exception_caught", error_context)

                if reraise:
                    raise
                return None

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def log_method(
    operation_name: Optional[str] = None,
    include_args: bool = False,
    include_result: bool = False,
) -> Callable[[F], F]:
    """
    Combined decorator that applies both timing and exception logging.

    This is the most commonly used decorator for comprehensive method instrumentation.
    Always includes performance tracking as it's essential for observability.
    """

    def decorator(func: F) -> F:
        # Apply both decorators
        instrumented_func = log_execution_time(
            operation_name=operation_name,
            include_args=include_args,
            include_result=include_result,
        )(func)

        instrumented_func = log_exceptions(operation_name=operation_name)(
            instrumented_func
        )

        return instrumented_func

    return decorator


def _extract_safe_args(args: tuple, kwargs: dict) -> Dict[str, Any]:
    """Extract safe arguments for logging (avoid sensitive data)."""
    safe_context = {}

    # Common safe argument patterns
    safe_keys = {
        "document_id",
        "file_id",
        "path",
        "mime_type",
        "operation",
        "limit",
        "offset",
        "top_k",
        "similarity_threshold",
        "model",
        "temperature",
        "max_tokens",
    }

    # Process positional args (skip 'self' if present)
    if args:
        start_idx = 1 if len(args) > 0 and hasattr(args[0], "__class__") else 0
        for i, value in enumerate(args[start_idx:], start=start_idx):
            if isinstance(value, (str, int, float, bool)):
                if isinstance(value, str) and len(value) < 100:  # Only short strings
                    safe_context[f"arg_pos_{i}"] = value
                elif isinstance(value, (int, float, bool)):
                    safe_context[f"arg_pos_{i}"] = value

    # Add safe kwargs
    for key, value in kwargs.items():
        if key in safe_keys and isinstance(value, (str, int, float, bool)):
            if key == "path" and isinstance(value, str):
                # Only log filename, not full path for privacy
                safe_context[f"arg_{key}"] = (
                    value.split("/")[-1] if "/" in value else value
                )
            else:
                safe_context[f"arg_{key}"] = value

    return safe_context


def _extract_result_info(result: Any) -> Dict[str, Any]:
    """Extract safe information about the result."""
    result_info = {
        "result_type": type(result).__name__,
    }

    if isinstance(result, (list, tuple)):
        result_info["result_length"] = len(result)
    elif isinstance(result, dict):
        result_info["result_keys_count"] = len(result.keys())
        if "success" in result:
            result_info["operation_success"] = result["success"]
    elif isinstance(result, str):
        result_info["result_length"] = len(result)

    return result_info
