"""
Mistral AI provider implementation.

Provides access to Mistral's models using OpenAI-compatible endpoints.
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
from ..provider_config import MistralConfig

logger = logging.getLogger(__name__)


class MistralProvider(BaseHTTPProvider, BaseLLMProvider):
    """
    Mistral AI provider for advanced language models.

    Uses OpenAI-compatible API with Mistral's models.
    """

    config: MistralConfig

    def __init__(self, provider_id: str, config: MistralConfig):
        """
        Initialize Mistral provider with typed config.

        Args:
            provider_id: Unique provider identifier
            config: Typed Mistral configuration
        """
        BaseLLMProvider.__init__(self, provider_id, config)
        BaseHTTPProvider.__init__(self)

    def _get_provider_type(self) -> ProviderType:
        """Return Mistral provider type."""
        return ProviderType.MISTRAL

    async def initialize(self) -> None:
        """
        Initialize HTTP session with Mistral-specific settings.
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
            "mistral_provider_initialized",
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
            "mistral_provider_cleaned_up",
            {"provider_id": self.provider_id},
        )

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """
        Convert LLMMessage objects to OpenAI/Mistral format.

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
        operation="mistral_generate",
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
        Generate response using Mistral.

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
        if "random_seed" in kwargs:
            payload["random_seed"] = kwargs["random_seed"]
        if "safe_prompt" in kwargs:
            payload["safe_prompt"] = kwargs["safe_prompt"]

        url = f"{self.config.base_url}/chat/completions"

        try:
            async with session.post(url, json=payload) as response:
                response_text = await response.text()

                if response.status != 200:
                    log_event(
                        "mistral_request_failed",
                        {
                            "status": response.status,
                            "error": response_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )

                    raise RuntimeError(
                        f"Mistral API error (HTTP {response.status}): {response_text[:500]}"
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
                    provider="mistral",
                    tokens_used=total_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                    finish_reason=choice.get("finish_reason", "stop"),
                    metadata={
                        "mistral_id": data.get("id"),
                        "created": data.get("created"),
                        "object": data.get("object"),
                    },
                )

        except aiohttp.ClientError as e:
            log_event(
                "mistral_connection_error",
                {"error": str(e), "url": url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to connect to Mistral: {e}") from e

    @track(
        operation="mistral_generate_stream",
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
        Stream response from Mistral.

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
        }

        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]
        if "random_seed" in kwargs:
            payload["random_seed"] = kwargs["random_seed"]
        if "safe_prompt" in kwargs:
            payload["safe_prompt"] = kwargs["safe_prompt"]

        async for chunk in self._stream_openai_format(
            url=f"{self.config.base_url}/chat/completions",
            payload=payload,
            model=model,
            provider_name="Mistral",
            error_log_event="mistral_stream_failed",
        ):
            yield chunk

    @track(
        operation="mistral_list_models",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_models(self) -> List[ModelInfo]:
        """
        List available Mistral models.

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
                        "mistral_list_models_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                        },
                        level=logging.ERROR,
                    )
                    raise RuntimeError(
                        f"Failed to list Mistral models (HTTP {response.status}): {error_text[:500]}"
                    )

                data = await response.json()
                models = []

                # Handle both array and object response formats
                model_list = data if isinstance(data, list) else data.get("data", [])

                for model_data in model_list:
                    model_id = model_data["id"]

                    # Get capabilities
                    capabilities = model_data.get("capabilities", {})
                    supports_functions = capabilities.get("function_calling", False)
                    supports_vision = capabilities.get("vision", False)

                    # Get context window
                    context_window = model_data.get("max_context_length", 32768)

                    # Estimate pricing based on model name
                    if "large" in model_id.lower():
                        cost_per_1k_input = 0.002
                        cost_per_1k_output = 0.006
                    elif "medium" in model_id.lower():
                        cost_per_1k_input = 0.00065
                        cost_per_1k_output = 0.002
                    elif "small" in model_id.lower():
                        cost_per_1k_input = 0.00015
                        cost_per_1k_output = 0.00045
                    elif "tiny" in model_id.lower() or "7b" in model_id.lower():
                        cost_per_1k_input = 0.00014
                        cost_per_1k_output = 0.00014
                    else:
                        # Default/mixtral pricing
                        cost_per_1k_input = 0.00045
                        cost_per_1k_output = 0.00045

                    models.append(
                        ModelInfo(
                            id=model_id,
                            name=model_data.get("name") or model_id,
                            provider="mistral",
                            provider_id=self.provider_id,
                            context_window=context_window,
                            max_output_tokens=min(8192, context_window // 2),
                            supports_streaming=True,
                            supports_functions=supports_functions,
                            supports_vision=supports_vision,
                            cost_per_1k_input=cost_per_1k_input,
                            cost_per_1k_output=cost_per_1k_output,
                            metadata={
                                "owned_by": model_data.get("owned_by"),
                                "created": model_data.get("created"),
                                "type": model_data.get("TYPE", model_data.get("type")),
                                "archived": model_data.get("archived", False),
                                "deprecation": model_data.get("deprecation"),
                                "capabilities": capabilities,
                            },
                        )
                    )

                return models

        except aiohttp.ClientError as e:
            log_event(
                "mistral_list_models_error",
                {"error": str(e), "url": url},
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to list Mistral models: {e}") from e

    async def validate_credentials(self) -> bool:
        """
        Validate Mistral API key by listing models.

        Returns:
            True if credentials are valid
        """
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception as e:
            log_event(
                "mistral_validation_failed",
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
        Estimate cost for Mistral usage.

        Args:
            prompt_tokens: Number of input tokens
            completion_tokens: Number of output tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        # Mistral pricing per million tokens
        if "large" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 2.0
            output_cost = (completion_tokens / 1_000_000) * 6.0
        elif "medium" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.65
            output_cost = (completion_tokens / 1_000_000) * 2.0
        elif "small" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.15
            output_cost = (completion_tokens / 1_000_000) * 0.45
        elif "tiny" in model.lower() or "7b" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.14
            output_cost = (completion_tokens / 1_000_000) * 0.14
        else:
            # Default/mixtral pricing
            input_cost = (prompt_tokens / 1_000_000) * 0.45
            output_cost = (completion_tokens / 1_000_000) * 0.45

        return input_cost + output_cost
