"""
Custom HTTP exceptions for API routes.
"""

from typing import Dict, Optional

from fastapi import HTTPException, status


class ServiceUnavailableError(HTTPException):
    """Raised when a required service is not available."""

    def __init__(
        self,
        service_name: str,
        detail: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail or f"{service_name} not available",
            headers=headers,
        )


class ValidationError(HTTPException):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
            headers=headers,
        )


class ResourceNotFoundError(HTTPException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        if identifier:
            detail = f"{resource} not found: {identifier}"
        else:
            detail = f"{resource} not found"

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            headers=headers,
        )


class ConflictError(HTTPException):
    """Raised when a request conflicts with current state."""

    def __init__(
        self,
        message: str,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
            headers=headers,
        )


class InternalServerError(HTTPException):
    """Raised for internal server errors."""

    def __init__(
        self,
        operation: str,
        error: Exception,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{operation} failed: {str(error)}",
            headers=headers,
        )
