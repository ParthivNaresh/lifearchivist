"""
Generate text endpoint.
"""

from fastapi import APIRouter, status

from lifearchivist.llm import LLMMessage

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .request_models import GenerateRequest
from .response_models import GenerateResponse

router = APIRouter()


@router.post(
    "/generate",
    response_model=GenerateResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid request parameters",
            "content": {
                "application/json": {"example": {"detail": "Invalid message format"}}
            },
        },
        402: {
            "description": "Budget exceeded",
            "content": {
                "application/json": {"example": {"detail": "Budget exceeded for user"}}
            },
        },
        404: {
            "description": "Provider or model not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Provider not found: invalid-provider"}
                }
            },
        },
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {"example": {"detail": "LLM manager not available"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Generate text failed: <error message>"}
                }
            },
        },
    },
)
async def generate_text(request: GenerateRequest) -> GenerateResponse:
    """
    Generate text using an LLM provider.

    Supports multiple providers (OpenAI, Anthropic, Ollama, etc.) with automatic
    routing, cost tracking, and health monitoring.

    ## Request Body

    - **messages**: List of conversation messages with role and content
      - Each message must have `role` (system/user/assistant) and `content`
      - Optional `name` field for message attribution
    - **model**: Model identifier (e.g., 'gpt-4o-mini', 'claude-3-5-sonnet-20241022')
    - **provider_id**: Optional provider ID (uses default if not specified)
    - **temperature**: Sampling temperature (0.0-2.0, default: 0.7)
      - Lower = more deterministic, Higher = more creative
    - **max_tokens**: Maximum tokens to generate (1-100000, default: 2000)

    ## Response Fields

    - **content**: Generated text response
    - **model**: Model identifier used for generation
    - **provider**: Provider type that generated the response
    - **tokens_used**: Total tokens consumed (prompt + completion)
    - **prompt_tokens**: Tokens in the prompt
    - **completion_tokens**: Tokens in the completion
    - **cost_usd**: Estimated cost in USD (null if free/unknown)
    - **finish_reason**: Why generation stopped (stop, length, error, etc)
    - **metadata**: Additional provider-specific response data

    ## Example Request

    ```json
    {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "model": "gpt-4o-mini",
        "provider_id": "openai-main",
        "temperature": 0.7,
        "max_tokens": 500
    }
    ```

    ## Example Response

    ```json
    {
        "content": "The capital of France is Paris.",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "tokens_used": 25,
        "prompt_tokens": 15,
        "completion_tokens": 10,
        "cost_usd": 0.000125,
        "finish_reason": "stop",
        "metadata": {}
    }
    ```

    ## Error Codes

    - **400**: Invalid message format or parameters
    - **402**: Budget exceeded (cost tracking enabled)
    - **404**: Provider or model not found
    - **503**: Provider unhealthy or service unavailable
    - **500**: Unexpected generation error
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    try:
        llm_messages = [
            LLMMessage(
                role=msg["role"],
                content=msg["content"],
                name=msg.get("name"),
            )
            for msg in request.messages
        ]

    except (KeyError, ValueError) as e:
        raise ValidationError(f"Invalid message format: {str(e)}") from e

    try:
        result = await server.llm_manager.generate(
            messages=llm_messages,
            model=request.model,
            provider_id=request.provider_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        if result.is_failure():
            error = result.error_or("Unknown error")
            error_type = result.error_type
            status_code = result.status_code

            if status_code == 404 or error_type == "ProviderNotFound":
                raise ResourceNotFoundError(
                    "Provider or model", request.provider_id or "default"
                )
            elif status_code == 402 or error_type == "BudgetExceeded":
                from fastapi import HTTPException

                raise HTTPException(status_code=402, detail=error)
            elif status_code == 503 or error_type in (
                "ProviderUnhealthy",
                "ServiceUnavailable",
            ):
                raise ServiceUnavailableError(f"Provider: {error}")
            elif status_code == 400 or error_type == "ValidationError":
                raise ValidationError(error)
            else:
                raise InternalServerError(
                    "Generate text", Exception(f"{error_type}: {error}")
                )

        response = result.unwrap()

        return GenerateResponse(
            content=response.content,
            model=response.model,
            provider=response.provider,
            tokens_used=response.tokens_used,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            cost_usd=response.cost_usd,
            finish_reason=response.finish_reason,
            metadata=response.metadata or {},
        )

    except (ServiceUnavailableError, ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Generate text", e) from e
