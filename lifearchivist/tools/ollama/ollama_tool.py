"""
LLM integration tools using Ollama.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from lifearchivist.config import get_settings
from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.tools.ollama.ollama_utils import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    HEALTH_CHECK_ENDPOINT,
    MODEL_PULL_ENDPOINT,
    create_error_response,
    create_model_pull_request,
    create_success_response,
    extract_models_from_health_response,
    extract_response_text,
    parse_streaming_chunk,
    prepare_chat_request,
    prepare_generate_request,
)
from lifearchivist.utils.logging import log_event, track


class OllamaTool(BaseTool):
    """Tool for interacting with Ollama for LLM inference."""

    def __init__(self):
        super().__init__()
        self.settings = get_settings()

    def _get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="llm.ollama",
            description="Generate text using local Ollama LLM",
            input_schema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Text prompt for the LLM",
                    },
                    "system": {
                        "type": "string",
                        "description": "System message/instructions",
                    },
                    "messages": {
                        "type": "array",
                        "description": "Chat messages for conversation",
                    },
                    "model": {"type": "string", "description": "Ollama model name"},
                    "max_tokens": {
                        "type": "integer",
                        "default": 2048,
                        "description": "Maximum tokens to generate",
                    },
                    "temperature": {
                        "type": "number",
                        "default": 0.7,
                        "description": "Sampling temperature (0.0 to 1.0)",
                    },
                    "stream": {
                        "type": "boolean",
                        "default": False,
                        "description": "Enable streaming response",
                    },
                },
                "required": ["prompt"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "response": {
                        "type": "string",
                        "description": "Generated text response",
                    },
                    "model": {"type": "string", "description": "Model used"},
                    "tokens_generated": {
                        "type": "integer",
                        "description": "Number of tokens generated",
                    },
                    "generation_time_ms": {
                        "type": "integer",
                        "description": "Generation time in milliseconds",
                    },
                },
            },
            async_tool=True,
            idempotent=False,
        )

    @track(
        operation="ollama_text_generation",
        include_args=["model", "max_tokens", "temperature", "stream"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Generate text using Ollama."""
        prompt = kwargs.get("prompt")
        system = kwargs.get("system")
        messages = kwargs.get("messages", [])
        model = kwargs.get("model", self.settings.llm_model)
        max_tokens = kwargs.get("max_tokens", 2048)
        temperature = kwargs.get("temperature", 0.7)
        stream = kwargs.get("stream", False)

        if not prompt and not messages:
            raise ValueError("Either 'prompt' or 'messages' must be provided")

        # Log generation request with context
        input_type = "chat" if messages else "prompt"
        input_length = len(str(messages)) if messages else len(str(prompt))

        log_event(
            "ollama_generation_started",
            {
                "model": model,
                "input_type": input_type,
                "input_length": input_length,
                "prompt_preview": (
                    str(prompt)[:100] + "..."
                    if prompt and len(str(prompt)) > 100
                    else str(prompt) if prompt else None
                ),
                "message_count": len(messages) if messages else 0,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream,
                "has_system": bool(system),
            },
        )

        # Use session-per-request pattern with explicit cleanup configuration
        timeout = aiohttp.ClientTimeout(
            total=DEFAULT_REQUEST_TIMEOUT_SECONDS,
            connect=10,  # Connection timeout
            sock_read=30,  # Socket read timeout
        )

        connector = aiohttp.TCPConnector(
            limit=1,  # Limit connections for this session
            limit_per_host=1,  # Single connection per host
            ttl_dns_cache=300,  # DNS cache TTL
            use_dns_cache=True,
            keepalive_timeout=30,  # Keep-alive timeout
            enable_cleanup_closed=True,  # Enable cleanup of closed connections
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            connector_owner=True,  # Session owns the connector and will close it
        ) as session:
            try:
                # Check if Ollama is available
                await self._check_ollama_health(session)

                # Prepare the request
                if messages:
                    # Use chat format
                    request_data, endpoint = prepare_chat_request(
                        model=model,
                        messages=messages,
                        system=system,
                        prompt=prompt,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=stream,
                    )
                else:
                    # Use simple generate format
                    request_data, endpoint = prepare_generate_request(
                        model=model,
                        prompt=str(prompt),
                        system=system,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        stream=stream,
                    )
                # Make the request
                if stream:
                    response_text = await self._stream_request(
                        session, endpoint, request_data
                    )
                    generation_time = 0  # Cannot accurately measure for streaming
                    tokens_generated = 0  # Cannot measure for streaming
                else:
                    response_data = await self._single_request(
                        session, endpoint, request_data
                    )
                    response_text = extract_response_text(response_data, endpoint)

                    # Calculate generation time and tokens
                    generation_time = (
                        response_data.get("total_duration", 0) // 1_000_000
                    )
                    tokens_generated = response_data.get("eval_count", 0)

                # Log successful generation with metrics
                log_event(
                    "ollama_generation_completed",
                    {
                        "model": model,
                        "response_length": len(response_text),
                        "tokens_generated": tokens_generated,
                        "generation_time_ms": generation_time,
                        "stream": stream,
                        "tokens_per_second": (
                            (tokens_generated * 1000 / generation_time)
                            if generation_time > 0 and tokens_generated > 0
                            else 0
                        ),
                    },
                )

                # Log if response is empty or very short (potential issue)
                if not response_text or len(response_text) < 10:
                    log_event(
                        "ollama_short_response",
                        {
                            "model": model,
                            "response_length": len(response_text),
                            "prompt_length": input_length,
                            "temperature": temperature,
                        },
                        level=logging.WARNING,
                    )

                return create_success_response(
                    response_text, model, tokens_generated, generation_time
                )

            except Exception as e:
                log_event(
                    "ollama_generation_failed",
                    {
                        "model": model,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "endpoint": endpoint if "endpoint" in locals() else "unknown",
                    },
                    level=logging.ERROR,
                )
                return create_error_response(model, e)
            finally:
                # Small delay to allow any remaining cleanup to complete
                # This helps prevent "Unclosed client session" warnings on shutdown
                await asyncio.sleep(0.01)

    @track(
        operation="ollama_health_check",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _check_ollama_health(self, session: aiohttp.ClientSession) -> bool:
        """Check if Ollama service is available."""
        try:
            async with session.get(
                f"{self.settings.ollama_url}{HEALTH_CHECK_ENDPOINT}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    models = extract_models_from_health_response(data)

                    # Log available models for debugging
                    log_event(
                        "ollama_models_available",
                        {
                            "models": models,
                            "requested_model": self.settings.llm_model,
                            "model_available": self.settings.llm_model in models,
                        },
                        level=logging.DEBUG,
                    )

                    if self.settings.llm_model not in models:
                        # Try to pull the model
                        log_event(
                            "ollama_model_missing",
                            {
                                "model": self.settings.llm_model,
                                "available_models": models,
                            },
                            level=logging.WARNING,
                        )
                        await self._pull_model(session, self.settings.llm_model)
                    return True
                else:
                    raise RuntimeError(
                        f"Ollama health check failed: HTTP {response.status}"
                    )
        except Exception as e:
            log_event(
                "ollama_health_check_failed",
                {
                    "url": self.settings.ollama_url,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.settings.ollama_url}: {e}"
            ) from None

    @track(
        operation="model_pull",
        include_args=["model_name"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def _pull_model(
        self, session: aiohttp.ClientSession, model_name: str
    ) -> bool:
        """Attempt to pull a model if it's not available."""
        log_event(
            "ollama_model_pull_started",
            {
                "model": model_name,
            },
        )

        try:
            request_data = create_model_pull_request(model_name)
            async with session.post(
                f"{self.settings.ollama_url}{MODEL_PULL_ENDPOINT}", json=request_data
            ) as response:
                if response.status == 200:
                    log_event(
                        "ollama_model_pull_succeeded",
                        {
                            "model": model_name,
                        },
                    )
                    return True
                else:
                    log_event(
                        "ollama_model_pull_failed",
                        {
                            "model": model_name,
                            "status_code": response.status,
                        },
                        level=logging.WARNING,
                    )
                    return False

        except Exception as e:
            log_event(
                "ollama_model_pull_error",
                {
                    "model": model_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return False

    @track(
        operation="ollama_single_request",
        include_args=["endpoint"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _single_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        request_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Make a single (non-streaming) request to Ollama."""
        async with session.post(
            f"{self.settings.ollama_url}{endpoint}",
            json=request_data,
            # Timeout is configured at session level, no need to override here
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                # Log failed requests for debugging
                log_event(
                    "ollama_request_failed",
                    {
                        "endpoint": endpoint,
                        "status_code": response.status,
                        "error_text": error_text[:200],  # Truncate long errors
                        "model": request_data.get("model"),
                    },
                    level=logging.ERROR,
                )
                raise RuntimeError(
                    f"Ollama request failed: HTTP {response.status} - {error_text}"
                )

            response_data = await response.json()

            # Log slow requests for performance monitoring
            total_duration_ms = response_data.get("total_duration", 0) // 1_000_000
            if total_duration_ms > 5000:  # Log if generation takes more than 5 seconds
                log_event(
                    "ollama_slow_generation",
                    {
                        "endpoint": endpoint,
                        "model": request_data.get("model"),
                        "duration_ms": total_duration_ms,
                        "prompt_eval_count": response_data.get("prompt_eval_count", 0),
                        "eval_count": response_data.get("eval_count", 0),
                    },
                    level=logging.WARNING,
                )

            return dict(response_data)

    @track(
        operation="ollama_stream_request",
        include_args=["endpoint"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _stream_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        request_data: Dict[str, Any],
    ) -> str:
        """Make a streaming request to Ollama and return the full response."""
        accumulated_response = ""
        chunks_processed = 0

        async with session.post(
            f"{self.settings.ollama_url}{endpoint}",
            json=request_data,
            # Timeout is configured at session level, no need to override here
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                log_event(
                    "ollama_stream_request_failed",
                    {
                        "endpoint": endpoint,
                        "status_code": response.status,
                        "error_text": error_text[:200],
                        "model": request_data.get("model"),
                    },
                    level=logging.ERROR,
                )
                raise RuntimeError(
                    f"Ollama streaming request failed: HTTP {response.status} - {error_text}"
                )

            async for line in response.content:
                if line:
                    content, is_done = parse_streaming_chunk(line, endpoint)
                    if content:  # Only count chunks with actual content
                        chunks_processed += 1
                        accumulated_response += content

                    if is_done:
                        break

        # Log streaming metrics
        if chunks_processed > 0:
            log_event(
                "ollama_stream_completed",
                {
                    "endpoint": endpoint,
                    "chunks_processed": chunks_processed,
                    "response_length": len(accumulated_response),
                    "model": request_data.get("model"),
                },
                level=logging.DEBUG,
            )

        return accumulated_response

    @track(
        operation="ollama_chat_convenience",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Convenience method for chat-style interactions."""
        result = await self.execute(
            messages=messages,
            system=system,
            model=model or self.settings.llm_model,
            **kwargs,
        )
        return str(result.get("response", ""))

    @track(
        operation="ollama_generate_convenience",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Convenience method for simple text generation."""
        result = await self.execute(
            prompt=prompt,
            system=system,
            model=model or self.settings.llm_model,
            **kwargs,
        )
        return str(result.get("response", ""))
