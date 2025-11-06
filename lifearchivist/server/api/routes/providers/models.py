"""
List provider models endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .response_models import ListModelsResponse, ModelInfo

router = APIRouter()


@router.get(
    "/{provider_id}/models",
    response_model=ListModelsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Provider not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Provider not found: invalid-provider"}
                }
            },
        },
        503: {
            "description": "LLM Manager service unavailable",
            "content": {
                "application/json": {"example": {"detail": "LLM manager not available"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "List models failed: <error message>"}
                }
            },
        },
    },
)
async def list_provider_models(provider_id: str) -> ListModelsResponse:
    """
    List available models for a provider.

    Returns comprehensive model metadata including context windows, costs, and capabilities.

    ## Path Parameters

    - **provider_id**: Unique provider identifier (e.g., 'openai-main', 'anthropic-backup')

    ## Response Fields

    - **id**: Unique model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')
    - **name**: Human-readable model name
    - **provider**: Provider type (openai, anthropic, ollama, etc)
    - **provider_id**: Specific provider instance ID
    - **context_window**: Maximum context window size in tokens
    - **max_output_tokens**: Maximum output tokens
    - **supports_streaming**: Whether streaming is supported
    - **supports_functions**: Whether function calling is supported
    - **supports_vision**: Whether vision/image inputs are supported
    - **cost_per_1k_input**: Cost per 1K input tokens in USD (null if free/unknown)
    - **cost_per_1k_output**: Cost per 1K output tokens in USD (null if free/unknown)
    - **metadata**: Additional model-specific information

    ## Example Response

    ```json
    {
        "provider_id": "openai-main",
        "models": [
            {
                "id": "gpt-4o",
                "name": "GPT-4o",
                "provider": "openai",
                "provider_id": "openai-main",
                "context_window": 128000,
                "max_output_tokens": 4096,
                "supports_streaming": true,
                "supports_functions": true,
                "supports_vision": true,
                "cost_per_1k_input": 0.005,
                "cost_per_1k_output": 0.015,
                "metadata": {}
            }
        ],
        "total": 1
    }
    ```
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    try:
        result = await server.llm_manager.list_models(provider_id=provider_id)

        if result.is_failure():
            error = result.error_or("Unknown error")
            error_type = result.error_type

            if result.status_code == 404 or error_type == "ProviderNotFound":
                raise ResourceNotFoundError("Provider", provider_id)
            elif result.status_code == 503 or error_type == "ServiceUnavailable":
                raise ServiceUnavailableError(f"Provider {provider_id}")
            else:
                raise InternalServerError(
                    "List models", Exception(f"{error_type}: {error}")
                )

        models_data = result.unwrap()

        models = [
            ModelInfo(
                id=model.id,
                name=model.name,
                provider=model.provider,
                provider_id=model.provider_id,
                context_window=model.context_window,
                max_output_tokens=model.max_output_tokens,
                supports_streaming=model.supports_streaming,
                supports_functions=model.supports_functions,
                supports_vision=model.supports_vision,
                cost_per_1k_input=model.cost_per_1k_input,
                cost_per_1k_output=model.cost_per_1k_output,
                metadata=model.metadata,
            )
            for model in models_data
        ]

        return ListModelsResponse(
            provider_id=provider_id, models=models, total=len(models)
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("List models", e) from e
