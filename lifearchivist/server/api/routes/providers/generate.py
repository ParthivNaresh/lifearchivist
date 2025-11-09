"""
Generate text endpoint.
"""

from typing import Any, List, NoReturn

from fastapi import APIRouter, HTTPException, status

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


class GenerationHandler:
    """Handles text generation workflow."""

    def __init__(self, server: Any, request: GenerateRequest):
        self.server = server
        self.request = request

    def validate_service(self) -> None:
        """Validate LLM manager is available."""
        if not self.server.llm_manager:
            raise ServiceUnavailableError("LLM manager")

    def prepare_messages(self) -> List[LLMMessage]:
        """Convert request messages to LLM format."""
        try:
            return [
                LLMMessage(
                    role=msg["role"],
                    content=msg["content"],
                    name=msg.get("name"),
                )
                for msg in self.request.messages
            ]
        except (KeyError, ValueError) as e:
            raise ValidationError(f"Invalid message format: {str(e)}") from e

    async def generate_response(self, llm_messages: List[LLMMessage]) -> Any:
        """Generate text using LLM manager."""
        result = await self.server.llm_manager.generate(
            messages=llm_messages,
            model=self.request.model,
            provider_id=self.request.provider_id,
            temperature=self.request.temperature,
            max_tokens=self.request.max_tokens,
        )

        if result.is_failure():
            self._handle_generation_failure(result)

        return result.unwrap()

    def _handle_generation_failure(self, result: Any) -> NoReturn:
        """Handle generation failure based on error type."""
        error = result.error_or("Unknown error")
        error_type = result.error_type
        status_code = result.status_code

        error_handlers = {
            (404, None): self._handle_not_found,
            (None, "ProviderNotFound"): self._handle_not_found,
            (402, None): self._handle_budget_exceeded,
            (None, "BudgetExceeded"): self._handle_budget_exceeded,
            (503, None): self._handle_service_unavailable,
            (None, "ProviderUnhealthy"): self._handle_service_unavailable,
            (None, "ServiceUnavailable"): self._handle_service_unavailable,
            (400, None): self._handle_validation_error,
            (None, "ValidationError"): self._handle_validation_error,
        }

        for (code, err_type), handler in error_handlers.items():
            if (code and status_code == code) or (err_type and error_type == err_type):
                handler(error)

        raise InternalServerError("Generate text", Exception(f"{error_type}: {error}"))

    def _handle_not_found(self, error: str) -> NoReturn:
        """Handle provider or model not found error."""
        raise ResourceNotFoundError(
            "Provider or model", self.request.provider_id or "default"
        )

    def _handle_budget_exceeded(self, error: str) -> NoReturn:
        """Handle budget exceeded error."""
        raise HTTPException(status_code=402, detail=error)

    def _handle_service_unavailable(self, error: str) -> NoReturn:
        """Handle service unavailable error."""
        raise ServiceUnavailableError(f"Provider: {error}")

    def _handle_validation_error(self, error: str) -> NoReturn:
        """Handle validation error."""
        raise ValidationError(error)

    def create_response(self, llm_response: Any) -> GenerateResponse:
        """Create generation response from LLM response."""
        return GenerateResponse(
            content=llm_response.content,
            model=llm_response.model,
            provider=llm_response.provider,
            tokens_used=llm_response.tokens_used,
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            cost_usd=llm_response.cost_usd,
            finish_reason=llm_response.finish_reason,
            metadata=llm_response.metadata or {},
        )


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
    try:
        server = get_server()
        handler = GenerationHandler(server, request)

        handler.validate_service()
        llm_messages = handler.prepare_messages()
        llm_response = await handler.generate_response(llm_messages)

        return handler.create_response(llm_response)

    except (ServiceUnavailableError, ResourceNotFoundError, ValidationError):
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise InternalServerError("Generate text", e) from e
