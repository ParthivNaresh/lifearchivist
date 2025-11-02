"""
Error formatting utilities for API responses.

Provides user-friendly error messages from LLM provider errors.
"""

import json
import re
from typing import Any, Dict

from lifearchivist.llm.exceptions import (
    InvalidRequestError,
    LLMProviderError,
)


def format_llm_error(error: Exception, model: str) -> str:
    """
    Extract user-friendly error message from LLM provider error.

    Args:
        error: Exception from LLM provider
        model: Model identifier

    Returns:
        User-friendly error message
    """
    if isinstance(error, LLMProviderError):
        if hasattr(error, "get_user_message"):
            return str(error.get_user_message())
        return error.message

    if isinstance(error, InvalidRequestError):
        return _format_invalid_request_error(error)

    return _format_legacy_error(error, model)


def _format_invalid_request_error(error: InvalidRequestError) -> str:
    """Format InvalidRequestError with parameter context."""
    if error.param:
        return f"Invalid parameter '{error.param}'. {error.message}"
    return error.message


def _format_legacy_error(error: Exception, model: str) -> str:
    """
    Format legacy RuntimeError exceptions with pattern matching.

    This handles errors from providers that haven't been updated
    to use structured exceptions yet.
    """
    error_str = str(error)

    parsed_message = _try_parse_json_error(error_str)
    if parsed_message:
        return parsed_message

    return _match_error_patterns(error_str, model)


def _try_parse_json_error(error_str: str) -> str | None:
    """Attempt to extract error message from JSON in error string."""
    try:
        json_match = re.search(r"\{[\s\S]*\}", error_str)
        if not json_match:
            return None

        error_json = json.loads(json_match.group())
        if "error" not in error_json:
            return None

        error_obj = error_json["error"]
        if not isinstance(error_obj, dict) or "message" not in error_obj:
            return None

        message = error_obj["message"]
        return _categorize_json_message(message)

    except (json.JSONDecodeError, KeyError, AttributeError):
        return None


def _categorize_json_message(message: str) -> str:
    """Categorize and format JSON error message."""
    message_lower = message.lower()

    if "credit balance" in message_lower:
        return "Your API credit balance is too low. Please add credits to your account."

    if "model incompatible" in message_lower or "incompatible request" in message_lower:
        return "Model doesn't support the requested parameters. Try adjusting temperature or other settings."

    if "rate limit" in message_lower:
        return "Rate limit exceeded. Please wait a moment and try again."

    if "invalid" in message_lower and "api key" in message_lower:
        return "Invalid API key. Please check your provider configuration."

    return message


def _check_credit_balance_error(error_str_lower: str) -> str | None:
    """Check for credit balance errors."""
    if "credit" in error_str_lower and "balance" in error_str_lower:
        return "Your API credit balance is too low. Please add credits to your account."
    return None


def _check_rate_limit_error(error_str_lower: str) -> str | None:
    """Check for rate limit errors."""
    if "rate limit" in error_str_lower or "too many requests" in error_str_lower:
        return "Rate limit exceeded. Please wait a moment and try again."
    return None


def _check_authentication_error(error_str_lower: str) -> str | None:
    """Check for authentication errors."""
    if "invalid" in error_str_lower and (
        "api key" in error_str_lower or "authentication" in error_str_lower
    ):
        return "Invalid API key. Please check your provider configuration."
    return None


def _check_model_availability_error(error_str_lower: str, model: str) -> str | None:
    """Check for model availability errors."""
    if "model" in error_str_lower and (
        "not found" in error_str_lower or "does not exist" in error_str_lower
    ):
        return f"Model '{model}' is not available. Please select a different model."
    return None


def _check_model_compatibility_error(error_str_lower: str, model: str) -> str | None:
    """Check for model compatibility errors."""
    if "incompatible" in error_str_lower and "temperature" in error_str_lower:
        return f"Model '{model}' doesn't support temperature parameter. Try a different model or adjust settings."
    return None


def _check_timeout_error(error_str_lower: str) -> str | None:
    """Check for timeout errors."""
    if "timeout" in error_str_lower or "timed out" in error_str_lower:
        return "Request timed out. Please try again."
    return None


def _check_network_error(error_str_lower: str) -> str | None:
    """Check for network errors."""
    if "connection" in error_str_lower or "network" in error_str_lower:
        return "Network error. Please check your connection and try again."
    return None


def _check_quota_error(error_str_lower: str) -> str | None:
    """Check for quota errors."""
    if "quota" in error_str_lower or "exceeded" in error_str_lower:
        return "API quota exceeded. Please check your account limits."
    return None


def _match_error_patterns(error_str: str, model: str) -> str:
    """Match error string against known patterns."""
    error_str_lower = error_str.lower()

    error_checks = [
        _check_credit_balance_error(error_str_lower),
        _check_rate_limit_error(error_str_lower),
        _check_authentication_error(error_str_lower),
        _check_model_availability_error(error_str_lower, model),
        _check_model_compatibility_error(error_str_lower, model),
        _check_timeout_error(error_str_lower),
        _check_network_error(error_str_lower),
        _check_quota_error(error_str_lower),
    ]

    for error_message in error_checks:
        if error_message:
            return error_message

    return f"An error occurred: {error_str[:200]}"


def create_error_metadata(
    error: Exception,
    provider_id: str,
    model: str,
    retryable: bool = True,
) -> Dict[str, Any]:
    """
    Create standardized error metadata for message storage.

    Args:
        error: Exception from LLM provider
        provider_id: Provider identifier
        model: Model identifier
        retryable: Whether the error is retryable

    Returns:
        Metadata dictionary for error message
    """
    if isinstance(error, LLMProviderError):
        return {
            "is_error": True,
            "error_type": error.error_type,
            "provider_id": error.provider_id,
            "model": error.model or model,
            "retryable": error.retryable,
            "raw_error": error.message[:500],
        }

    return {
        "is_error": True,
        "error_type": type(error).__name__,
        "provider_id": provider_id,
        "model": model,
        "retryable": retryable,
        "raw_error": str(error)[:500],
    }
