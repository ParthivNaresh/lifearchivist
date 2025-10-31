"""
Base provider abstraction for LLM services.

Defines the interface that all LLM providers must implement,
ensuring consistent behavior across Ollama, OpenAI, Anthropic, etc.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional

import aiohttp

if TYPE_CHECKING:
    from .provider_config import BaseProviderConfig
    from .provider_metadata import BaseProviderMetadata

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported LLM provider types."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    GROQ = "groq"
    MISTRAL = "mistral"
    CUSTOM = "custom"


@dataclass
class LLMMessage:
    """
    Unified message format across all providers.

    Attributes:
        role: Message role ('system', 'user', 'assistant')
        content: Message content/text
        name: Optional name for the message sender
        metadata: Additional provider-specific metadata
    """

    role: str
    content: str
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate message role."""
        valid_roles = {"system", "user", "assistant", "function", "tool"}
        if self.role not in valid_roles:
            raise ValueError(
                f"Invalid role '{self.role}'. Must be one of: {valid_roles}"
            )


@dataclass
class LLMResponse:
    """
    Unified response format from LLM providers.

    Attributes:
        content: Generated text response
        model: Model identifier used for generation
        provider: Provider type that generated the response
        tokens_used: Total tokens consumed (prompt + completion)
        prompt_tokens: Tokens in the prompt
        completion_tokens: Tokens in the completion
        cost_usd: Estimated cost in USD
        finish_reason: Reason generation stopped ('stop', 'length', 'error', etc.)
        metadata: Additional provider-specific response data
    """

    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    cost_usd: Optional[float] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class LLMStreamChunk:
    """
    Streaming response chunk from LLM providers.

    Attributes:
        content: Text content in this chunk
        is_final: Whether this is the final chunk
        tokens_used: Total tokens used (only available in final chunk)
        finish_reason: Reason generation stopped (only in final chunk)
        metadata: Additional chunk-specific metadata
    """

    content: str
    is_final: bool = False
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


@dataclass
class ModelInfo:
    """
    Information about an available model.

    Attributes:
        id: Unique model identifier (e.g., "gpt-4o")
        name: Human-readable model name
        provider: Provider type (e.g., "openai", "anthropic")
        provider_id: Specific provider instance ID (e.g., "work-openai", "personal-openai")
        context_window: Maximum context window size
        max_output_tokens: Maximum output tokens
        supports_streaming: Whether streaming is supported
        supports_functions: Whether function calling is supported
        supports_vision: Whether vision/image inputs are supported
        cost_per_1k_input: Cost per 1K input tokens in USD
        cost_per_1k_output: Cost per 1K output tokens in USD
        metadata: Additional model-specific information (org, endpoint, etc.)
    """

    id: str
    name: str
    provider: str
    provider_id: str
    context_window: int = 4096
    max_output_tokens: int = 2048
    supports_streaming: bool = True
    supports_functions: bool = False
    supports_vision: bool = False
    cost_per_1k_input: Optional[float] = None
    cost_per_1k_output: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class BaseHTTPProvider:
    """
    Mixin class for HTTP-based LLM providers.

    Provides connection pooling and session management for providers
    that communicate over HTTP/HTTPS (Ollama, OpenAI, Anthropic, etc.).

    This is a concrete mixin class, not an abstract base class.
    All methods are implemented and ready to use.
    """

    def __init__(self):
        """Initialize HTTP session management."""
        self._session: Optional[aiohttp.ClientSession] = None

    def _create_connector(
        self,
        max_connections: int = 100,
        max_connections_per_host: int = 30,
        keepalive_timeout: int = 30,
    ) -> aiohttp.TCPConnector:
        """
        Create optimized TCP connector for connection pooling.

        Args:
            max_connections: Maximum total connections
            max_connections_per_host: Maximum connections per host
            keepalive_timeout: Keep-alive timeout in seconds

        Returns:
            Configured TCPConnector
        """
        return aiohttp.TCPConnector(
            limit=max_connections,
            limit_per_host=max_connections_per_host,
            ttl_dns_cache=300,  # DNS cache TTL (5 minutes)
            use_dns_cache=True,
            keepalive_timeout=keepalive_timeout,
            enable_cleanup_closed=True,
            force_close=False,  # Enable connection reuse
        )

    def _create_timeout(
        self, total: int, connect: int = 10, sock_read: int = 30
    ) -> aiohttp.ClientTimeout:
        """
        Create timeout configuration.

        Args:
            total: Total request timeout in seconds
            connect: Connection timeout in seconds
            sock_read: Socket read timeout in seconds

        Returns:
            Configured ClientTimeout
        """
        return aiohttp.ClientTimeout(
            total=total,
            connect=connect,
            sock_read=sock_read,
        )

    async def _initialize_session(
        self,
        timeout_seconds: int,
        max_connections: int = 100,
        max_connections_per_host: int = 30,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Initialize HTTP session with connection pooling.

        Args:
            timeout_seconds: Total request timeout
            max_connections: Maximum total connections
            max_connections_per_host: Maximum connections per host
            headers: Optional default headers
        """
        if self._session is not None:
            return

        timeout = self._create_timeout(timeout_seconds)
        connector = self._create_connector(max_connections, max_connections_per_host)

        self._session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            connector_owner=True,
            headers=headers,
        )

    async def _cleanup_session(self) -> None:
        """
        Clean up HTTP session and release connections.

        Properly closes the session and waits for connections to close gracefully.
        """
        if self._session and not self._session.closed:
            await self._session.close()
            # Give connections time to close gracefully
            await asyncio.sleep(0.25)

        self._session = None

    def _ensure_session(self) -> aiohttp.ClientSession:
        """
        Ensure session is initialized and return it.

        Returns:
            Active ClientSession

        Raises:
            RuntimeError: If session not initialized
        """
        if self._session is None or self._session.closed:
            raise RuntimeError("HTTP session not initialized. Call initialize() first.")
        return self._session


class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers.

    All providers must implement this interface to ensure consistent
    behavior across different LLM services.

    Lifecycle:
        1. __init__: Create provider instance
        2. initialize: Set up resources (connections, sessions)
        3. [use provider for requests]
        4. cleanup: Release resources
    """

    def __init__(self, provider_id: str, config: "BaseProviderConfig"):
        """
        Initialize provider with typed configuration.

        Args:
            provider_id: Unique identifier for this provider instance
            config: Typed provider configuration
        """
        self.provider_id = provider_id
        self.config = config
        self.provider_type = self._get_provider_type()
        self._initialized = False
        self.metadata: Optional["BaseProviderMetadata"] = None

    @abstractmethod
    def _get_provider_type(self) -> ProviderType:
        """
        Return the provider type.

        Returns:
            ProviderType enum value
        """
        pass

    async def initialize(self) -> None:
        """
        Initialize provider resources.

        Called once after construction to set up persistent resources
        like HTTP sessions, connection pools, etc.

        Subclasses should override this to set up their specific resources.
        Must be idempotent (safe to call multiple times).

        Raises:
            RuntimeError: If initialization fails
        """
        if self._initialized:
            return
        self._initialized = True

    async def cleanup(self) -> None:
        """
        Clean up provider resources.

        Called when provider is being removed or application is shutting down.
        Should release all resources (close sessions, connections, etc.).

        Subclasses should override this to clean up their specific resources.
        Must be idempotent (safe to call multiple times).
        """
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if provider is initialized."""
        return self._initialized

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a response (non-streaming).

        Args:
            messages: List of conversation messages
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            RuntimeError: If generation fails
            ValueError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generate a streaming response.

        Args:
            messages: List of conversation messages
            model: Model identifier to use
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Yields:
            LLMStreamChunk objects with incremental content

        Raises:
            RuntimeError: If streaming fails
            ValueError: If parameters are invalid
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """
        List available models for this provider.

        Returns:
            List of ModelInfo objects describing available models

        Raises:
            RuntimeError: If model listing fails
        """
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate provider credentials/configuration.

        Returns:
            True if credentials are valid, False otherwise
        """
        pass

    @abstractmethod
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> float:
        """
        Estimate cost for token usage.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        pass

    def get_provider_name(self) -> str:
        """
        Get human-readable provider name.

        Returns:
            Provider name string
        """
        return self.provider_type.value.title()

    def __repr__(self) -> str:
        """String representation of provider."""
        return f"{self.__class__.__name__}(id={self.provider_id}, type={self.provider_type.value})"
