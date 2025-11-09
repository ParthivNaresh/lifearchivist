"""
Shared utilities for API route handlers.

Provides common functionality for:
- Result type unwrapping and validation
- Document metadata extraction
- Vault file management
- Error response handling
"""

from typing import Any, Optional, TypeVar

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from ..constants import HTTPStatus

T = TypeVar("T")


def unwrap_result_or_error(
    result: Any,
    expected_type: type[T],
    error_message: str = "Operation failed",
) -> T:
    """
    Unwrap a Result object and validate its type, or raise HTTPException.

    Args:
        result: Result object to unwrap
        expected_type: Expected type of the result value
        error_message: Error message prefix for failures

    Returns:
        The unwrapped value of the expected type

    Raises:
        HTTPException: If result is a failure or type mismatch
    """
    if hasattr(result, "is_failure") and result.is_failure():
        raise HTTPException(
            status_code=getattr(
                result, "status_code", HTTPStatus.INTERNAL_SERVER_ERROR
            ),
            detail=f"{error_message}: {getattr(result, 'error', 'Unknown error')}",
        )

    if not hasattr(result, "value"):
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"{error_message}: Invalid result object",
        )

    value = result.value
    if not isinstance(value, expected_type):
        raise HTTPException(
            status_code=500,
            detail=f"{error_message}: Expected {expected_type.__name__}, got {type(value).__name__}",
        )

    return value


def unwrap_result_to_json_response(result: Any) -> Optional[JSONResponse]:
    """
    Check if Result is a failure and return JSONResponse if so, otherwise None.

    Args:
        result: Result object to check

    Returns:
        JSONResponse if result is a failure, None if success
    """
    if hasattr(result, "is_failure") and result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=getattr(
                result, "status_code", HTTPStatus.INTERNAL_SERVER_ERROR
            ),
        )
    return None


def extract_result_value(result: Any, expected_type: type[T], default: T) -> T:
    """
    Safely extract value from Result object with type checking and default fallback.

    Args:
        result: Result object to extract from
        expected_type: Expected type of the value
        default: Default value if extraction fails

    Returns:
        Extracted value or default
    """
    if not hasattr(result, "value"):
        return default

    value = result.value
    if isinstance(value, expected_type):
        return value

    return default


def handle_service_result(result: Any) -> Optional[JSONResponse]:
    """
    Handle service result and return error response if failed.

    Args:
        result: Service result object

    Returns:
        JSONResponse if result is failure, None if success
    """
    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )
    return None
