"""
Structured exception hierarchy for LLM providers.

Provides granular error handling with rich context for debugging and user feedback.
"""

from typing import Any, Dict, Optional


class LLMProviderError(Exception):
    """
    Base exception for all LLM provider errors.

    Attributes:
        message: Human-readable error message
        provider_id: Identifier of the provider that raised the error
        model: Model identifier (if applicable)
        error_type: Categorization of error type
        retryable: Whether the operation can be retried
        metadata: Additional context about the error
    """

    def __init__(
        self,
        message: str,
        provider_id: str,
        model: Optional[str] = None,
        error_type: str = "unknown",
        retryable: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.provider_id = provider_id
        self.model = model
        self.error_type = error_type
        self.retryable = retryable
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for serialization.

        Returns:
            Dictionary representation of the error
        """
        return {
            "error": self.message,
            "error_type": self.error_type,
            "provider_id": self.provider_id,
            "model": self.model,
            "retryable": self.retryable,
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation of the error."""
        parts = [self.message]
        if self.provider_id:
            parts.append(f"(provider: {self.provider_id})")
        if self.model:
            parts.append(f"(model: {self.model})")
        return " ".join(parts)


class ProviderAPIError(LLMProviderError):
    """
    Error from provider API with HTTP context.

    Attributes:
        status_code: HTTP status code
        response_body: Raw response body from API
        request_id: Provider's request ID (if available)
    """

    def __init__(
        self,
        message: str,
        provider_id: str,
        status_code: int,
        response_body: str,
        model: Optional[str] = None,
        request_id: Optional[str] = None,
        retryable: bool = False,
    ):
        error_type = self._categorize_status_code(status_code)
        metadata = {
            "status_code": status_code,
            "response_body": response_body[:1000],
            "request_id": request_id,
        }

        super().__init__(
            message=message,
            provider_id=provider_id,
            model=model,
            error_type=error_type,
            retryable=retryable,
            metadata=metadata,
        )

        self.status_code = status_code
        self.response_body = response_body
        self.request_id = request_id

    @staticmethod
    def _categorize_status_code(status_code: int) -> str:
        """
        Categorize HTTP status code into error type.

        Args:
            status_code: HTTP status code

        Returns:
            Error type string
        """
        if status_code == 400:
            return "invalid_request"
        elif status_code == 401:
            return "authentication_error"
        elif status_code == 403:
            return "permission_denied"
        elif status_code == 404:
            return "not_found"
        elif status_code == 429:
            return "rate_limit_exceeded"
        elif 500 <= status_code < 600:
            return "server_error"
        else:
            return "api_error"


class AuthenticationError(ProviderAPIError):
    """
    Authentication or authorization failure.

    Raised when API key is invalid, expired, or lacks permissions.
    """

    USER_MESSAGE = "Invalid API key. Please check your provider configuration."

    def __init__(
        self,
        message: str,
        provider_id: str,
        status_code: int,
        response_body: str,
        model: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            status_code=status_code,
            response_body=response_body,
            model=model,
            retryable=False,
        )

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return self.USER_MESSAGE


class RateLimitError(ProviderAPIError):
    """
    Rate limit exceeded error.

    Attributes:
        retry_after: Seconds to wait before retrying (if provided by API)
        limit_type: Type of limit exceeded (requests, tokens, etc.)
    """

    USER_MESSAGE = "Rate limit exceeded. Please wait a moment and try again."

    def __init__(
        self,
        message: str,
        provider_id: str,
        status_code: int,
        response_body: str,
        model: Optional[str] = None,
        retry_after: Optional[int] = None,
        limit_type: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            status_code=status_code,
            response_body=response_body,
            model=model,
            retryable=True,
        )

        self.retry_after = retry_after
        self.limit_type = limit_type

        if retry_after:
            self.metadata["retry_after"] = retry_after
        if limit_type:
            self.metadata["limit_type"] = limit_type

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        if self.retry_after:
            return f"Rate limit exceeded. Please wait {self.retry_after} seconds and try again."
        return self.USER_MESSAGE


class InvalidRequestError(ProviderAPIError):
    """
    Invalid request parameters or format.

    Attributes:
        param: Parameter that caused the error (if identified)
        error_code: Provider-specific error code
    """

    def __init__(
        self,
        message: str,
        provider_id: str,
        status_code: int,
        response_body: str,
        model: Optional[str] = None,
        param: Optional[str] = None,
        error_code: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            status_code=status_code,
            response_body=response_body,
            model=model,
            retryable=False,
        )

        self.param = param
        self.error_code = error_code

        if param:
            self.metadata["param"] = param
        if error_code:
            self.metadata["error_code"] = error_code


class InsufficientCreditsError(ProviderAPIError):
    """
    Insufficient credits or quota.

    Raised when account has insufficient credits or quota to complete request.
    """

    USER_MESSAGE = (
        "Your API credit balance is too low. Please add credits to your account."
    )

    def __init__(
        self,
        message: str,
        provider_id: str,
        status_code: int,
        response_body: str,
        model: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            status_code=status_code,
            response_body=response_body,
            model=model,
            retryable=False,
        )

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return self.USER_MESSAGE


class ModelNotFoundError(ProviderAPIError):
    """
    Requested model not found or not available.
    """

    def __init__(
        self,
        message: str,
        provider_id: str,
        status_code: int,
        response_body: str,
        model: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            status_code=status_code,
            response_body=response_body,
            model=model,
            retryable=False,
        )

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return (
            f"Model '{self.model}' is not available. Please select a different model."
        )


class ServerError(ProviderAPIError):
    """
    Provider server error (5xx status codes).

    Typically transient and retryable.
    """

    USER_MESSAGE = "Provider server error. Please try again in a moment."

    def __init__(
        self,
        message: str,
        provider_id: str,
        status_code: int,
        response_body: str,
        model: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            status_code=status_code,
            response_body=response_body,
            model=model,
            retryable=True,
        )

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return self.USER_MESSAGE


class ConnectionError(LLMProviderError):
    """
    Network connection error.

    Raised when unable to establish connection to provider.
    """

    USER_MESSAGE = "Network error. Please check your connection and try again."

    def __init__(
        self,
        message: str,
        provider_id: str,
        model: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            model=model,
            error_type="connection_error",
            retryable=True,
            metadata={"original_error": str(original_error)} if original_error else {},
        )

        self.original_error = original_error

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return self.USER_MESSAGE


class TimeoutError(LLMProviderError):
    """
    Request timeout error.

    Raised when request exceeds timeout threshold.
    """

    def __init__(
        self,
        message: str,
        provider_id: str,
        timeout_seconds: int,
        model: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            model=model,
            error_type="timeout",
            retryable=True,
            metadata={"timeout_seconds": timeout_seconds},
        )

        self.timeout_seconds = timeout_seconds

    def get_user_message(self) -> str:
        """Get user-friendly error message."""
        return (
            f"Request timed out after {self.timeout_seconds} seconds. Please try again."
        )


class StreamingError(LLMProviderError):
    """
    Error during streaming response.

    Attributes:
        chunks_received: Number of chunks successfully received before error
    """

    def __init__(
        self,
        message: str,
        provider_id: str,
        model: Optional[str] = None,
        chunks_received: int = 0,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            provider_id=provider_id,
            model=model,
            error_type="streaming_error",
            retryable=False,
            metadata={
                "chunks_received": chunks_received,
                "original_error": str(original_error) if original_error else None,
            },
        )

        self.chunks_received = chunks_received
        self.original_error = original_error


class ProviderNotInitializedError(LLMProviderError):
    """
    Provider not properly initialized.

    Raised when attempting to use provider before calling initialize().
    """

    def __init__(self, provider_id: str):
        super().__init__(
            message=f"Provider '{provider_id}' not initialized. Call initialize() first.",
            provider_id=provider_id,
            error_type="not_initialized",
            retryable=False,
        )


class ProviderConfigurationError(LLMProviderError):
    """
    Provider configuration error.

    Raised when provider configuration is invalid or incomplete.
    """

    def __init__(
        self,
        message: str,
        provider_id: str,
        config_field: Optional[str] = None,
    ):
        metadata = {"config_field": config_field} if config_field else {}

        super().__init__(
            message=message,
            provider_id=provider_id,
            error_type="configuration_error",
            retryable=False,
            metadata=metadata,
        )

        self.config_field = config_field


def parse_provider_error(
    error: Exception,
    provider_id: str,
    model: Optional[str] = None,
) -> LLMProviderError:
    """
    Parse generic exception into structured provider error.

    Attempts to extract structured information from exception and
    convert to appropriate LLMProviderError subclass.

    Args:
        error: Original exception
        provider_id: Provider identifier
        model: Model identifier

    Returns:
        Structured LLMProviderError instance
    """
    if isinstance(error, LLMProviderError):
        return error

    error_str = str(error)
    error_str_lower = error_str.lower()

    if "timeout" in error_str_lower or "timed out" in error_str_lower:
        return TimeoutError(
            message=error_str,
            provider_id=provider_id,
            timeout_seconds=120,
            model=model,
        )

    if "connection" in error_str_lower or "network" in error_str_lower:
        return ConnectionError(
            message=error_str,
            provider_id=provider_id,
            model=model,
            original_error=error,
        )

    return LLMProviderError(
        message=error_str,
        provider_id=provider_id,
        model=model,
        error_type="unknown",
        retryable=False,
        metadata={"original_exception": type(error).__name__},
    )
