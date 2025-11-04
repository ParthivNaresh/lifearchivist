"""
Shared utilities for API routes.

Provides:
- Response builders (responses.py)
- Result unwrapping utilities (utils.py)
- Dependency injection helpers (dependencies.py)
"""

from .dependencies import get_server
from .responses import (
    create_error_response,
    create_success_response,
    error_response,
    internal_error_response,
    not_found_response,
    service_unavailable_response,
    success_response,
    validation_error_response,
)
from .utils import (
    extract_result_value,
    handle_service_result,
    unwrap_result_or_error,
    unwrap_result_to_json_response,
)

__all__ = [
    "get_server",
    "error_response",
    "success_response",
    "service_unavailable_response",
    "validation_error_response",
    "not_found_response",
    "internal_error_response",
    "create_error_response",
    "create_success_response",
    "unwrap_result_or_error",
    "unwrap_result_to_json_response",
    "extract_result_value",
    "handle_service_result",
]
