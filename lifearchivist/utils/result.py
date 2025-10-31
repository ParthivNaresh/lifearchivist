"""
Result type for explicit error handling.

This module provides a Result type that represents either a successful operation
(Success) or a failed operation (Failure). This pattern makes error handling
explicit and provides consistent response formats for APIs and UIs.

Example:
    >>> result = Success({"user_id": 123})
    >>> if result.is_success():
    ...     print(result.value)
    {"user_id": 123}

    >>> result = Failure("User not found", error_type="NotFoundError")
    >>> result.to_dict()
    {"success": False, "error": "User not found", "error_type": "NotFoundError"}
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, Optional, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")


@dataclass
class Success(Generic[T]):
    """
    Represents a successful operation with a value.

    Attributes:
        value: The successful result value
        metadata: Optional metadata about the operation
    """

    value: T
    metadata: Optional[Dict[str, Any]] = None

    def is_success(self) -> bool:
        """Check if this is a success result."""
        return True

    def is_failure(self) -> bool:
        """Check if this is a failure result."""
        return False

    def unwrap(self) -> T:
        """
        Get the success value.

        Returns:
            The wrapped value
        """
        return self.value

    def unwrap_or(self, default: T) -> T:
        """
        Get the success value or a default.

        Args:
            default: Value to return if this is a Failure

        Returns:
            The wrapped value (always, since this is Success)
        """
        return self.value

    def unwrap_or_else(self, func: Callable[[Any], T]) -> T:
        """
        Get the success value or compute a default.

        Args:
            func: Function to call if this is a Failure

        Returns:
            The wrapped value (always, since this is Success)
        """
        return self.value

    def map(self, func: Callable[[T], Any]) -> "Result":
        """
        Transform the success value.

        Args:
            func: Function to apply to the value

        Returns:
            Success with transformed value
        """
        try:
            return Success(func(self.value), metadata=self.metadata)
        except Exception as e:
            return Failure(
                error=str(e),
                error_type=type(e).__name__,
                context={"original_value": str(self.value)},
            )

    def and_then(self, func: Callable[[T], "Result"]) -> "Result":
        """
        Chain operations that return Results.

        Args:
            func: Function that takes the value and returns a Result

        Returns:
            The result of calling func with the value
        """
        try:
            return func(self.value)
        except Exception as e:
            return Failure(
                error=str(e),
                error_type=type(e).__name__,
                context={"original_value": str(self.value)},
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with success=True and data field
        """
        result = {"success": True, "data": self.value}
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    def __bool__(self) -> bool:
        """Make Success truthy."""
        return True

    def __repr__(self) -> str:
        """String representation."""
        return f"Success({self.value})"

    def error_or(self, default: E) -> E:
        """
        Get error value or default (always returns default for Success).

        Args:
            default: Default error value to return

        Returns:
            The default value (always, since this is Success)
        """
        return default


@dataclass
class Failure(Generic[E]):
    """
    Represents a failed operation with an error.

    Attributes:
        error: The error message
        error_type: Type/category of error (e.g., "ValidationError")
        context: Additional context about the error
        recoverable: Whether the operation can be retried
        status_code: HTTP status code hint for API responses
    """

    error: E
    error_type: str = "UnknownError"
    context: Optional[Dict[str, Any]] = None
    recoverable: bool = False
    status_code: int = 500

    def is_success(self) -> bool:
        """Check if this is a success result."""
        return False

    def is_failure(self) -> bool:
        """Check if this is a failure result."""
        return True

    def unwrap(self) -> Any:
        """
        Attempt to get the value (will raise).

        Raises:
            RuntimeError: Always, since this is a Failure
        """
        raise RuntimeError(f"Called unwrap on Failure: {self.error}")

    def unwrap_or(self, default: Any) -> Any:
        """
        Get a default value since this is a failure.

        Args:
            default: Value to return

        Returns:
            The default value
        """
        return default

    def unwrap_or_else(self, func: Callable[[E], Any]) -> Any:
        """
        Compute a default value from the error.

        Args:
            func: Function to call with the error

        Returns:
            Result of calling func with the error
        """
        return func(self.error)

    def map(self, func: Callable) -> "Result":
        """
        No-op for Failure (preserves the error).

        Args:
            func: Function that would transform a success value

        Returns:
            This Failure unchanged
        """
        return self

    def and_then(self, func: Callable) -> "Result":
        """
        No-op for Failure (preserves the error).

        Args:
            func: Function that would chain another operation

        Returns:
            This Failure unchanged
        """
        return self

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dictionary with success=False and error fields
        """
        result = {
            "success": False,
            "error": str(self.error),
            "error_type": self.error_type,
        }
        if self.context:
            result["context"] = self.context
        if self.recoverable:
            result["recoverable"] = True
        return result

    def __bool__(self) -> bool:
        """Make Failure falsy."""
        return False

    def __repr__(self) -> str:
        """String representation."""
        return f"Failure({self.error_type}: {self.error})"

    def error_or(self, default: E) -> E:
        """
        Get error value or default.

        Args:
            default: Default error value (unused for Failure)

        Returns:
            The error value
        """
        return self.error


# Type alias for Result
Result = Union[Success[T], Failure[E]]


# Common error types with predefined status codes
class ErrorType:
    """Common error types with HTTP status codes."""

    VALIDATION_ERROR = ("ValidationError", 400, True)
    NOT_FOUND_ERROR = ("NotFoundError", 404, False)
    CONFLICT_ERROR = ("ConflictError", 409, True)
    AUTHENTICATION_ERROR = ("AuthenticationError", 401, False)
    AUTHORIZATION_ERROR = ("AuthorizationError", 403, False)
    RATE_LIMIT_ERROR = ("RateLimitError", 429, True)
    INTERNAL_ERROR = ("InternalError", 500, False)
    SERVICE_UNAVAILABLE = ("ServiceUnavailable", 503, True)
    TIMEOUT_ERROR = ("TimeoutError", 504, True)
    STORAGE_ERROR = ("StorageError", 500, True)
    INDEX_ERROR = ("IndexError", 500, True)
    NETWORK_ERROR = ("NetworkError", 503, True)


def validation_error(message: str, context: Optional[Dict[str, Any]] = None) -> Failure:
    """Create a validation error result."""
    error_type, status_code, recoverable = ErrorType.VALIDATION_ERROR
    return Failure(
        error=message,
        error_type=error_type,
        context=context,
        recoverable=recoverable,
        status_code=status_code,
    )


def not_found_error(message: str, context: Optional[Dict[str, Any]] = None) -> Failure:
    """Create a not found error result."""
    error_type, status_code, recoverable = ErrorType.NOT_FOUND_ERROR
    return Failure(
        error=message,
        error_type=error_type,
        context=context,
        recoverable=recoverable,
        status_code=status_code,
    )


def internal_error(message: str, context: Optional[Dict[str, Any]] = None) -> Failure:
    """Create an internal error result."""
    error_type, status_code, recoverable = ErrorType.INTERNAL_ERROR
    return Failure(
        error=message,
        error_type=error_type,
        context=context,
        recoverable=recoverable,
        status_code=status_code,
    )


def storage_error(message: str, context: Optional[Dict[str, Any]] = None) -> Failure:
    """Create a storage error result."""
    error_type, status_code, recoverable = ErrorType.STORAGE_ERROR
    return Failure(
        error=message,
        error_type=error_type,
        context=context,
        recoverable=recoverable,
        status_code=status_code,
    )


def service_unavailable(
    message: str, context: Optional[Dict[str, Any]] = None
) -> Failure:
    """Create a service unavailable error result."""
    error_type, status_code, recoverable = ErrorType.SERVICE_UNAVAILABLE
    return Failure(
        error=message,
        error_type=error_type,
        context=context,
        recoverable=recoverable,
        status_code=status_code,
    )


# Utility functions for working with Results
def collect_results(results: list[Result]) -> Result[list, str]:
    """
    Collect multiple Results into a single Result.

    If all are Success, returns Success with list of values.
    If any are Failure, returns the first Failure.

    Args:
        results: List of Result objects

    Returns:
        Success with list of values, or first Failure
    """
    values = []
    for result in results:
        if result.is_failure():
            return result
        values.append(result.unwrap())
    return Success(values)


def partition_results(results: list[Result]) -> tuple[list, list]:
    """
    Partition Results into successes and failures.

    Args:
        results: List of Result objects

    Returns:
        Tuple of (success_values, failures)
    """
    successes = []
    failures = []
    for result in results:
        if result.is_success():
            successes.append(result.unwrap())
        else:
            failures.append(result)
    return successes, failures
