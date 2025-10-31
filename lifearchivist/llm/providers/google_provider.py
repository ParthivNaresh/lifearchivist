"""
Google AI (Gemini) provider implementation.

Provides access to Google's Gemini models via the Google AI API with simple API key authentication.
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
from ..exceptions import (
    AuthenticationError,
    ConnectionError,
    InvalidRequestError,
    ModelNotFoundError,
    ProviderAPIError,
    RateLimitError,
    ServerError,
    StreamingError,
)
from ..provider_config import GoogleConfig

logger = logging.getLogger(__name__)

DEFAULT_CAPABILITIES = {
    "context_window": 32768,
    "max_output": 8192,
    "supports_vision": True,
    "supports_functions": True,
}

DEFAULT_PRICING = {"input": 1.00, "output": 3.00}


class GoogleProvider(BaseHTTPProvider, BaseLLMProvider):
    """
    Google AI provider for Gemini models.

    Supports all Gemini models with streaming, function calling,
    and vision capabilities (model-dependent).

    Uses simple API key authentication for easy setup.
    """

    config: GoogleConfig

    def __init__(self, provider_id: str, config: GoogleConfig):
        """
        Initialize Google AI provider with typed config.

        Args:
            provider_id: Unique provider identifier
            config: Typed Google configuration
        """
        BaseLLMProvider.__init__(self, provider_id, config)
        BaseHTTPProvider.__init__(self)

    def _get_provider_type(self) -> ProviderType:
        """Return Google provider type."""
        return ProviderType.GOOGLE

    async def initialize(self) -> None:
        """
        Initialize HTTP session with Google AI-specific settings.
        """
        if self._initialized:
            return

        await self._initialize_session(
            timeout_seconds=self.config.timeout_seconds,
            max_connections=100,
            max_connections_per_host=30,
        )

        await BaseLLMProvider.initialize(self)

        log_event(
            "google_provider_initialized",
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
            "google_provider_cleaned_up",
            {"provider_id": self.provider_id},
        )

    def _build_url(self, model: str, action: str = "generateContent") -> str:
        """
        Build Google AI API URL.

        Args:
            model: Model identifier
            action: API action (generateContent, streamGenerateContent, countTokens)

        Returns:
            Complete API URL with key
        """
        return (
            f"{self.config.base_url}/models/{model}:{action}?key={self.config.api_key}"
        )

    def _convert_messages(self, messages: List[LLMMessage]) -> List[Dict]:
        """
        Convert LLMMessage objects to Google AI format.

        Returns:
            List of content objects
        """
        contents = []

        for msg in messages:
            if msg.role == "system":
                contents.append(
                    {"role": "user", "parts": [{"text": f"System: {msg.content}"}]}
                )
                contents.append(
                    {
                        "role": "model",
                        "parts": [
                            {"text": "Understood. I'll follow these instructions."}
                        ],
                    }
                )
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg.content}]})

        return contents

    @track(
        operation="google_generate",
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
        Generate response using Google AI.

        Args:
            messages: Conversation messages
            model: Gemini model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional Google-specific parameters

        Returns:
            LLMResponse with generated content and cost
        """
        session = self._ensure_session()
        contents = self._convert_messages(messages)

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
            },
        }

        if "stop_sequences" in kwargs:
            payload["generationConfig"]["stopSequences"] = kwargs["stop_sequences"]

        url = self._build_url(model, "generateContent")

        try:
            async with session.post(url, json=payload) as response:
                response_text = await response.text()

                if response.status != 200:
                    log_event(
                        "google_request_failed",
                        {
                            "status": response.status,
                            "error": response_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )

                    self._raise_api_error(response.status, response_text, model)

                data = await response.json()

                candidates = data.get("candidates", [])
                if not candidates:
                    raise InvalidRequestError(
                        message="No candidates in Google AI response",
                        provider_id=self.provider_id,
                        status_code=200,
                        response_body=response_text,
                        model=model,
                    )

                candidate = candidates[0]
                content_parts = candidate.get("content", {}).get("parts", [])
                content = "".join(part.get("text", "") for part in content_parts)

                finish_reason = candidate.get("finishReason", "STOP")

                usage_metadata = data.get("usageMetadata", {})
                prompt_tokens = usage_metadata.get("promptTokenCount", 0)
                completion_tokens = usage_metadata.get("candidatesTokenCount", 0)
                total_tokens = usage_metadata.get("totalTokenCount", 0)

                cost = self._calculate_cost(prompt_tokens, completion_tokens, model)

                return LLMResponse(
                    content=content,
                    model=model,
                    provider="google",
                    tokens_used=total_tokens,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    cost_usd=cost,
                    finish_reason=finish_reason,
                    metadata={
                        "usage_metadata": usage_metadata,
                        "safety_ratings": candidate.get("safetyRatings", []),
                    },
                )

        except aiohttp.ClientError as e:
            log_event(
                "google_connection_error",
                {"error": str(e), "url": url},
                level=logging.ERROR,
            )
            raise ConnectionError(
                message=f"Failed to connect to Google AI: {str(e)}",
                provider_id=self.provider_id,
                model=model,
                original_error=e,
            ) from e

    @track(
        operation="google_generate_stream",
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
        Stream response from Google AI.

        Args:
            messages: Conversation messages
            model: Gemini model name
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Yields:
            LLMStreamChunk objects with incremental content
        """
        session = self._ensure_session()
        contents = self._convert_messages(messages)

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": kwargs.get("top_p", 0.95),
                "topK": kwargs.get("top_k", 40),
            },
        }

        url = self._build_url(model, "streamGenerateContent")

        try:
            async with session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    log_event(
                        "google_stream_failed",
                        {
                            "status": response.status,
                            "error": error_text[:500],
                            "model": model,
                        },
                        level=logging.ERROR,
                    )
                    self._raise_api_error(response.status, error_text, model)

                # Process streaming response
                buffer = ""
                first_chunk = True
                async for chunk in response.content:
                    if not chunk:
                        continue

                    buffer += chunk.decode("utf-8")

                    # Check for error array at the beginning
                    if first_chunk and buffer.startswith("["):
                        # Try to parse complete array if we have enough data
                        if buffer.count("]") > 0:
                            try:
                                end_idx = buffer.index("]") + 1
                                array_str = buffer[:end_idx]
                                data_array = json.loads(array_str)
                                if (
                                    data_array
                                    and isinstance(data_array, list)
                                    and len(data_array) > 0
                                ):
                                    first_item = data_array[0]
                                    if "error" in first_item:
                                        error_obj = first_item["error"]
                                        status_code = error_obj.get("code", 500)
                                        self._raise_api_error(
                                            status_code, json.dumps(first_item), model
                                        )
                            except (json.JSONDecodeError, ValueError):
                                pass

                    first_chunk = False

                    # Process complete JSON objects from buffer
                    while True:
                        # Try to find a complete JSON object
                        start_idx = buffer.find("{")
                        if start_idx == -1:
                            break

                        # Count braces to find complete object
                        brace_count = 0
                        end_idx = -1
                        for i in range(start_idx, len(buffer)):
                            if buffer[i] == "{":
                                brace_count += 1
                            elif buffer[i] == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    end_idx = i + 1
                                    break

                        if end_idx == -1:
                            # No complete object yet
                            break

                        # Extract and parse the complete object
                        json_str = buffer[start_idx:end_idx]
                        buffer = buffer[end_idx:]

                        # Skip commas and brackets
                        buffer = buffer.lstrip(",]\n\r\t ")

                        try:
                            data = json.loads(json_str)

                            # Check for error in response
                            if "error" in data:
                                error_obj = data["error"]
                                status_code = error_obj.get("code", 500)
                                self._raise_api_error(
                                    status_code, json.dumps(data), model
                                )

                            candidates = data.get("candidates", [])
                            if candidates:
                                candidate = candidates[0]
                                content_parts = candidate.get("content", {}).get(
                                    "parts", []
                                )
                                content = "".join(
                                    part.get("text", "") for part in content_parts
                                )

                                finish_reason = candidate.get("finishReason")

                                if content or finish_reason:
                                    chunk_obj = LLMStreamChunk(
                                        content=content,
                                        is_final=finish_reason is not None,
                                        finish_reason=finish_reason,
                                    )

                                    if finish_reason:
                                        usage_metadata = data.get("usageMetadata", {})
                                        chunk_obj.tokens_used = usage_metadata.get(
                                            "totalTokenCount", 0
                                        )
                                        chunk_obj.metadata = {
                                            "usage_metadata": usage_metadata
                                        }

                                    yield chunk_obj

                        except json.JSONDecodeError as e:
                            log_event(
                                "google_stream_parse_error",
                                {"error": str(e), "json": json_str[:100]},
                                level=logging.WARNING,
                            )
                            continue

        except aiohttp.ClientError as e:
            log_event(
                "google_stream_connection_error",
                {"error": str(e), "url": url},
                level=logging.ERROR,
            )
            raise StreamingError(
                message=f"Failed to stream from Google AI: {str(e)}",
                provider_id=self.provider_id,
                model=model,
                original_error=e,
            ) from e

    @track(
        operation="google_list_models",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_models(self) -> List[ModelInfo]:
        """
        List available Google AI models dynamically.

        Returns:
            List of ModelInfo objects for Gemini models
        """
        try:
            models = await self._fetch_models_from_api()
            if models:
                log_event(
                    "google_models_fetched_from_api",
                    {"count": len(models)},
                )
                return models
        except Exception as e:
            log_event(
                "google_models_api_error",
                {"error": str(e), "using_fallback": True},
                level=logging.WARNING,
            )

        known_models = [
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-1.0-pro",
        ]

        models = []
        for model_id in known_models:
            models.append(self._create_model_info(model_id))

        return models

    async def _fetch_models_from_api(self) -> List[ModelInfo]:
        """
        Fetch available models from Google AI API.

        Returns:
            List of ModelInfo objects
        """
        session = self._ensure_session()
        models = []

        url = f"{self.config.base_url}/models?key={self.config.api_key}"

        try:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    model_list = data.get("models", [])

                    for model_data in model_list:
                        model_name = model_data.get("name", "").replace("models/", "")

                        if model_name and "gemini" in model_name.lower():
                            supported_methods = model_data.get(
                                "supportedGenerationMethods", []
                            )
                            if "generateContent" in supported_methods:
                                models.append(
                                    self._create_model_info_from_api(model_data)
                                )

                    return models
                else:
                    response_text = await response.text()
                    log_event(
                        "google_models_api_failed",
                        {
                            "status": response.status,
                            "error": response_text[:500],
                        },
                        level=logging.WARNING,
                    )
        except Exception as e:
            log_event(
                "google_models_fetch_exception",
                {"error": str(e)},
                level=logging.WARNING,
            )

        return []

    def _create_model_info_from_api(self, model_data: Dict) -> ModelInfo:
        """
        Create ModelInfo from API response.

        Args:
            model_data: Model data from API

        Returns:
            ModelInfo object
        """
        model_name = model_data.get("name", "").replace("models/", "")
        display_name = model_data.get("displayName", model_name)

        input_token_limit = model_data.get(
            "inputTokenLimit", DEFAULT_CAPABILITIES["context_window"]
        )
        output_token_limit = model_data.get(
            "outputTokenLimit", DEFAULT_CAPABILITIES["max_output"]
        )

        supported_methods = model_data.get("supportedGenerationMethods", [])
        supports_streaming = "streamGenerateContent" in supported_methods
        supports_functions = "generateContent" in supported_methods

        supports_vision = False
        if "vision" in model_name.lower() or "1.5" in model_name:
            supports_vision = True

        if "pro" in model_name.lower():
            if "1.5" in model_name:
                pricing = {"input": 1.25, "output": 5.00}
            else:
                pricing = {"input": 0.50, "output": 1.50}
        elif "flash" in model_name.lower():
            if "8b" in model_name.lower():
                pricing = {"input": 0.0375, "output": 0.15}
            else:
                pricing = {"input": 0.075, "output": 0.30}
        else:
            pricing = DEFAULT_PRICING

        return ModelInfo(
            id=model_name,
            name=display_name,
            provider="google",
            provider_id=self.provider_id,
            context_window=input_token_limit,
            max_output_tokens=output_token_limit,
            supports_streaming=supports_streaming,
            supports_functions=supports_functions,
            supports_vision=supports_vision,
            cost_per_1k_input=pricing["input"] / 1000,
            cost_per_1k_output=pricing["output"] / 1000,
            metadata={
                "base_url": self.config.base_url,
                "version": model_data.get("version"),
                "description": model_data.get("description"),
            },
        )

    def _create_model_info(self, model_id: str) -> ModelInfo:
        """
        Create ModelInfo for a known model (fallback).

        Args:
            model_id: Model identifier

        Returns:
            ModelInfo object with default capabilities
        """
        if "pro" in model_id.lower():
            if "1.5" in model_id:
                pricing = {"input": 1.25, "output": 5.00}
                context_window = 2097152
            else:
                pricing = {"input": 0.50, "output": 1.50}
                context_window = 32768
        elif "flash" in model_id.lower():
            if "8b" in model_id.lower():
                pricing = {"input": 0.0375, "output": 0.15}
            else:
                pricing = {"input": 0.075, "output": 0.30}
            context_window = 1048576
        else:
            pricing = DEFAULT_PRICING
            context_window = DEFAULT_CAPABILITIES["context_window"]

        supports_vision = "1.0" not in model_id

        return ModelInfo(
            id=model_id,
            name=model_id,
            provider="google",
            provider_id=self.provider_id,
            context_window=context_window,
            max_output_tokens=DEFAULT_CAPABILITIES["max_output"],
            supports_streaming=True,
            supports_functions=bool(DEFAULT_CAPABILITIES["supports_functions"]),
            supports_vision=supports_vision,
            cost_per_1k_input=pricing["input"] / 1000,
            cost_per_1k_output=pricing["output"] / 1000,
            metadata={
                "base_url": self.config.base_url,
            },
        )

    async def validate_credentials(self) -> bool:
        """
        Validate Google AI API key using models endpoint.

        Returns:
            True if API key is valid and has permissions
        """
        try:
            session = self._ensure_session()

            url = f"{self.config.base_url}/models?key={self.config.api_key}"

            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                is_valid = response.status == 200

                log_event(
                    "google_validation_result",
                    {
                        "valid": is_valid,
                        "status": response.status,
                    },
                )

                return is_valid

        except Exception as e:
            log_event(
                "google_validation_exception",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
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
        Estimate cost for Google AI usage.

        Args:
            prompt_tokens: Input tokens
            completion_tokens: Output tokens
            model: Model identifier

        Returns:
            Estimated cost in USD
        """
        return self._calculate_cost(prompt_tokens, completion_tokens, model)

    def _calculate_cost(
        self, prompt_tokens: int, completion_tokens: int, model: str
    ) -> float:
        """
        Calculate actual cost based on usage.
        """
        if "pro" in model.lower():
            if "1.5" in model:
                pricing = {"input": 1.25, "output": 5.00}
            else:
                pricing = {"input": 0.50, "output": 1.50}
        elif "flash" in model.lower():
            if "8b" in model.lower():
                pricing = {"input": 0.0375, "output": 0.15}
            else:
                pricing = {"input": 0.075, "output": 0.30}
        else:
            pricing = DEFAULT_PRICING

        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    def _raise_api_error(
        self, status_code: int, response_text: str, model: Optional[str] = None
    ) -> None:
        """
        Raise appropriate exception based on status code.

        Args:
            status_code: HTTP status code
            response_text: Response body text
            model: Model identifier

        Raises:
            Appropriate exception based on status code
        """
        error_message = self._extract_error_message(response_text)

        if status_code == 401 or status_code == 403:
            raise AuthenticationError(
                message=f"Invalid API key or insufficient permissions: {error_message}",
                provider_id=self.provider_id,
                status_code=status_code,
                response_body=response_text,
                model=model,
            )
        elif status_code == 404:
            if model and "model" in error_message.lower():
                raise ModelNotFoundError(
                    message=f"Model '{model}' not found: {error_message}",
                    provider_id=self.provider_id,
                    status_code=status_code,
                    response_body=response_text,
                    model=model,
                )
            else:
                raise InvalidRequestError(
                    message=f"Resource not found: {error_message}",
                    provider_id=self.provider_id,
                    status_code=status_code,
                    response_body=response_text,
                    model=model,
                )
        elif status_code == 429:
            raise RateLimitError(
                message=f"Rate limit exceeded: {error_message}",
                provider_id=self.provider_id,
                status_code=status_code,
                response_body=response_text,
                model=model,
            )
        elif status_code == 400:
            raise InvalidRequestError(
                message=f"Invalid request: {error_message}",
                provider_id=self.provider_id,
                status_code=status_code,
                response_body=response_text,
                model=model,
            )
        elif 500 <= status_code < 600:
            raise ServerError(
                message=f"Google AI server error: {error_message}",
                provider_id=self.provider_id,
                status_code=status_code,
                response_body=response_text,
                model=model,
            )
        else:
            raise ProviderAPIError(
                message=f"Google AI API error: {error_message}",
                provider_id=self.provider_id,
                status_code=status_code,
                response_body=response_text,
                model=model,
            )

    def _extract_error_message(self, response_text: str) -> str:
        """
        Extract error message from Google AI response.

        Args:
            response_text: Raw response text

        Returns:
            Extracted error message or truncated response
        """
        try:
            data = json.loads(response_text)
            if isinstance(data, dict):
                error = data.get("error", {})
                if isinstance(error, dict):
                    message = error.get("message", "")
                    if (
                        "billing" in message.lower()
                        or "credit" in message.lower()
                        or "quota" in message.lower()
                    ):
                        return "Insufficient API credits. Please add billing to your Google AI Studio account."
                    return message or response_text[:500]
                elif isinstance(error, str):
                    return error
                return str(data.get("message", response_text[:500]))
        except json.JSONDecodeError:
            pass

        return response_text[:500]
