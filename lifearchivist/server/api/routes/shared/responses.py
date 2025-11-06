"""
Shared response utilities for API routes.
"""

from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse


def success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: Response data

    Returns:
        Dictionary with success flag and data
    """
    return {"success": True, **data}


def error_response(
    error: str,
    error_type: str = "InternalServerError",
    status_code: int = 500,
    **extra_fields: Any,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        error: Human-readable error message
        error_type: Type/category of error
        status_code: HTTP status code
        **extra_fields: Additional fields to include in response

    Returns:
        JSONResponse with error details
    """
    content: Dict[str, Any] = {
        "success": False,
        "error": error,
        "detail": error,
        "error_type": error_type,
        **extra_fields,
    }
    return JSONResponse(content=content, status_code=status_code)


def service_unavailable_response(
    service_name: str,
    message: Optional[str] = None,
) -> JSONResponse:
    """
    Create a 503 Service Unavailable response.

    Args:
        service_name: Name of the unavailable service
        message: Optional custom message

    Returns:
        JSONResponse with 503 status
    """
    error_msg = message or f"{service_name} not available"
    return error_response(
        error=error_msg,
        error_type="ServiceUnavailable",
        status_code=503,
    )


def validation_error_response(
    message: str,
    **extra_fields: Any,
) -> JSONResponse:
    """
    Create a 400 Validation Error response.

    Args:
        message: Validation error message
        **extra_fields: Additional fields to include

    Returns:
        JSONResponse with 400 status
    """
    return error_response(
        error=message,
        error_type="ValidationError",
        status_code=400,
        **extra_fields,
    )


def not_found_response(
    resource: str,
    identifier: Optional[str] = None,
) -> JSONResponse:
    """
    Create a 404 Not Found response.

    Args:
        resource: Type of resource not found
        identifier: Optional resource identifier

    Returns:
        JSONResponse with 404 status
    """
    if identifier:
        message = f"{resource} not found: {identifier}"
    else:
        message = f"{resource} not found"

    return error_response(
        error=message,
        error_type="NotFoundError",
        status_code=404,
    )


def internal_error_response(
    operation: str,
    error: Exception,
) -> JSONResponse:
    """
    Create a 500 Internal Server Error response.

    Args:
        operation: Operation that failed
        error: Exception that occurred

    Returns:
        JSONResponse with 500 status
    """
    return error_response(
        error=f"{operation} failed: {str(error)}",
        error_type=type(error).__name__,
        status_code=500,
    )


create_error_response = error_response
create_success_response = success_response
