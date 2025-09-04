"""
LLM integration tools using Ollama.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from lifearchivist.config import get_settings
from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.tools.ollama.ollama_utils import (
    DEFAULT_REQUEST_TIMEOUT_SECONDS,
    HEALTH_CHECK_ENDPOINT,
    MODEL_PULL_ENDPOINT,
    calculate_generation_metrics,
    calculate_input_metrics,
    create_error_response,
    create_model_pull_request,
    create_success_response,
    extract_models_from_health_response,
    extract_response_text,
    parse_streaming_chunk,
    prepare_chat_request,
    prepare_generate_request,
)
from lifearchivist.utils.logging import log_context, log_event, log_method
from lifearchivist.utils.logging.structured import MetricsCollector

logger = logging.getLogger(__name__)


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

    @log_method(
        operation_name="ollama_text_generation", include_args=True, include_result=True
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

        with log_context(
            operation="ollama_generation",
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=stream,
        ):

            metrics = MetricsCollector("ollama_generation")
            metrics.start()

            # Calculate input metrics
            input_metrics = calculate_input_metrics(prompt, messages, system)
            input_length = input_metrics["input_length"]
            system_length = input_metrics["system_length"]

            metrics.add_metric("model", model)
            metrics.add_metric("input_length", input_length)
            metrics.add_metric("system_length", system_length)
            metrics.add_metric("max_tokens", max_tokens)
            metrics.add_metric("temperature", temperature)
            metrics.add_metric("stream", stream)

            log_event(
                "ollama_generation_started",
                {
                    "model": model,
                    "input_length": input_length,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "use_chat_format": bool(messages),
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
                # Log session creation for debugging
                log_event(
                    "aiohttp_session_created",
                    {
                        "session_id": id(session),
                        "connector_id": id(connector),
                        "timeout_total": timeout.total,
                    },
                )

                try:
                    # Check if Ollama is available
                    await self._check_ollama_health(session)
                    metrics.add_metric("ollama_health_check_passed", True)

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
                        metrics.add_metric(
                            "message_count", len(request_data["messages"])
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
                        metrics.add_metric("prompt_length", len(request_data["prompt"]))

                    log_event(
                        "ollama_request_prepared",
                        {
                            "endpoint": endpoint,
                            "stream": stream,
                            "request_size_chars": len(json.dumps(request_data)),
                        },
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

                        # Add generation metrics
                        gen_metrics = calculate_generation_metrics(
                            response_data, len(response_text), tokens_generated
                        )
                        for key, value in gen_metrics.items():
                            metrics.add_metric(key, value)

                    # Calculate output metrics
                    output_length = len(response_text)
                    metrics.add_metric("output_length", output_length)
                    metrics.add_metric("tokens_generated", tokens_generated)
                    metrics.add_metric("generation_time_ms", generation_time)

                    metrics.set_success(True)
                    metrics.report("ollama_generation_completed")

                    chars_per_second = (
                        gen_metrics.get("chars_per_second", 0) if not stream else 0
                    )

                    log_event(
                        "ollama_generation_successful",
                        {
                            "model": model,
                            "output_length": output_length,
                            "tokens_generated": tokens_generated,
                            "generation_time_ms": generation_time,
                            "chars_per_second": chars_per_second,
                        },
                    )

                    return create_success_response(
                        response_text, model, tokens_generated, generation_time
                    )

                except Exception as e:
                    metrics.set_error(e)
                    metrics.report("ollama_generation_failed")

                    log_event(
                        "ollama_generation_error",
                        {
                            "model": model,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "input_length": input_length,
                        },
                    )

                    return create_error_response(model, e)

                finally:
                    # Explicit session cleanup logging
                    log_event(
                        "aiohttp_session_cleanup_started",
                        {
                            "session_id": id(session),
                            "connector_id": id(connector),
                            "session_closed": session.closed,
                        },
                    )

                    # Log after session is fully closed
                    log_event(
                        "aiohttp_session_closed",
                        {
                            "session_cleanup": "completed",
                            "connector_cleanup": "completed",
                        },
                    )

                    # Small delay to allow any remaining cleanup to complete
                    # This helps prevent "Unclosed client session" warnings on shutdown
                    await asyncio.sleep(0.01)

    @log_method(operation_name="ollama_health_check")
    async def _check_ollama_health(self, session: aiohttp.ClientSession) -> bool:
        """Check if Ollama service is available."""
        log_event(
            "ollama_health_check_started",
            {
                "ollama_url": self.settings.ollama_url,
                "expected_model": self.settings.llm_model,
            },
        )

        try:
            async with session.get(
                f"{self.settings.ollama_url}{HEALTH_CHECK_ENDPOINT}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    models = extract_models_from_health_response(data)

                    log_event(
                        "ollama_models_discovered",
                        {"available_models": models, "model_count": len(models)},
                    )

                    if self.settings.llm_model not in models:
                        log_event(
                            "model_not_available",
                            {
                                "requested_model": self.settings.llm_model,
                                "available_models": models,
                                "attempting_pull": True,
                            },
                        )
                        # Try to pull the model
                        await self._pull_model(session, self.settings.llm_model)

                    log_event(
                        "ollama_health_check_passed",
                        {"model_available": self.settings.llm_model in models},
                    )
                    return True
                else:
                    log_event(
                        "ollama_health_check_failed",
                        {
                            "http_status": response.status,
                            "ollama_url": self.settings.ollama_url,
                        },
                    )
                    raise RuntimeError(
                        f"Ollama health check failed: HTTP {response.status}"
                    )
        except Exception as e:
            log_event(
                "ollama_connection_failed",
                {
                    "ollama_url": self.settings.ollama_url,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise RuntimeError(
                f"Cannot connect to Ollama at {self.settings.ollama_url}: {e}"
            ) from None

    @log_method(operation_name="model_pull")
    async def _pull_model(
        self, session: aiohttp.ClientSession, model_name: str
    ) -> bool:
        """Attempt to pull a model if it's not available."""
        log_event(
            "model_pull_started",
            {"model_name": model_name, "ollama_url": self.settings.ollama_url},
        )

        try:
            request_data = create_model_pull_request(model_name)
            async with session.post(
                f"{self.settings.ollama_url}{MODEL_PULL_ENDPOINT}", json=request_data
            ) as response:
                if response.status == 200:
                    log_event(
                        "model_pull_initiated",
                        {"model_name": model_name, "status": "pull_started"},
                    )
                    return True
                else:
                    log_event(
                        "model_pull_failed",
                        {"model_name": model_name, "http_status": response.status},
                    )
                    return False

        except Exception as e:
            log_event(
                "model_pull_error",
                {
                    "model_name": model_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            return False

    @log_method(operation_name="ollama_single_request")
    async def _single_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        request_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Make a single (non-streaming) request to Ollama."""
        log_event(
            "ollama_request_started",
            {
                "endpoint": endpoint,
                "model": request_data.get("model"),
                "stream": False,
                "timeout_seconds": 300,
            },
        )

        async with session.post(
            f"{self.settings.ollama_url}{endpoint}",
            json=request_data,
            # Timeout is configured at session level, no need to override here
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                log_event(
                    "ollama_request_failed",
                    {
                        "endpoint": endpoint,
                        "http_status": response.status,
                        "error_preview": (
                            error_text[:100] + "..."
                            if len(error_text) > 100
                            else error_text
                        ),
                    },
                )
                raise RuntimeError(
                    f"Ollama request failed: HTTP {response.status} - {error_text}"
                )

            response_data = await response.json()
            log_event(
                "ollama_request_completed",
                {
                    "endpoint": endpoint,
                    "response_keys": list(response_data.keys()),
                    "has_message": "message" in response_data,
                    "has_response": "response" in response_data,
                },
            )
            return dict(response_data)

    @log_method(operation_name="ollama_stream_request")
    async def _stream_request(
        self,
        session: aiohttp.ClientSession,
        endpoint: str,
        request_data: Dict[str, Any],
    ) -> str:
        """Make a streaming request to Ollama and return the full response."""
        accumulated_response = ""
        chunks_processed = 0

        log_event(
            "ollama_stream_started",
            {"endpoint": endpoint, "model": request_data.get("model"), "stream": True},
        )

        async with session.post(
            f"{self.settings.ollama_url}{endpoint}",
            json=request_data,
            # Timeout is configured at session level, no need to override here
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                log_event(
                    "ollama_stream_failed",
                    {
                        "endpoint": endpoint,
                        "http_status": response.status,
                        "error_preview": (
                            error_text[:100] + "..."
                            if len(error_text) > 100
                            else error_text
                        ),
                    },
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

        log_event(
            "ollama_stream_completed",
            {
                "endpoint": endpoint,
                "chunks_processed": chunks_processed,
                "response_length": len(accumulated_response),
            },
        )

        return accumulated_response

    @log_method(operation_name="ollama_chat_convenience")
    async def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Convenience method for chat-style interactions."""
        log_event(
            "chat_method_called",
            {
                "message_count": len(messages),
                "has_system": bool(system),
                "model": model or self.settings.llm_model,
            },
        )

        result = await self.execute(
            messages=messages,
            system=system,
            model=model or self.settings.llm_model,
            **kwargs,
        )
        return str(result.get("response", ""))

    @log_method(operation_name="ollama_generate_convenience")
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """Convenience method for simple text generation."""
        log_event(
            "generate_method_called",
            {
                "prompt_length": len(prompt),
                "has_system": bool(system),
                "model": model or self.settings.llm_model,
            },
        )

        result = await self.execute(
            prompt=prompt,
            system=system,
            model=model or self.settings.llm_model,
            **kwargs,
        )
        return str(result.get("response", ""))
