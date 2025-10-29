"""
LLM provider abstraction layer.

Provides unified interface for multiple LLM providers (Ollama, OpenAI, Anthropic, etc.)
with credential management, cost tracking, and streaming support.
"""

from .base_provider import (
    BaseHTTPProvider,
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    ModelInfo,
    ProviderType,
)
from .cost_tracker import Budget, CostRecord, CostSummary, CostTracker
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    InsufficientCreditsError,
    InvalidRequestError,
    LLMProviderError,
    ModelNotFoundError,
    ProviderAPIError,
    ProviderConfigurationError,
    ProviderNotInitializedError,
    RateLimitError,
    ServerError,
    StreamingError,
    TimeoutError,
    parse_provider_error,
)
from .provider_factory import ProviderManagerFactory
from .provider_health_monitor import HealthCheck, HealthStatus, ProviderHealthMonitor
from .provider_loader import ProviderLoader
from .provider_manager import LLMProviderManager
from .provider_registry import ProviderRegistry
from .provider_router import ProviderRouter, RoutingStrategy

__all__ = [
    # Base types
    "BaseHTTPProvider",
    "BaseLLMProvider",
    "LLMMessage",
    "LLMResponse",
    "LLMStreamChunk",
    "ModelInfo",
    "ProviderType",
    # Exceptions
    "LLMProviderError",
    "ProviderAPIError",
    "AuthenticationError",
    "RateLimitError",
    "InvalidRequestError",
    "InsufficientCreditsError",
    "ModelNotFoundError",
    "ServerError",
    "ConnectionError",
    "TimeoutError",
    "StreamingError",
    "ProviderNotInitializedError",
    "ProviderConfigurationError",
    "parse_provider_error",
    # Manager and services
    "LLMProviderManager",
    "ProviderManagerFactory",
    "ProviderRegistry",
    "ProviderRouter",
    "RoutingStrategy",
    "ProviderLoader",
    "CostTracker",
    "CostRecord",
    "CostSummary",
    "Budget",
    "ProviderHealthMonitor",
    "HealthCheck",
    "HealthStatus",
]
