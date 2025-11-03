"""
Shared response utilities for API routes.
"""

from typing import Any, Dict

from fastapi.responses import JSONResponse


def create_error_response(
    error_message: str,
    error_type: str = "InternalServerError",
    status_code: int = 500,
    **extra_fields: Any,
) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        error_message: Human-readable error message
        error_type: Type/category of error
        status_code: HTTP status code
        **extra_fields: Additional fields to include in response

    Returns:
        JSONResponse with error details
    """
    content: Dict[str, Any] = {
        "success": False,
        "error": error_message,
        "error_type": error_type,
        **extra_fields,
    }
    return JSONResponse(content=content, status_code=status_code)


def create_success_response(
    data: Dict[str, Any], status_code: int = 200
) -> Dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: Response data
        status_code: HTTP status code (not used in dict response, for consistency)

    Returns:
        Dictionary with success flag and data
    """
    return {"success": True, **data}
