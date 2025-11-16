# logx/context.py
import contextvars
import secrets
from contextlib import contextmanager
from typing import Dict, Optional

# Core IDs
_correlation_id = contextvars.ContextVar("correlation_id", default=None)
_request_id = contextvars.ContextVar("request_id", default=None)
_session_id = contextvars.ContextVar("session_id", default=None)
_user_id_h = contextvars.ContextVar("user_id_hashed", default=None)

# Tracing-ish
_span_id = contextvars.ContextVar("span_id", default=None)
_parent_span_id = contextvars.ContextVar("parent_span_id", default=None)


def _id(hex_bytes: int = 8) -> str:
    return secrets.token_hex(hex_bytes)


def set_request_context(
    correlation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id_hashed: Optional[str] = None,
) -> None:
    _correlation_id.set(correlation_id or _id(8))
    _request_id.set(request_id or _id(8))
    _session_id.set(session_id)
    _user_id_h.set(user_id_hashed)


def set_span(span_id: Optional[str], parent_span_id: Optional[str]) -> None:
    _span_id.set(span_id)
    _parent_span_id.set(parent_span_id)


def clear_span() -> None:
    _span_id.set(None)
    _parent_span_id.set(None)


def current_context() -> Dict[str, Optional[str]]:
    return {
        "correlation_id": _correlation_id.get(),
        "request_id": _request_id.get(),
        "session_id": _session_id.get(),
        "user_id_hashed": _user_id_h.get(),
        "span_id": _span_id.get(),
        "parent_span_id": _parent_span_id.get(),
    }


@contextmanager
def log_context(**kv):
    """Temporarily push ad-hoc context fields (e.g., conversation_id='...')."""
    # You can enrich via structured log payload (preferred); this is a convenience.
    # Example: with log_context(conversation_id=cid): ...
    token_map = {}
    try:
        # create a synthetic contextvar per key to avoid global collision
        for k, v in kv.items():
            var = contextvars.ContextVar(f"ctx_{k}", default=None)
            token_map[var] = var.set(v)
        yield
    finally:
        for var, tok in token_map.items():
            var.reset(tok)
