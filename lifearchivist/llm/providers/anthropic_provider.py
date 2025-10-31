"""
Anthropic provider implementation.

Provides access to Claude models via Anthropic API with cost tracking.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import aiohttp

from ...utils.logging import log_event, track
from ..base_provider import (
    BaseHTTPProvider,
    BaseLLMProvider,
    LLMMessage,
    LLMResponse,
    LLMStreamChunk,
    ModelInfo,
    ProviderType,
)
from ..provider_config import AnthropicConfig
from .anthropic_metadata import AnthropicMetadata

logger = logging.getLogger(__name__)

ANTHROPIC_PRICING = {
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}

DEFAULT_CAPABILITIES = {
    "context_window": 200000,
    "max_output": 8192,
    "supports_vision": True,
}


class AnthropicProvider(BaseHTTPProvider, BaseLLMProvider):
    """
    Anthropic provider for Claude models.

    Supports all Claude 3 models with streaming and vision capabilities.

    Uses persistent HTTP session with connection pooling for optimal performance.
    """

    config: AnthropicConfig
    metadata: AnthropicMetadata

    def __init__(self, provider_id: str, config: AnthropicConfig):
        """
        Initialize Anthropic provider with typed config.

        Args:
            provider_id: Unique provider identifier
            config: Typed Anthropic configuration
        """
        BaseLLMProvider.__init__(self, provider_id, config)
        BaseHTTPProvider.__init__(self)
        self.metadata = AnthropicMetadata(
            provider_id=provider_id,
            api_key=config.api_key,
            base_url=config.base_url,
        )

    def _get_provider_type(self) -> ProviderType:
        """Return Anthropic provider type."""
        return ProviderType.ANTHROPIC

    async def initialize(self) -> None:
        """
        Initialize HTTP session with connection pooling.

        Creates a persistent aiohttp session with Anthropic-specific headers.
        """
        if self._initialized:
            return

        # Initialize HTTP session with Anthropic-specific settings
        await self._initialize_session(
            timeout_seconds=self.config.timeout_seconds,
            max_connections=100,
            max_connections_per_host=30,
            headers=self._build_headers(),
        )

        await BaseLLMProvider.initialize(self)

        log_event(
            "anthropic_provider_initialized",
            {
                "provider_id": self.provider_id,
                "base_url": self.config.base_url,
                "timeout": self.config.timeout_seconds,
            },
        )

    async def cleanup(self) -> None:
        """
        Clean up HTTP session and release connections.
        """
        await self._cleanup_session()
        await BaseLLMProvider.cleanup(self)

        log_event(
            "anthropic_provider_cleaned_up",
            {"provider_id": self.provider_id},
        )

    def _convert_messages(
        self, messages: List[LLMMessage]
    ) -> tuple[Optional[str], List[Dict[str, str]]]:
        """
        Convert LLMMessage objects to Anthropic format.

        Anthropic requires system message to be separate from conversation messages.

        Args:
            messages: List of LLMMessage objects

        Returns:
            Tuple of (system_prompt, conversation_messages)
        """
        system_prompt = None
        conversation_messages = []

        for msg in messages:
            if msg.role == "system":
                # Anthropic uses separate system parameter
                system_prompt = msg.content
            else:
                conversation_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                    }
                )

        return system_prompt, conversation_messages

    def _build_headers(self) -> Dict[str, str]:
        """
        Build request headers with authentication.

        Returns:
            Headers dictionary
        """
        return {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def _get_base_url(self) -> str:
        """Get Anthropic API base URL from config."""
        return self.config.base_url

    @track(
        operation="anthropic_generate",
        include_args=["model"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def generate(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate response using Anthropic.

        Args:
            messages: Conversation messages
            model: Anthropic model name (e.g., 'claude-3-5-sonnet-20241022')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic-specific parameters

        Returns:
            LLMResponse with generated content and cost

        Raises:
            RuntimeError: If Anthropic request fails or provider not initialized
        """
        session = self._ensure_session()
        base_url = self._get_base_url()
        system_prompt, anthropic_messages = self._convert_messages(messages)

        # Build request payload
        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
            **kwargs,
        }

        # Add system prompt if present
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with session.post(
                f"{base_url}/messages",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_event(
                        "anthropic_request_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )
                    raise RuntimeError(
                        f"Anthropic request failed (HTTP {response.status}): {error_text}"
                    )

                data = await response.json()

                # Extract response
                content_blocks = data.get("content", [])
                content = ""
                for block in content_blocks:
                    if block.get("type") == "text":
                        content += block.get("text", "")

                finish_reason = data.get("stop_reason", "end_turn")

                # Extract usage
                usage = data.get("usage", {})
                prompt_tokens = usage.get("input_tokens", 0)
                completion_tokens = usage.get("output_tokens", 0)
                total_tokens = prompt_tokens + completion_tokens

                # Calculate cost
                cost = self._calculate_cost(prompt_tokens, completion_tokens, model)

                return LLMResponse(
                    content=content,
                    model=model,
                    provider="anthropic",
                    tokens_used=total_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                    finish_reason=finish_reason,
                    metadata={
                        "usage": usage,
                        "stop_reason": finish_reason,
                    },
                )

        except aiohttp.ClientError as e:
            log_event(
                "anthropic_connection_error",
                {"error": str(e), "base_url": base_url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to connect to Anthropic: {e}") from e

    @track(
        operation="anthropic_generate_stream",
        include_args=["model"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> AsyncGenerator[LLMStreamChunk, None]:
        """
        Stream response from Anthropic.

        Args:
            messages: Conversation messages
            model: Anthropic model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Anthropic-specific parameters

        Yields:
            LLMStreamChunk objects with incremental content

        Raises:
            RuntimeError: If streaming fails or provider not initialized
        """
        session = self._ensure_session()
        base_url = self._get_base_url()
        system_prompt, anthropic_messages = self._convert_messages(messages)

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with session.post(
                f"{base_url}/messages",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_event(
                        "anthropic_stream_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )
                    raise RuntimeError(
                        f"Anthropic streaming failed (HTTP {response.status}): {error_text}"
                    )

                # Process SSE stream
                async for line in response.content:
                    if not line:
                        continue

                    line_str = line.decode("utf-8").strip()

                    # Skip empty lines and comments
                    if not line_str or line_str.startswith(":"):
                        continue

                    # Parse SSE format: "event: <type>" and "data: {...}"
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]

                        try:
                            data = json.loads(data_str)
                            event_type = data.get("type")

                            # Handle content block delta
                            if event_type == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    text = delta.get("text", "")
                                    if text:
                                        yield LLMStreamChunk(
                                            content=text,
                                            is_final=False,
                                        )

                            # Handle message completion
                            elif event_type == "message_delta":
                                delta = data.get("delta", {})
                                stop_reason = delta.get("stop_reason")
                                usage = data.get("usage", {})

                                if stop_reason:
                                    yield LLMStreamChunk(
                                        content="",
                                        is_final=True,
                                        finish_reason=stop_reason,
                                        tokens_used=usage.get("output_tokens", 0),
                                    )

                            # Handle stream end
                            elif event_type == "message_stop":
                                yield LLMStreamChunk(
                                    content="",
                                    is_final=True,
                                    finish_reason="end_turn",
                                )
                                break

                        except json.JSONDecodeError as e:
                            log_event(
                                "anthropic_stream_parse_error",
                                {"error": str(e), "data": data_str[:100]},
                                level=logging.WARNING,
                            )
                            continue

        except aiohttp.ClientError as e:
            log_event(
                "anthropic_stream_connection_error",
                {"error": str(e), "base_url": base_url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to stream from Anthropic: {e}") from e

    @track(
        operation="anthropic_list_models",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_models(self) -> List[ModelInfo]:
        """
        List available Anthropic models.

        Returns:
            List of ModelInfo objects for Claude models, or empty list for admin keys
        """
        if self.metadata and self.metadata.is_admin_key:
            log_event(
                "anthropic_admin_key_no_models",
                {"provider_id": self.provider_id},
            )
            return []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.base_url}/models",
                    headers=self._build_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("data", [])

                        if models:
                            log_event(
                                "anthropic_models_fetched_from_api",
                                {"count": len(models)},
                            )
                            return [
                                self._create_model_info_from_api(model)
                                for model in models
                            ]

                    log_event(
                        "anthropic_models_api_unavailable",
                        {"status": response.status, "using_fallback": True},
                        level=logging.WARNING,
                    )
        except Exception as e:
            log_event(
                "anthropic_models_api_error",
                {"error": str(e), "using_fallback": True},
                level=logging.WARNING,
            )

        return [
            self._create_model_info(model_id) for model_id in ANTHROPIC_PRICING.keys()
        ]

    def _create_model_info_from_api(self, model_data: Dict[str, Any]) -> ModelInfo:
        """
        Create ModelInfo from API response.

        Args:
            model_data: Model data from API

        Returns:
            ModelInfo object
        """
        model_id = model_data.get("id", "")

        context_window = model_data.get(
            "context_window", DEFAULT_CAPABILITIES["context_window"]
        )
        max_output = model_data.get(
            "max_output_tokens", DEFAULT_CAPABILITIES["max_output"]
        )
        supports_vision = model_data.get(
            "supports_vision", DEFAULT_CAPABILITIES["supports_vision"]
        )

        pricing = ANTHROPIC_PRICING.get(model_id, {"input": 3.00, "output": 15.00})

        metadata = {
            "pricing_per_1m": pricing,
            "base_url": self.config.base_url,
            "created": model_data.get("created_at"),
            "display_name": model_data.get("display_name", model_id),
        }

        return ModelInfo(
            id=model_id,
            name=model_data.get("display_name", model_id),
            provider="anthropic",
            provider_id=self.provider_id,
            context_window=context_window,
            max_output_tokens=max_output,
            supports_streaming=True,
            supports_functions=False,
            supports_vision=supports_vision,
            cost_per_1k_input=pricing["input"] / 1000,
            cost_per_1k_output=pricing["output"] / 1000,
            metadata=metadata,
        )

    async def validate_credentials(self) -> bool:
        """
        Validate Anthropic API key.

        Returns:
            True if API key is valid, False if key is invalid
        """
        try:
            session = self._ensure_session()
            base_url = self._get_base_url()

            if self.metadata and self.metadata.is_admin_key:
                endpoint = f"{base_url}/organizations/workspaces"
            else:
                endpoint = f"{base_url}/models"

            async with session.get(
                endpoint,
                headers=self._build_headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                is_valid = response.status != 401

                log_event(
                    "anthropic_validation",
                    {
                        "valid": is_valid,
                        "status": response.status,
                        "is_admin": (
                            self.metadata.is_admin_key if self.metadata else False
                        ),
                    },
                )

                return is_valid

        except Exception as e:
            log_event(
                "anthropic_validation_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            return False

    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str,
    ) -> float:
        """
        Estimate cost for Anthropic usage.

        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        return self._calculate_cost(prompt_tokens, completion_tokens, model)

    def _get_base_model_name(self, model_id: str) -> str:
        """
        Extract base model name from full model ID.

        Args:
            model_id: Full model identifier

        Returns:
            Base model name for pricing lookup
        """
        # Try exact match first
        if model_id in ANTHROPIC_PRICING:
            return model_id

        # Fallback to latest Sonnet pricing
        log_event(
            "unknown_anthropic_model",
            {"model_id": model_id, "using_fallback": "claude-3-5-sonnet-20241022"},
            level=logging.WARNING,
        )
        return "claude-3-5-sonnet-20241022"

    def _calculate_cost(
        self, prompt_tokens: int, completion_tokens: int, model: str
    ) -> float:
        """
        Calculate actual cost based on usage.

        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            model: Model identifier

        Returns:
            Cost in USD
        """
        base_model_name = self._get_base_model_name(model)
        pricing = ANTHROPIC_PRICING[base_model_name]

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _create_model_info(self, model_id: str) -> ModelInfo:
        """
        Create ModelInfo for an Anthropic model (fallback when API unavailable).

        Args:
            model_id: Anthropic model identifier

        Returns:
            ModelInfo object with capabilities and pricing
        """
        pricing = ANTHROPIC_PRICING[model_id]

        metadata = {
            "pricing_per_1m": pricing,
            "base_url": self.config.base_url,
        }

        return ModelInfo(
            id=model_id,
            name=model_id,
            provider="anthropic",
            provider_id=self.provider_id,
            context_window=DEFAULT_CAPABILITIES["context_window"],
            max_output_tokens=DEFAULT_CAPABILITIES["max_output"],
            supports_streaming=True,
            supports_functions=False,
            supports_vision=bool(DEFAULT_CAPABILITIES["supports_vision"]),
            cost_per_1k_input=pricing["input"] / 1000,
            cost_per_1k_output=pricing["output"] / 1000,
            metadata=metadata,
        )
