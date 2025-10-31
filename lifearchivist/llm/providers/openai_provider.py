"""
OpenAI provider implementation.

Provides access to GPT models via OpenAI API with cost tracking.
"""

import json
import logging
from typing import AsyncGenerator, Dict, List

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
from ..provider_config import OpenAIConfig
from .openai_metadata import OpenAIMetadata

logger = logging.getLogger(__name__)

# Pricing per 1M tokens (as of 2024)
# Source: https://openai.com/api/pricing/
OPENAI_PRICING = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4": {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-16k": {"input": 3.00, "output": 4.00},
}

# Model capabilities
MODEL_CAPABILITIES = {
    "gpt-4o": {
        "context_window": 128000,
        "max_output": 16384,
        "supports_vision": True,
        "supports_functions": True,
    },
    "gpt-4o-mini": {
        "context_window": 128000,
        "max_output": 16384,
        "supports_vision": True,
        "supports_functions": True,
    },
    "gpt-4-turbo": {
        "context_window": 128000,
        "max_output": 4096,
        "supports_vision": True,
        "supports_functions": True,
    },
    "gpt-4": {
        "context_window": 8192,
        "max_output": 4096,
        "supports_vision": False,
        "supports_functions": True,
    },
    "gpt-3.5-turbo": {
        "context_window": 16385,
        "max_output": 4096,
        "supports_vision": False,
        "supports_functions": True,
    },
}


class OpenAIProvider(BaseHTTPProvider, BaseLLMProvider):
    """
    OpenAI provider for GPT models.

    Supports all OpenAI chat models with streaming, function calling,
    and vision capabilities (model-dependent).

    Uses persistent HTTP session with connection pooling for optimal performance.
    """

    config: OpenAIConfig
    metadata: OpenAIMetadata

    def __init__(self, provider_id: str, config: OpenAIConfig):
        """
        Initialize OpenAI provider with typed config.

        Args:
            provider_id: Unique provider identifier
            config: Typed OpenAI configuration
        """
        BaseLLMProvider.__init__(self, provider_id, config)
        BaseHTTPProvider.__init__(self)
        self.metadata = OpenAIMetadata(
            provider_id=provider_id,
            api_key=config.api_key,
            base_url=config.base_url,
        )

    def _get_provider_type(self) -> ProviderType:
        """Return OpenAI provider type."""
        return ProviderType.OPENAI

    async def initialize(self) -> None:
        """
        Initialize HTTP session with connection pooling.

        Creates a persistent aiohttp session with OpenAI-specific headers.
        """
        if self._initialized:
            return

        # Initialize HTTP session with OpenAI-specific settings
        await self._initialize_session(
            timeout_seconds=self.config.timeout_seconds,
            max_connections=100,
            max_connections_per_host=30,
            headers=self._build_headers(),
        )

        await BaseLLMProvider.initialize(self)

        log_event(
            "openai_provider_initialized",
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
            "openai_provider_cleaned_up",
            {"provider_id": self.provider_id},
        )

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """
        Convert LLMMessage objects to OpenAI format.

        Args:
            messages: List of LLMMessage objects

        Returns:
            List of message dicts in OpenAI format
        """
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
            }
            for msg in messages
        ]

    def _build_headers(self) -> Dict[str, str]:
        """
        Build request headers with authentication.

        Returns:
            Headers dictionary
        """
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        if self.config.organization and self.config.organization.strip():
            headers["OpenAI-Organization"] = self.config.organization

        return headers

    def _get_base_url(self) -> str:
        """Get OpenAI API base URL from config."""
        return self.config.base_url

    @track(
        operation="openai_generate",
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
        Generate response using OpenAI.

        Args:
            messages: Conversation messages
            model: OpenAI model name (e.g., 'gpt-4o-mini')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI-specific parameters

        Returns:
            LLMResponse with generated content and cost

        Raises:
            RuntimeError: If OpenAI request fails or provider not initialized
        """
        session = self._ensure_session()
        base_url = self._get_base_url()
        openai_messages = self._convert_messages(messages)

        # Build request payload
        payload = {
            "model": model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
            **kwargs,
        }

        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_event(
                        "openai_request_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )
                    raise RuntimeError(
                        f"OpenAI request failed (HTTP {response.status}): {error_text}"
                    )

                data = await response.json()

                # Extract response
                choice = data["choices"][0]
                content = choice["message"]["content"]
                finish_reason = choice.get("finish_reason", "stop")

                # Extract usage
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                # Calculate cost
                cost = self._calculate_cost(prompt_tokens, completion_tokens, model)

                return LLMResponse(
                    content=content,
                    model=model,
                    provider="openai",
                    tokens_used=total_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                    finish_reason=finish_reason,
                    metadata={
                        "usage": usage,
                        "system_fingerprint": data.get("system_fingerprint"),
                    },
                )

        except aiohttp.ClientError as e:
            log_event(
                "openai_connection_error",
                {"error": str(e), "base_url": base_url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to connect to OpenAI: {e}") from e

    @track(
        operation="openai_generate_stream",
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
        Stream response from OpenAI.

        Args:
            messages: Conversation messages
            model: OpenAI model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional OpenAI-specific parameters

        Yields:
            LLMStreamChunk objects with incremental content

        Raises:
            RuntimeError: If streaming fails or provider not initialized
        """
        session = self._ensure_session()
        base_url = self._get_base_url()
        openai_messages = self._convert_messages(messages)

        payload = {
            "model": model,
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }

        try:
            async with session.post(
                f"{base_url}/chat/completions",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_event(
                        "openai_stream_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )
                    raise RuntimeError(
                        f"OpenAI streaming failed (HTTP {response.status}): {error_text}"
                    )

                # Process SSE stream
                async for line in response.content:
                    if not line:
                        continue

                    line_str = line.decode("utf-8").strip()

                    # Skip empty lines and comments
                    if not line_str or line_str.startswith(":"):
                        continue

                    # Parse SSE format: "data: {...}"
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]

                        # Check for stream end
                        if data_str == "[DONE]":
                            yield LLMStreamChunk(
                                content="",
                                is_final=True,
                                finish_reason="stop",
                            )
                            break

                        try:
                            data = json.loads(data_str)

                            # Extract delta content
                            if "choices" in data and len(data["choices"]) > 0:
                                choice = data["choices"][0]
                                delta = choice.get("delta", {})
                                content = delta.get("content", "")
                                finish_reason = choice.get("finish_reason")

                                if content or finish_reason:
                                    yield LLMStreamChunk(
                                        content=content,
                                        is_final=finish_reason is not None,
                                        finish_reason=finish_reason,
                                    )

                        except json.JSONDecodeError as e:
                            log_event(
                                "openai_stream_parse_error",
                                {"error": str(e), "data": data_str[:100]},
                                level=logging.WARNING,
                            )
                            continue

        except aiohttp.ClientError as e:
            log_event(
                "openai_stream_connection_error",
                {"error": str(e), "base_url": base_url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to stream from OpenAI: {e}") from e

    @track(
        operation="openai_list_models",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_models(self) -> List[ModelInfo]:
        """
        List available OpenAI models.

        Returns:
            List of ModelInfo objects for chat models, or empty list for admin keys
        """
        if self.metadata and self.metadata.is_admin_key:
            log_event(
                "openai_admin_key_no_models",
                {"provider_id": self.provider_id},
            )
            return []

        base_url = self._get_base_url()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{base_url}/models",
                    headers=self._build_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"Failed to list OpenAI models (HTTP {response.status}): {error_text}"
                        )

                    data = await response.json()
                    models = data.get("data", [])

                    # Filter to chat models only
                    chat_models = [
                        model for model in models if "gpt" in model["id"].lower()
                    ]

                    return [
                        self._create_model_info(model["id"]) for model in chat_models
                    ]

        except aiohttp.ClientError as e:
            log_event(
                "openai_list_models_error",
                {"error": str(e), "base_url": base_url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to connect to OpenAI: {e}") from e

    async def validate_credentials(self) -> bool:
        """
        Validate OpenAI API key.

        Returns:
            True if API key is valid, False otherwise
        """
        try:
            session = self._ensure_session()
            base_url = self._get_base_url()

            if self.metadata and self.metadata.is_admin_key:
                endpoint = f"{base_url}/organization"
            else:
                endpoint = f"{base_url}/models"

            async with session.get(
                endpoint,
                headers=self._build_headers(),
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                is_valid = response.status != 401

                log_event(
                    "openai_validation",
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
                "openai_validation_failed",
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
        Estimate cost for OpenAI usage.

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

        Handles versioned models like 'gpt-4-0125-preview' by matching prefixes.

        Args:
            model_id: Full model identifier

        Returns:
            Base model name for pricing lookup
        """
        # Try exact match first
        if model_id in OPENAI_PRICING:
            return model_id

        # Try prefix matching for versioned models
        for base_model in OPENAI_PRICING.keys():
            if model_id.startswith(base_model + "-"):
                return base_model

        # Fallback to gpt-4-turbo pricing
        log_event(
            "unknown_openai_model",
            {"model_id": model_id, "using_fallback": "gpt-4-turbo"},
            level=logging.WARNING,
        )
        return "gpt-4-turbo"

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
        pricing = OPENAI_PRICING[base_model_name]

        # Calculate cost (pricing is per 1M tokens)
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _create_model_info(self, model_id: str) -> ModelInfo:
        """
        Create ModelInfo for an OpenAI model.

        Args:
            model_id: OpenAI model identifier

        Returns:
            ModelInfo object with capabilities and pricing
        """
        # Use same logic as cost calculation
        base_model_name = self._get_base_model_name(model_id)

        capabilities = MODEL_CAPABILITIES.get(
            base_model_name,
            {
                "context_window": 8192,
                "max_output": 4096,
                "supports_vision": False,
                "supports_functions": True,
            },
        )

        pricing = OPENAI_PRICING[base_model_name]

        # Build metadata with provider-specific info
        metadata = {
            "base_model": base_model_name,
            "pricing_per_1m": pricing,
            "base_url": self.config.base_url,
        }

        # Include organization if configured
        if self.config.organization:
            metadata["organization"] = self.config.organization

        return ModelInfo(
            id=model_id,
            name=model_id,
            provider="openai",
            provider_id=self.provider_id,
            context_window=capabilities["context_window"],
            max_output_tokens=capabilities["max_output"],
            supports_streaming=True,
            supports_functions=bool(capabilities["supports_functions"]),
            supports_vision=bool(capabilities["supports_vision"]),
            cost_per_1k_input=pricing["input"] / 1000,  # Convert to per 1K
            cost_per_1k_output=pricing["output"] / 1000,
            metadata=metadata,
        )
