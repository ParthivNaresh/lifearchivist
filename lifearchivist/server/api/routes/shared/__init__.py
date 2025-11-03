"""
Shared utilities for API routes.

This module provides common functionality used across multiple route domains.
"""

from .dependencies import get_server
from .responses import create_error_response, create_success_response

__all__ = [
    "get_server",
    "create_error_response",
    "create_success_response",
]
