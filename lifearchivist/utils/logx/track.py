# logx/track.py
import asyncio
import functools
import logging
import os
import random
import time
import tracemalloc
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

from .context import clear_span, current_context, set_span
from .structured import log_span

T = TypeVar("T")

# Configurable performance sampling to limit cost of tracemalloc
_PERF_SAMPLE_RATE = float(os.getenv("LOG_PERF_SAMPLE_RATE", "0.25"))
_MAX_ARG_STR = int(os.getenv("LOG_MAX_ARG_STR", "256"))
_SENSITIVE = tuple(
    k.strip()
    for k in os.getenv(
        "LOG_SENSITIVE_KEYS", "password,secret,token,apikey,authorization,api_key,auth"
    ).split(",")
)


def _now_ns() -> int:
    return time.monotonic_ns()


def _cpu_ns() -> int:
    return time.process_time_ns()


def _start_mem():
    try:
        tracemalloc.start(1)
        return tracemalloc.take_snapshot()
    except Exception:
        return None


def _end_mem(sn):
    try:
        if sn is None:
            return 0
        end = tracemalloc.take_snapshot()
        stats = end.compare_to(sn, "lineno")
        alloc = sum(s.size_diff for s in stats) // 1024  # KiB
        return int(alloc)
    except Exception:
        return 0


def _sanitize_keyval(k: str, v: Any) -> Any:
    lk = k.lower()
    if any(s in lk for s in _SENSITIVE):
        return "[REDACTED]"
    if isinstance(v, str):
        return v if len(v) <= _MAX_ARG_STR else (v[:_MAX_ARG_STR] + "…")
    if isinstance(v, (int, float, bool, type(None))):
        return v
    return f"<{type(v).__name__}>"


def _extract_args(kwargs: dict, include_args: Union[bool, List[str]]) -> Dict[str, Any]:
    if not include_args:
        return {}
    if include_args is True:
        keys = list(kwargs.keys())
    else:
        keys = [k for k in include_args if k in kwargs]
    return {f"arg_{k}": _sanitize_keyval(k, kwargs[k]) for k in keys}


def track(
    operation: Optional[str] = None,
    include_result: bool = False,
    include_args: Union[bool, List[str]] = False,
    track_performance: bool = True,
    frequency: str = "default",  # high_frequency|default|low_frequency|rare|always
    level: int = logging.INFO,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorate sync/async functions to emit:
      - span: operation_started
      - span: operation_completed/operation_failed with duration/cpu/memory deltas

    Args:
      operation: friendly operation name (defaults to function name)
      include_result: if True, log small primitives / presence-only for others
      include_args: False | True (all kwargs) | ['subset','of','kwargs']
      track_performance: if True, capture duration/cpu and (sampled) alloc_kib
      frequency: sampling hint used by the SamplingFilter
    """
    frequency = "always"

    def deco(func: Callable[..., T]) -> Callable[..., T]:
        op = operation or func.__name__

        def enter(kwargs: dict) -> Dict[str, Any]:
            parent = current_context().get("span_id")
            span = f"{int(time.time()*1e6):x}"
            set_span(span, parent)
            # emit started
            log_span("operation_started", op, {"frequency": frequency}, level)
            ctx: Dict[str, Any] = {
                "t0": _now_ns(),
                "c0": _cpu_ns(),
                "perf": track_performance and (random.random() < _PERF_SAMPLE_RATE),
                "mem0": None,
                "args": _extract_args(kwargs, include_args),
            }
            if ctx["perf"]:
                ctx["mem0"] = _start_mem()
            return ctx

        def leave(
            ctx: Dict[str, Any],
            success: bool,
            err: Optional[BaseException],
            result: Any = None,
        ) -> None:
            try:
                duration_ms = (_now_ns() - ctx["t0"]) // 1_000_000
                cpu_ms = (_cpu_ns() - ctx["c0"]) // 1_000_000
                alloc_kib = _end_mem(ctx["mem0"]) if ctx["perf"] else 0

                payload: Dict[str, Any] = {
                    "duration_ms": int(duration_ms),
                    "cpu_ms": int(cpu_ms),
                    "alloc_kib": int(alloc_kib),
                    "success": success,
                    "frequency": frequency,
                }
                if ctx["args"]:
                    payload.update(ctx["args"])
                if include_result and success:
                    payload["result_present"] = result is not None
                    if isinstance(result, (str, int, float, bool)):
                        payload["result_value"] = result

                if not success and err is not None:
                    payload["error_type"] = type(err).__name__
                    payload["error_message"] = str(err)

                log_span(
                    "operation_completed" if success else "operation_failed",
                    op,
                    payload,
                    logging.INFO if success else logging.ERROR,
                )
            finally:
                clear_span()

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            ctx = enter(kwargs)
            try:
                res = func(*args, **kwargs)
                leave(ctx, True, None, res)
                return res
            except BaseException as e:
                leave(ctx, False, e, None)
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            ctx = enter(kwargs)
            try:
                res = await func(*args, **kwargs)
                leave(ctx, True, None, res)
                return res
            except BaseException as e:
                leave(ctx, False, e, None)
                raise

        return cast(
            Callable[..., T],
            async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper,
        )

    return deco
