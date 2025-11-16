# logx/formatters.py
import json
import logging
import os
import socket
import time
from typing import Any, Dict

_HOST = socket.gethostname()
_SERVICE = os.getenv("LOG_SERVICE", "app")

_DEV_MAX_KV = int(os.getenv("LOG_DEV_MAX_KV", "8"))  # how many key=val pairs to print
_DEV_MAX_VAL = int(os.getenv("LOG_DEV_MAX_VAL", "120"))  # max chars per value

_RESERVED = {
    "ts",
    "ts_epoch_ms",
    "kind",
    "event",
    "operation",
    "success",
    "frequency",
    "duration_ms",
    "cpu_ms",
    "alloc_kib",
    "peak_rss_kib",
    "error_type",
    "error_message",
    "stack",
    "logger",
    "service",
    "host",
    "pid",
    "correlation_id",
    "request_id",
    "session_id",
    "span_id",
    "parent_span_id",
}


def _val_to_str(v: Any) -> str:
    if isinstance(v, (int, float, bool)) or v is None:
        s = str(v)
    elif isinstance(v, (dict, list, tuple)):
        s = json.dumps(v, ensure_ascii=False)
    else:
        s = str(v)
    return s if len(s) <= _DEV_MAX_VAL else (s[:_DEV_MAX_VAL] + "…")


def _kv_suffix(sd: Dict[str, Any]) -> str:
    """
    Produce ' k1=v1 k2=v2 ...' for either sd['data'] (preferred) or
    the non-reserved top-level keys if no 'data' block is present.
    """
    # prefer nested data
    src = (
        sd.get("data")
        if isinstance(sd.get("data"), dict)
        else {k: v for k, v in sd.items() if k not in _RESERVED}
    )
    if not src:
        return ""
    # deterministic, capped
    items = sorted(src.items(), key=lambda kv: kv[0])[:_DEV_MAX_KV]
    return " " + " ".join(f"{k}={_val_to_str(v)}" for k, v in items)


class JsonFormatter(logging.Formatter):
    """Production: stable JSON schema that machines can parse."""

    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "service": _SERVICE,
            "host": _HOST,
            "pid": record.process,
        }
        data = getattr(record, "structured_data", None)
        if isinstance(data, dict):
            base.update(data)
        else:
            base.update(
                {
                    "kind": "log",
                    "event": "message",
                    "data": {"msg": record.getMessage()},
                }
            )
        if record.exc_info:
            base["error_type"] = record.exc_info[0].__name__
            base["stack"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


class DevFormatter(logging.Formatter):
    """Development: human-centric emoji lines like the output you shared."""

    def format(self, record: logging.LogRecord) -> str:
        ts = (
            time.strftime("%H:%M:%S", time.localtime(record.created))
            + f".{int(record.msecs):03d}"
        )
        sd: Dict[str, Any] = getattr(record, "structured_data", {}) or {}
        data = getattr(record, "structured_data", {}) or {}
        event = data.get("event")
        kind = data.get("kind")
        op = data.get("operation")

        if kind == "span" and event == "operation_started":
            return f"{ts} | {record.levelname:4} | 🚀 {op} started{_kv_suffix(sd)}"
        if kind == "span" and event == "operation_completed":
            d = sd.get("duration_ms")
            return f"{ts} | {record.levelname:4} | ⚡ {d}ms {op}{_kv_suffix(sd)}"
        if kind == "span" and event == "operation_failed":
            em = sd.get("error_message", "")
            return f"{ts} | ERROR | ❌ {op} failed: {em[:160]}{_kv_suffix(sd)}"

        # events
        if kind == "event" and event:
            return f"{ts} | {record.levelname:4} | 📝 {event}{_kv_suffix(sd)}"

        # fallback
        return f"{ts} | {record.levelname:4} | {record.getMessage()}"
