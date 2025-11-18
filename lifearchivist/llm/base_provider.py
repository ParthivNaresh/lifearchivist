"""
Base provider abstraction for LLM services.

Defines the interface that all LLM providers must implement,
ensuring consistent behavior across Ollama, OpenAI, Anthropic, etc.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    cast,
)

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
        self, total: int, connect: int = 10, sock_read: Optional[int] = None
    ) -> aiohttp.ClientTimeout:
        """
        Create timeout configuration.

        Args:
            total: Total request timeout in seconds
            connect: Connection timeout in seconds
            sock_read: Socket read timeout in seconds (defaults to total if not specified)

        Returns:
            Configured ClientTimeout
        """
        if sock_read is None:
            sock_read = total

        return aiohttp.ClientTimeout(
            total=total,
            connect=connect,
            sock_read=sock_read,
        )

    def _initialize_session(
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

    def _handle_http_error(
        self,
        status: int,
        error_text: str,
        model: str,
        provider_name: str,
        error_log_event: str,
    ) -> None:
        """
        Handle HTTP error response.

        Args:
            status: HTTP status code
            error_text: Error response text
            model: Model identifier
            provider_name: Provider name
            error_log_event: Log event name

        Raises:
            RuntimeError: Always raises with formatted error message
        """
        from ..utils.logx import log_event

        log_event(
            error_log_event,
            {
                "status": status,
                "error": error_text[:500],
                "model": model,
            },
            level=logging.ERROR,
        )
        raise RuntimeError(
            f"{provider_name} streaming failed (HTTP {status}): {error_text}"
        )

    def _should_skip_sse_line(self, line_str: str) -> bool:
        """
        Check if SSE line should be skipped.

        Args:
            line_str: Decoded and stripped line string

        Returns:
            True if line should be skipped, False otherwise
        """
        return not line_str or line_str.startswith(":")

    def _parse_sse_data_line(
        self,
        line_str: str,
        chunk_parser: Callable[[Dict[str, Any]], Optional[LLMStreamChunk]],
        error_log_event: str,
    ) -> Optional[LLMStreamChunk]:
        """
        Parse SSE data line and extract chunk.

        Args:
            line_str: SSE line string
            chunk_parser: Callback to parse provider-specific chunk format
            error_log_event: Log event name for errors

        Returns:
            Parsed LLMStreamChunk or None if line should be skipped
        """
        if not line_str.startswith("data: "):
            return None

        data_str = line_str[6:]

        if data_str == "[DONE]":
            return LLMStreamChunk(
                content="",
                is_final=True,
                finish_reason="stop",
            )

        try:
            data = json.loads(data_str)
            return chunk_parser(data)
        except json.JSONDecodeError as e:
            from ..utils.logx import log_event

            log_event(
                f"{error_log_event}_parse_error",
                {"error": str(e), "data": data_str[:100]},
                level=logging.WARNING,
            )
            return None

    async def _stream_sse_response(
        self,
        url: str,
        payload: Dict[str, Any],
        model: str,
        provider_name: str,
        chunk_parser: Callable[[Dict[str, Any]], Optional[LLMStreamChunk]],
        error_log_event: str,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generic SSE (Server-Sent Events) streaming handler for OpenAI-compatible APIs.

        Handles HTTP request, error responses, SSE parsing, and JSON decoding.
        Provider-specific chunk parsing is delegated to the chunk_parser callback.

        Args:
            url: API endpoint URL
            payload: Request payload (already includes stream=True)
            model: Model identifier for error logging
            provider_name: Provider name for error messages
            chunk_parser: Callback to parse provider-specific chunk format
            error_log_event: Log event name for errors

        Yields:
            LLMStreamChunk objects parsed by chunk_parser

        Raises:
            RuntimeError: If HTTP request fails or streaming errors occur
        """
        session = self._ensure_session()

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self._handle_http_error(
                        response.status,
                        error_text,
                        model,
                        provider_name,
                        error_log_event,
                    )

                async for line in response.content:
                    if not line:
                        continue

                    line_str = line.decode("utf-8").strip()

                    if self._should_skip_sse_line(line_str):
                        continue

                    chunk = self._parse_sse_data_line(
                        line_str,
                        chunk_parser,
                        error_log_event,
                    )

                    if chunk is not None:
                        yield chunk
                        if chunk.is_final:
                            break

        except aiohttp.ClientError as e:
            from ..utils.logx import log_event

            log_event(
                f"{error_log_event}_connection_error",
                {"error": str(e), "url": url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to stream from {provider_name}: {e}") from e

    async def _stream_openai_format(
        self,
        url: str,
        payload: Dict[str, Any],
        model: str,
        provider_name: str,
        error_log_event: str,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Convenience method for OpenAI-format SSE streaming.

        Used by OpenAI, Groq, and Mistral providers (identical format).

        Args:
            url: API endpoint URL
            payload: Request payload (already includes stream=True)
            model: Model identifier for error logging
            provider_name: Provider name for error messages
            error_log_event: Log event name for errors

        Yields:
            LLMStreamChunk objects with content and metadata

        Raises:
            RuntimeError: If HTTP request fails or streaming errors occur
        """

        def parse_openai_chunk(data: Dict[str, Any]) -> Optional[LLMStreamChunk]:
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                delta = choice.get("delta", {})
                content = delta.get("content", "")
                finish_reason = choice.get("finish_reason")

                if content or finish_reason:
                    return LLMStreamChunk(
                        content=content,
                        is_final=finish_reason is not None,
                        finish_reason=finish_reason,
                    )
            return None

        async for chunk in self._stream_sse_response(
            url=url,
            payload=payload,
            model=model,
            provider_name=provider_name,
            chunk_parser=parse_openai_chunk,
            error_log_event=error_log_event,
        ):
            yield chunk

    async def _stream_anthropic_format(
        self,
        url: str,
        payload: Dict[str, Any],
        model: str,
        error_log_event: str,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Convenience method for Anthropic-format SSE streaming.

        Anthropic uses event-based SSE with content_block_delta events.

        Args:
            url: API endpoint URL
            payload: Request payload (already includes stream=True)
            model: Model identifier for error logging
            error_log_event: Log event name for errors

        Yields:
            LLMStreamChunk objects with content and metadata

        Raises:
            RuntimeError: If HTTP request fails or streaming errors occur
        """

        def parse_anthropic_chunk(data: Dict[str, Any]) -> Optional[LLMStreamChunk]:
            event_type = data.get("type")

            if event_type == "content_block_delta":
                delta = data.get("delta", {})
                if delta.get("type") == "text_delta":
                    content = delta.get("text", "")
                    if content:
                        return LLMStreamChunk(content=content, is_final=False)

            elif event_type == "message_delta":
                delta = data.get("delta", {})
                finish_reason = delta.get("stop_reason")
                usage = data.get("usage", {})
                tokens_used = usage.get("output_tokens")

                return LLMStreamChunk(
                    content="",
                    is_final=True,
                    finish_reason=finish_reason,
                    tokens_used=tokens_used,
                )

            return None

        async for chunk in self._stream_sse_response(
            url=url,
            payload=payload,
            model=model,
            provider_name="Anthropic",
            chunk_parser=parse_anthropic_chunk,
            error_log_event=error_log_event,
        ):
            yield chunk

    def _check_array_error(
        self,
        buffer: str,
        model: str,
        provider_name: str,
        error_handler: Optional[Callable[[int, str, str], None]],
    ) -> None:
        """
        Check for errors in array-wrapped response.

        Args:
            buffer: Response buffer
            model: Model identifier
            provider_name: Provider name
            error_handler: Optional error handler callback

        Raises:
            RuntimeError: If error found and no error_handler provided
        """
        if not buffer.startswith("[") or buffer.count("]") == 0:
            return

        try:
            end_idx = buffer.index("]") + 1
            array_str = buffer[:end_idx]
            data_array = json.loads(array_str)

            if (
                not data_array
                or not isinstance(data_array, list)
                or len(data_array) == 0
            ):
                return

            first_item = data_array[0]
            if "error" not in first_item:
                return

            error_text = json.dumps(first_item)
            status_code = first_item.get("error", {}).get("code", 500)

            if error_handler:
                error_handler(status_code, error_text, model)
            else:
                raise RuntimeError(f"{provider_name} error: {error_text}")

        except json.JSONDecodeError:
            pass

    def _find_json_object_bounds(self, buffer: str, start_idx: int) -> int:
        """
        Find the end index of a JSON object in buffer.

        Args:
            buffer: String buffer containing JSON
            start_idx: Starting index of the JSON object

        Returns:
            End index of JSON object, or -1 if incomplete
        """
        brace_count = 0
        for i in range(start_idx, len(buffer)):
            if buffer[i] == "{":
                brace_count += 1
            elif buffer[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    return i + 1
        return -1

    def _handle_json_error(
        self,
        data: Dict[str, Any],
        model: str,
        provider_name: str,
        error_handler: Optional[Callable[[int, str, str], None]],
    ) -> None:
        """
        Handle error in parsed JSON data.

        Args:
            data: Parsed JSON data
            model: Model identifier
            provider_name: Provider name
            error_handler: Optional error handler callback

        Raises:
            RuntimeError: If error found and no error_handler provided
        """
        if "error" not in data:
            return

        error_text = json.dumps(data)
        status_code = data.get("error", {}).get("code", 500)

        if error_handler:
            error_handler(status_code, error_text, model)
        else:
            raise RuntimeError(f"{provider_name} error: {error_text}")

    def _parse_json_from_buffer(
        self,
        json_str: str,
        error_log_event: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Parse JSON string with error logging.

        Args:
            json_str: JSON string to parse
            error_log_event: Log event name for errors

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        try:
            result = json.loads(json_str)
            if isinstance(result, dict):
                return result
            return None
        except json.JSONDecodeError as e:
            from ..utils.logx import log_event

            log_event(
                f"{error_log_event}_parse_error",
                {"error": str(e), "json": json_str[:100]},
                level=logging.WARNING,
            )
            return None

    def _extract_json_objects_from_buffer(
        self,
        buffer: str,
        model: str,
        provider_name: str,
        chunk_parser: Callable[[Dict[str, Any]], Optional[LLMStreamChunk]],
        error_log_event: str,
        error_handler: Optional[Callable[[int, str, str], None]],
    ) -> tuple[str, list[LLMStreamChunk]]:
        """
        Extract all complete JSON objects from buffer.

        Args:
            buffer: String buffer containing JSON objects
            model: Model identifier
            provider_name: Provider name
            chunk_parser: Callback to parse provider-specific chunk format
            error_log_event: Log event name for errors
            error_handler: Optional error handler callback

        Returns:
            Tuple of (remaining_buffer, list_of_chunks)
        """
        chunks = []

        while True:
            start_idx = buffer.find("{")
            if start_idx == -1:
                break

            end_idx = self._find_json_object_bounds(buffer, start_idx)
            if end_idx == -1:
                break

            json_str = buffer[start_idx:end_idx]
            buffer = buffer[end_idx:].lstrip(",]\n\r\t ")

            data = self._parse_json_from_buffer(json_str, error_log_event)
            if data is None:
                continue

            self._handle_json_error(data, model, provider_name, error_handler)

            chunk_obj = chunk_parser(data)
            if chunk_obj is not None:
                chunks.append(chunk_obj)

        return buffer, chunks

    async def _stream_json_objects(
        self,
        url: str,
        payload: Dict[str, Any],
        model: str,
        provider_name: str,
        chunk_parser: Callable[[Dict[str, Any]], Optional[LLMStreamChunk]],
        error_log_event: str,
        error_handler: Optional[Callable[[int, str, str], None]] = None,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Generic streaming handler for newline-delimited or buffered JSON objects.

        Used by Google (buffered JSON) and potentially other providers.
        Handles HTTP request, error responses, and JSON object extraction from stream.

        Args:
            url: API endpoint URL
            payload: Request payload
            model: Model identifier for error logging
            provider_name: Provider name for error messages
            chunk_parser: Callback to parse provider-specific chunk format
            error_log_event: Log event name for errors
            error_handler: Optional callback to handle errors (status, response, model)

        Yields:
            LLMStreamChunk objects parsed by chunk_parser

        Raises:
            RuntimeError: If HTTP request fails or streaming errors occur
        """
        session = self._ensure_session()

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    self._handle_http_error(
                        response.status,
                        error_text,
                        model,
                        provider_name,
                        error_log_event,
                    )

                buffer = ""
                first_chunk = True

                async for chunk in response.content:
                    if not chunk:
                        continue

                    buffer += chunk.decode("utf-8")

                    if first_chunk:
                        self._check_array_error(
                            buffer,
                            model,
                            provider_name,
                            error_handler,
                        )
                        first_chunk = False

                    buffer, chunks = self._extract_json_objects_from_buffer(
                        buffer,
                        model,
                        provider_name,
                        chunk_parser,
                        error_log_event,
                        error_handler,
                    )

                    for chunk_obj in chunks:
                        yield chunk_obj

        except aiohttp.ClientError as e:
            from ..utils.logx import log_event

            log_event(
                f"{error_log_event}_connection_error",
                {"error": str(e), "url": url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to stream from {provider_name}: {e}") from e


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
        import asyncio

        await asyncio.sleep(0)

    async def cleanup(self) -> None:
        """
        Clean up provider resources.

        Called when provider is being removed or application is shutting down.
        Should release all resources (close sessions, connections, etc.).

        Subclasses should override this to clean up their specific resources.
        Must be idempotent (safe to call multiple times).
        """
        self._initialized = False
        import asyncio

        await asyncio.sleep(0)

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
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:  # help type-checkers see this as a generator
            yield cast(LLMStreamChunk, None)
        raise NotImplementedError

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
