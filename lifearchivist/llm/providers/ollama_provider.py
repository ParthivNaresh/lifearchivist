"""
Ollama provider implementation.

Provides local LLM inference through Ollama with zero cost.
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
from ..provider_config import OllamaConfig

logger = logging.getLogger(__name__)


class OllamaProvider(BaseHTTPProvider, BaseLLMProvider):
    """
    Ollama provider for local LLM inference.

    Supports all Ollama models with streaming and non-streaming generation.
    Cost is always $0 since models run locally.

    Uses persistent HTTP session with connection pooling for optimal performance.
    """

    config: OllamaConfig  # Type hint for IDE/type checker

    def __init__(self, provider_id: str, config: OllamaConfig):
        """
        Initialize Ollama provider with typed config.

        Args:
            provider_id: Unique provider identifier
            config: Typed Ollama configuration
        """
        BaseLLMProvider.__init__(self, provider_id, config)
        BaseHTTPProvider.__init__(self)

    def _get_provider_type(self) -> ProviderType:
        """Return Ollama provider type."""
        return ProviderType.OLLAMA

    async def initialize(self) -> None:
        """
        Initialize HTTP session with connection pooling.

        Creates a persistent aiohttp session with optimized settings.
        """
        if self._initialized:
            return

        # Initialize HTTP session with Ollama-specific settings
        self._initialize_session(
            timeout_seconds=self.config.timeout_seconds,
            max_connections=100,
            max_connections_per_host=30,
        )

        BaseLLMProvider.initialize(self)

        log_event(
            "ollama_provider_initialized",
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
            "ollama_provider_cleaned_up",
            {"provider_id": self.provider_id},
        )

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict[str, str]]:
        """
        Convert LLMMessage objects to Ollama format.

        Args:
            messages: List of LLMMessage objects

        Returns:
            List of message dicts in Ollama format
        """
        return [
            {
                "role": msg.role,
                "content": msg.content,
                **({"name": msg.name} if msg.name else {}),
            }
            for msg in messages
        ]

    @track(
        operation="ollama_generate",
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
        Generate response using Ollama.

        Args:
            messages: Conversation messages
            model: Ollama model name (e.g., 'llama3.2:1b')
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Ollama-specific options

        Returns:
            LLMResponse with generated content

        Raises:
            RuntimeError: If Ollama request fails or provider not initialized
        """
        session = self._ensure_session()

        ollama_messages = self._convert_messages(messages)

        # Build request payload
        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs.get("options", {}),
            },
        }

        # Add keep_alive if configured
        if self.config.keep_alive:
            payload["keep_alive"] = self.config.keep_alive

        try:
            async with session.post(
                f"{self.config.base_url}/api/chat",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_event(
                        "ollama_request_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )
                    raise RuntimeError(
                        f"Ollama request failed (HTTP {response.status}): {error_text}"
                    )

                data = await response.json()

                # Extract response content
                content = data.get("message", {}).get("content", "")

                # Extract token counts
                prompt_tokens = data.get("prompt_eval_count", 0)
                completion_tokens = data.get("eval_count", 0)
                total_tokens = prompt_tokens + completion_tokens

                # Calculate generation time
                total_duration_ns = data.get("total_duration", 0)
                generation_time_ms = total_duration_ns // 1_000_000

                return LLMResponse(
                    content=content,
                    model=model,
                    provider="ollama",
                    tokens_used=total_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=0.0,  # Ollama is free
                    finish_reason=data.get("done_reason", "stop"),
                    metadata={
                        "total_duration_ms": generation_time_ms,
                        "load_duration_ms": data.get("load_duration", 0) // 1_000_000,
                        "prompt_eval_duration_ms": data.get("prompt_eval_duration", 0)
                        // 1_000_000,
                        "eval_duration_ms": data.get("eval_duration", 0) // 1_000_000,
                    },
                )

        except aiohttp.ClientError as e:
            log_event(
                "ollama_connection_error",
                {"error": str(e), "base_url": self.config.base_url},
                level=logging.ERROR,
            )
            raise RuntimeError(
                f"Failed to connect to Ollama at {self.config.base_url}: {e}"
            ) from e

    @track(
        operation="ollama_generate_stream",
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
        Stream response from Ollama.

        Args:
            messages: Conversation messages
            model: Ollama model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Ollama-specific options

        Yields:
            LLMStreamChunk objects with incremental content

        Raises:
            RuntimeError: If streaming fails or provider not initialized
        """
        session = self._ensure_session()

        ollama_messages = self._convert_messages(messages)

        payload = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                **kwargs.get("options", {}),
            },
        }

        if self.config.keep_alive:
            payload["keep_alive"] = self.config.keep_alive

        try:
            async with session.post(
                f"{self.config.base_url}/api/chat",
                json=payload,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_event(
                        "ollama_stream_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )
                    raise RuntimeError(
                        f"Ollama streaming failed (HTTP {response.status}): {error_text}"
                    )

                # Process streaming response
                async for line in response.content:
                    if not line:
                        continue

                    try:
                        data = json.loads(line)

                        # Extract content from message
                        message = data.get("message", {})
                        content = message.get("content", "")

                        # Check if this is the final chunk
                        is_done = data.get("done", False)

                        if content or is_done:
                            chunk = LLMStreamChunk(
                                content=content,
                                is_final=is_done,
                            )

                            # Add token counts in final chunk
                            if is_done:
                                prompt_tokens = data.get("prompt_eval_count", 0)
                                completion_tokens = data.get("eval_count", 0)
                                chunk.tokens_used = prompt_tokens + completion_tokens
                                chunk.finish_reason = data.get("done_reason", "stop")
                                chunk.metadata = {
                                    "prompt_tokens": prompt_tokens,
                                    "completion_tokens": completion_tokens,
                                }

                            yield chunk

                    except json.JSONDecodeError as e:
                        log_event(
                            "ollama_stream_parse_error",
                            {"error": str(e), "line": str(line)[:100]},
                            level=logging.WARNING,
                        )
                        continue

        except aiohttp.ClientError as e:
            log_event(
                "ollama_stream_connection_error",
                {"error": str(e), "base_url": self.config.base_url},
                level=logging.ERROR,
            )
            raise RuntimeError(
                f"Failed to stream from Ollama at {self.config.base_url}: {e}"
            ) from e

    @track(
        operation="ollama_list_models",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_models(self) -> List[ModelInfo]:
        """
        List available Ollama models.

        Returns:
            List of ModelInfo objects for installed models

        Raises:
            RuntimeError: If model listing fails
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.config.base_url}/api/tags") as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"Failed to list Ollama models (HTTP {response.status}): {error_text}"
                        )

                    data = await response.json()
                    models = data.get("models", [])

                    return [
                        ModelInfo(
                            id=model["name"],
                            name=model["name"],
                            provider="ollama",
                            provider_id=self.provider_id,  # NEW: Include provider instance ID
                            context_window=self._estimate_context_window(model["name"]),
                            max_output_tokens=4096,  # Conservative default
                            supports_streaming=True,
                            supports_functions=False,
                            supports_vision=self._supports_vision(model["name"]),
                            cost_per_1k_input=0.0,
                            cost_per_1k_output=0.0,
                            metadata={
                                "size": model.get("size", 0),
                                "modified_at": model.get("modified_at"),
                                "digest": model.get("digest"),
                                "details": model.get("details", {}),
                                "base_url": self.config.base_url,
                            },
                        )
                        for model in models
                    ]

        except aiohttp.ClientError as e:
            log_event(
                "ollama_list_models_error",
                {"error": str(e), "base_url": self.config.base_url},
                level=logging.ERROR,
            )
            raise RuntimeError(
                f"Failed to connect to Ollama at {self.config.base_url}: {e}"
            ) from e

    async def validate_credentials(self) -> bool:
        """
        Validate Ollama is accessible.

        Returns:
            True if Ollama is reachable, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.base_url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    is_valid = response.status == 200

                    log_event(
                        "ollama_validation",
                        {
                            "base_url": self.config.base_url,
                            "valid": is_valid,
                            "status": response.status,
                        },
                    )

                    return is_valid

        except Exception as e:
            log_event(
                "ollama_validation_failed",
                {"error": str(e), "base_url": self.config.base_url},
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
        Estimate cost for Ollama (always $0).

        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            model: Model identifier

        Returns:
            0.0 (Ollama is free)
        """
        return 0.0

    def _estimate_context_window(self, model_name: str) -> int:
        """
        Estimate context window size based on model name.

        Args:
            model_name: Ollama model name

        Returns:
            Estimated context window size
        """
        # Common context windows for popular models
        if "llama3" in model_name.lower():
            return 8192
        elif "mistral" in model_name.lower():
            return 8192
        elif "codellama" in model_name.lower():
            return 16384
        elif "phi" in model_name.lower():
            return 2048
        else:
            return 4096  # Conservative default

    def _supports_vision(self, model_name: str) -> bool:
        """
        Check if model supports vision/image inputs.

        Args:
            model_name: Ollama model name

        Returns:
            True if model supports vision
        """
        vision_models = ["llava", "bakllava", "vision"]
        return any(vm in model_name.lower() for vm in vision_models)
