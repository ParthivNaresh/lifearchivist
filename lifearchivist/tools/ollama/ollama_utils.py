"""
Ollama integration utilities and data models for LLM interactions.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel


class OllamaMessage(BaseModel):
    """Represents a message in Ollama chat format."""

    role: str
    content: str


class OllamaResponse(BaseModel):
    """Represents an Ollama API response."""

    model: str
    created_at: str
    message: OllamaMessage
    done: bool
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_count: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_count: Optional[int] = None
    eval_duration: Optional[int] = None


# Configuration constants
DEFAULT_REQUEST_TIMEOUT_SECONDS = 300
HEALTH_CHECK_ENDPOINT = "/api/tags"
CHAT_ENDPOINT = "/api/chat"
GENERATE_ENDPOINT = "/api/generate"
MODEL_PULL_ENDPOINT = "/api/pull"

# Default generation parameters
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7
DEFAULT_STREAMING = False


def format_system_user_prompt(system: str, prompt: str) -> str:
    """
    Combine system and user prompts into a single prompt for generate endpoint.

    Args:
        system: System instructions
        prompt: User prompt

    Returns:
        Formatted prompt combining both
    """
    return f"System: {system}\n\nUser: {prompt}"


def prepare_chat_request(
    model: str,
    messages: List[Dict[str, str]],
    system: Optional[str] = None,
    prompt: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    stream: bool = DEFAULT_STREAMING,
) -> Tuple[Dict[str, Any], str]:
    """
    Prepare request data for Ollama chat endpoint.

    Args:
        model: Model name to use
        messages: List of chat messages
        system: Optional system message
        prompt: Optional additional user prompt
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        stream: Enable streaming

    Returns:
        Tuple of (request_data, endpoint)
    """
    chat_messages = []

    if system:
        chat_messages.append({"role": "system", "content": system})

    chat_messages.extend(messages)

    if prompt:
        chat_messages.append({"role": "user", "content": prompt})

    request_data = {
        "model": model,
        "messages": chat_messages,
        "stream": stream,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }

    return request_data, CHAT_ENDPOINT


def prepare_generate_request(
    model: str,
    prompt: str,
    system: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    stream: bool = DEFAULT_STREAMING,
) -> Tuple[Dict[str, Any], str]:
    """
    Prepare request data for Ollama generate endpoint.

    Args:
        model: Model name to use
        prompt: Text prompt
        system: Optional system instructions
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        stream: Enable streaming

    Returns:
        Tuple of (request_data, endpoint)
    """
    full_prompt = format_system_user_prompt(system, prompt) if system else prompt

    request_data = {
        "model": model,
        "prompt": full_prompt,
        "stream": stream,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }

    return request_data, GENERATE_ENDPOINT


def extract_response_text(response_data: Dict[str, Any], endpoint: str) -> str:
    """
    Extract the response text from Ollama API response based on endpoint.

    Args:
        response_data: Raw API response data
        endpoint: API endpoint used (/api/chat or /api/generate)

    Returns:
        Extracted response text
    """
    if endpoint == CHAT_ENDPOINT:
        # Ensure we return a string by casting the result
        content = response_data.get("message", {}).get("content", "")
        return str(content) if content is not None else ""
    else:
        # Ensure we return a string by casting the result
        response = response_data.get("response", "")
        return str(response) if response is not None else ""


def calculate_generation_metrics(
    response_data: Dict[str, Any], output_length: int, tokens_generated: int
) -> Dict[str, Any]:
    """
    Calculate generation performance metrics from Ollama response.

    Args:
        response_data: Raw API response with timing data
        output_length: Length of generated text in characters
        tokens_generated: Number of tokens generated

    Returns:
        Dictionary of performance metrics
    """
    metrics = {}

    # Extract timing data (in nanoseconds)
    total_duration_ns = response_data.get("total_duration", 0)
    eval_duration_ns = response_data.get("eval_duration", 0)
    prompt_eval_count = response_data.get("prompt_eval_count", 0)

    # Convert to milliseconds for user-friendly metrics
    generation_time_ms = total_duration_ns // 1_000_000

    metrics.update(
        {
            "ollama_total_duration_ns": total_duration_ns,
            "ollama_eval_duration_ns": eval_duration_ns,
            "ollama_prompt_eval_count": prompt_eval_count,
            "generation_time_ms": generation_time_ms,
        }
    )

    # Calculate efficiency metrics
    if generation_time_ms > 0:
        chars_per_second = int(output_length * 1000 / generation_time_ms)
        tokens_per_second = (
            int(tokens_generated * 1000 / generation_time_ms)
            if tokens_generated > 0
            else 0
        )
        metrics.update(
            {
                "chars_per_second": chars_per_second,
                "tokens_per_second": tokens_per_second,
            }
        )
    else:
        metrics.update(
            {
                "chars_per_second": 0,
                "tokens_per_second": 0,
            }
        )

    return metrics


def calculate_input_metrics(
    prompt: Optional[str], messages: List[Dict[str, str]], system: Optional[str]
) -> Dict[str, int]:
    """
    Calculate input-related metrics for logging and analysis.

    Args:
        prompt: User prompt text
        messages: Chat messages
        system: System instructions

    Returns:
        Dictionary of input metrics
    """
    input_length = (
        len(prompt) if prompt else sum(len(msg.get("content", "")) for msg in messages)
    )
    system_length = len(system) if system else 0

    return {
        "input_length": input_length,
        "system_length": system_length,
    }


def extract_models_from_health_response(health_data: Dict[str, Any]) -> List[str]:
    """
    Extract available model names from Ollama health check response.

    Args:
        health_data: Response from /api/tags endpoint

    Returns:
        List of available model names
    """
    return [model["name"] for model in health_data.get("models", [])]


def create_model_pull_request(model_name: str) -> Dict[str, str]:
    """
    Create request data for pulling a model from Ollama.

    Args:
        model_name: Name of model to pull

    Returns:
        Request data for model pull API
    """
    return {"name": model_name}


def parse_streaming_chunk(line: bytes, endpoint: str) -> Tuple[str, bool]:
    """
    Parse a single streaming response chunk from Ollama.

    Args:
        line: Raw bytes from streaming response
        endpoint: API endpoint used

    Returns:
        Tuple of (content, is_done)
    """
    try:
        chunk_data = json.loads(line.decode().strip())

        if endpoint == CHAT_ENDPOINT:
            content = chunk_data.get("message", {}).get("content", "")
        else:
            content = chunk_data.get("response", "")

        is_done = chunk_data.get("done", False)
        return content, is_done

    except json.JSONDecodeError:
        return "", False


def create_success_response(
    response_text: str,
    model: str,
    tokens_generated: int,
    generation_time_ms: int,
) -> Dict[str, Any]:
    """
    Create standardized success response for Ollama operations.

    Args:
        response_text: Generated text
        model: Model used
        tokens_generated: Number of tokens generated
        generation_time_ms: Generation time in milliseconds

    Returns:
        Standardized response dictionary
    """
    return {
        "response": response_text,
        "model": model,
        "tokens_generated": tokens_generated,
        "generation_time_ms": generation_time_ms,
    }


def create_error_response(model: str, error: Exception) -> Dict[str, Any]:
    """
    Create standardized error response for Ollama operations.

    Args:
        model: Model that was being used
        error: Exception that occurred

    Returns:
        Standardized error response dictionary
    """
    return {
        "response": "",
        "model": model,
        "tokens_generated": 0,
        "generation_time_ms": 0,
        "error": str(error),
    }
