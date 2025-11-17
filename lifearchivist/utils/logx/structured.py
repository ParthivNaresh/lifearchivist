# logx/structured.py
import logging
import time
from typing import Any, Dict, Optional, cast

from .context import current_context

# Use a single app-level logger; root pipeline handles transport/formatting.
_LOG = logging.getLogger("app")


def _record(
    kind: str, event: str, payload: Dict[str, Any], level: int
) -> logging.LogRecord:
    data: Dict[str, Any] = {
        "ts_epoch_ms": int(time.time() * 1000),
        "kind": kind,  # "event" or "span"
        "event": event,
        "data": payload or {},  # put domain-specific fields under "data"
    }
    # Include context (scheduler/filter also reinforces this)
    data.update({k: v for k, v in current_context().items() if v})

    rec = _LOG.makeRecord(_LOG.name, level, "(structured)", 0, event, (), None)
    cast(Any, rec).structured_data = data
    return rec


def log_event(
    event: str, data: Optional[Dict[str, Any]] = None, level: int = logging.INFO
) -> None:
    """Log a domain/business event with optional payload."""
    rec = _record("event", event, data or {}, level)
    _LOG.handle(rec)


def log_span(
    event: str,
    operation: str,
    data: Optional[Dict[str, Any]] = None,
    level: int = logging.INFO,
) -> None:
    payload = {"operation": operation}
    if data:
        payload.update(data)
    rec = _record("span", event, payload, level)

    # Promote key span fields to top-level for renderers/parsers
    sd: Dict[str, Any] = cast(Any, rec).structured_data
    sd["operation"] = operation
    for k in (
        "duration_ms",
        "cpu_ms",
        "alloc_kib",
        "peak_rss_kib",
        "success",
        "error_type",
        "error_message",
        "frequency",
    ):
        v = payload.get(k)
        if v is not None:
            sd[k] = v

    _LOG.handle(rec)
