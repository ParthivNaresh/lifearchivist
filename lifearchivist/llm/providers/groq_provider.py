"""
Groq provider implementation.

Provides access to Groq's fast inference API using OpenAI-compatible endpoints.
"""

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
from ..provider_config import GroqConfig

logger = logging.getLogger(__name__)


class GroqProvider(BaseHTTPProvider, BaseLLMProvider):
    """
    Groq provider for fast LLM inference.

    Uses OpenAI-compatible API with Groq's optimized models.
    """

    config: GroqConfig

    def __init__(self, provider_id: str, config: GroqConfig):
        """
        Initialize Groq provider with typed config.

        Args:
            provider_id: Unique provider identifier
            config: Typed Groq configuration
        """
        BaseLLMProvider.__init__(self, provider_id, config)
        BaseHTTPProvider.__init__(self)

    def _get_provider_type(self) -> ProviderType:
        """Return Groq provider type."""
        return ProviderType.GROQ

    async def initialize(self) -> None:
        """
        Initialize HTTP session with Groq-specific settings.
        """
        if self._initialized:
            return

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        self._initialize_session(
            timeout_seconds=self.config.timeout_seconds,
            max_connections=100,
            max_connections_per_host=30,
            headers=headers,
        )

        BaseLLMProvider.initialize(self)

        log_event(
            "groq_provider_initialized",
            {
                "provider_id": self.provider_id,
                "base_url": self.config.base_url,
            },
        )

    async def cleanup(self) -> None:
        """
        Clean up HTTP session and release connections.
        """
        await self._cleanup_session()
        await BaseLLMProvider.cleanup(self)

        log_event(
            "groq_provider_cleaned_up",
            {"provider_id": self.provider_id},
        )

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict]:
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
            }
            for msg in messages
        ]

    @track(
        operation="groq_generate",
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
        Generate response using Groq.

        Args:
            messages: Conversation messages
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated content
        """
        session = self._ensure_session()

        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        if "seed" in kwargs:
            payload["seed"] = kwargs["seed"]

        url = f"{self.config.base_url}/chat/completions"

        try:
            async with session.post(url, json=payload) as response:
                response_text = await response.text()

                if response.status != 200:
                    log_event(
                        "groq_request_failed",
                        {
                            "status": response.status,
                            "error": response_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )

                    raise RuntimeError(
                        f"Groq API error (HTTP {response.status}): {response_text[:500]}"
                    )

                data = await response.json()

                choice = data["choices"][0]
                message = choice["message"]

                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

                cost = self.estimate_cost(prompt_tokens, completion_tokens, model)

                return LLMResponse(
                    content=message["content"],
                    model=model,
                    provider="groq",
                    tokens_used=total_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                    finish_reason=choice.get("finish_reason", "stop"),
                    metadata={
                        "groq_id": data.get("id"),
                        "system_fingerprint": data.get("system_fingerprint"),
                        "x_groq": data.get("x_groq"),
                        "queue_time": usage.get("queue_time"),
                        "prompt_time": usage.get("prompt_time"),
                        "completion_time": usage.get("completion_time"),
                        "total_time": usage.get("total_time"),
                    },
                )

        except aiohttp.ClientError as e:
            log_event(
                "groq_connection_error",
                {"error": str(e), "url": url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to connect to Groq: {e}") from e

    @track(
        operation="groq_generate_stream",
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
        Stream response from Groq.

        Args:
            messages: Conversation messages
            model: Model identifier
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Yields:
            LLMStreamChunk objects with incremental content
        """
        payload = {
            "model": model,
            "messages": self._convert_messages(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        if "seed" in kwargs:
            payload["seed"] = kwargs["seed"]

        async for chunk in self._stream_openai_format(
            url=f"{self.config.base_url}/chat/completions",
            payload=payload,
            model=model,
            provider_name="Groq",
            error_log_event="groq_stream_failed",
        ):
            yield chunk

    @track(
        operation="groq_list_models",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_models(self) -> List[ModelInfo]:
        """
        List available Groq models.

        Returns:
            List of ModelInfo objects
        """
        session = self._ensure_session()
        url = f"{self.config.base_url}/models"

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_event(
                        "groq_list_models_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                        },
                        level=logging.ERROR,
                    )
                    raise RuntimeError(
                        f"Failed to list Groq models (HTTP {response.status}): {error_text[:500]}"
                    )

                data = await response.json()
                models = []

                for model_data in data.get("data", []):
                    model_id = model_data["id"]

                    # Skip non-chat models (like whisper)
                    if "whisper" in model_id.lower():
                        continue

                    context_window = model_data.get("context_window", 4096)

                    # Estimate pricing based on model size
                    if "70b" in model_id.lower():
                        cost_per_1k_input = 0.00059
                        cost_per_1k_output = 0.00079
                    elif "8b" in model_id.lower() or "7b" in model_id.lower():
                        cost_per_1k_input = 0.00005
                        cost_per_1k_output = 0.00008
                    else:
                        cost_per_1k_input = 0.00027
                        cost_per_1k_output = 0.00027

                    models.append(
                        ModelInfo(
                            id=model_id,
                            name=model_id,
                            provider="groq",
                            provider_id=self.provider_id,
                            context_window=context_window,
                            max_output_tokens=min(8192, context_window // 2),
                            supports_streaming=True,
                            supports_functions=False,
                            supports_vision=False,
                            cost_per_1k_input=cost_per_1k_input,
                            cost_per_1k_output=cost_per_1k_output,
                            metadata={
                                "owned_by": model_data.get("owned_by"),
                                "active": model_data.get("active", True),
                            },
                        )
                    )

                return models

        except aiohttp.ClientError as e:
            log_event(
                "groq_list_models_error",
                {"error": str(e), "url": url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to list Groq models: {e}") from e

    async def validate_credentials(self) -> bool:
        """
        Validate Groq API key by listing models.

        Returns:
            True if credentials are valid
        """
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception as e:
            log_event(
                "groq_validation_failed",
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
        Estimate cost for Groq usage.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        # Groq pricing per million tokens
        if "70b" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.59
            output_cost = (completion_tokens / 1_000_000) * 0.79
        elif "8b" in model.lower() or "7b" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.05
            output_cost = (completion_tokens / 1_000_000) * 0.08
        else:
            # Default/mixtral pricing
            input_cost = (prompt_tokens / 1_000_000) * 0.27
            output_cost = (completion_tokens / 1_000_000) * 0.27

        return input_cost + output_cost
