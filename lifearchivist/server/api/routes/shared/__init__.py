"""
Shared utilities for API routes.

Provides:
- Response builders (responses.py)
- Result unwrapping utilities (utils.py)
- Dependency injection helpers (dependencies.py)
"""

from .dependencies import get_server
from .utils import (
    extract_result_value,
    handle_service_result,
    unwrap_result_or_error,
    unwrap_result_to_json_response,
)

__all__ = [
    "get_server",
    "unwrap_result_or_error",
    "unwrap_result_to_json_response",
    "extract_result_value",
    "handle_service_result",
]
