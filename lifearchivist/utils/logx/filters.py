# logx/filters.py
import logging
import os
import random
import time
from typing import Any, Dict

from .context import current_context


# ---------- Context injection ----------
class ContextFilter(logging.Filter):
    """Injects correlation/request/session/span ids into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = current_context()
        sd = getattr(record, "structured_data", None)
        # attach as attributes so formatters/handlers can see them
        for k, v in ctx.items():
            if v is not None and not hasattr(record, k):
                setattr(record, k, v)
        # also into structured payload
        if isinstance(sd, dict):
            for k, v in ctx.items():
                if v is not None and k not in sd:
                    sd[k] = v
        return True


# ---------- Redaction & clamping ----------
_SENSITIVE_KEYS = tuple(
    k.strip()
    for k in os.getenv(
        "LOG_SENSITIVE_KEYS", "password,secret,token,apikey,authorization,api_key,auth"
    ).split(",")
)

_MAX_STR = int(os.getenv("LOG_MAX_STR", "2048"))
_MAX_LIST = int(os.getenv("LOG_MAX_LIST", "50"))


class RedactFilter(logging.Filter):
    def _scrub_value(self, k: str, v: Any):
        if isinstance(v, str) and len(v) > _MAX_STR:
            return v[:_MAX_STR] + "…"
        return v

    def _scrub_dict(self, d: Dict[str, Any]) -> None:
        for k, v in list(d.items()):
            lk = k.lower()
            if any(s in lk for s in _SENSITIVE_KEYS):
                d[k] = "[REDACTED]"
            elif isinstance(v, dict):
                self._scrub_dict(v)
            elif isinstance(v, list):
                clipped = v[:_MAX_LIST]
                d[k] = [self._scrub_value(k, x) for x in clipped]
                if len(v) > _MAX_LIST:
                    d[k].append("…")
            else:
                d[k] = self._scrub_value(k, v)

    def filter(self, record: logging.LogRecord) -> bool:
        sd = getattr(record, "structured_data", None)
        if isinstance(sd, dict):
            self._scrub_dict(sd)
        return True


# ---------- Sampling ----------
_DEFAULT_INFO_RATE = float(os.getenv("LOG_SAMPLE_DEFAULT", "0.10"))
_FREQ_RATES = {
    "always": 1.0,
    "high_frequency": 0.25,
    "default": _DEFAULT_INFO_RATE,
    "low_frequency": 0.02,
    "rare": 0.005,
}


class SamplingFilter(logging.Filter):
    """Probabilistically drops INFO/DEBUG events based on 'frequency' hint."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno >= logging.WARNING:
            return True
        sd = getattr(record, "structured_data", None)
        if not isinstance(sd, dict):
            return True
        rate = _FREQ_RATES.get(sd.get("frequency", "default"), _DEFAULT_INFO_RATE)
        return random.random() < rate


# ---------- Simple duplicate suppression ----------
_DEDUP_WINDOW_MS = int(os.getenv("LOG_DEDUP_WINDOW_MS", "0"))  # 0 disables


class DedupFilter(logging.Filter):
    """
    Collapses bursts of identical INFO messages for a short window.
    Keeps WARNING+ intact. Uses a tiny in-memory LRU keyed by (event, operation).
    """

    def __init__(self) -> None:
        super().__init__()
        self._last: dict[tuple, float] = {}
        self._max = 4096

    def filter(self, record: logging.LogRecord) -> bool:
        if _DEDUP_WINDOW_MS <= 0 or record.levelno >= logging.WARNING:
            return True
        sd = getattr(record, "structured_data", None)
        if not isinstance(sd, dict):
            return True
        key = (sd.get("event"), sd.get("operation"))
        now = time.monotonic() * 1000
        last = self._last.get(key)
        self._last[key] = now
        if len(self._last) > self._max:
            # crude eviction: clear oldest half
            for k in list(self._last.keys())[: self._max // 2]:
                self._last.pop(k, None)
        if last and (now - last) < _DEDUP_WINDOW_MS:
            return False
        return True
