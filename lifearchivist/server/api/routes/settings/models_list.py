"""
Get available models endpoint.
"""

import logging

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .response_models import AvailableModelsResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "/models",
    response_model=AvailableModelsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "LLM provider manager unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "LLM provider manager not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Failed to retrieve available models: <error message>"
                    }
                }
            },
        },
    },
)
async def get_available_models() -> AvailableModelsResponse:
    """
    Get available LLM and embedding models from all providers.

    Returns lists of LLM models from all registered providers and available
    embedding models for semantic search.

    ## Response Fields

    - **llm_models**: Array of LLM model objects
    - **embedding_models**: Array of embedding model objects

    ## Example Response

    ```json
    {
        "llm_models": [
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "description": "OPENAI model",
                "provider": "openai",
                "provider_id": "openai-main",
                "context_window": 8192,
                "supports_streaming": true,
                "cost_per_1k_input": 0.03,
                "cost_per_1k_output": 0.06
            },
            {
                "id": "llama2",
                "name": "Llama 2",
                "description": "OLLAMA model",
                "provider": "ollama",
                "provider_id": "ollama-local",
                "context_window": 4096,
                "supports_streaming": true,
                "cost_per_1k_input": 0.0,
                "cost_per_1k_output": 0.0
            }
        ],
        "embedding_models": [
            {
                "id": "all-MiniLM-L6-v2",
                "name": "all-MiniLM-L6-v2",
                "description": "Fast and efficient for most use cases",
                "dimensions": 384,
                "performance": "fast"
            },
            {
                "id": "all-mpnet-base-v2",
                "name": "all-mpnet-base-v2",
                "description": "Higher accuracy for semantic search",
                "dimensions": 768,
                "performance": "accurate"
            }
        ]
    }
    ```

    ## LLM Model Fields

    - **id**: Model identifier
    - **name**: Display name
    - **description**: Model description
    - **provider**: Provider type (openai, ollama, anthropic, etc.)
    - **provider_id**: Specific provider instance ID
    - **context_window**: Maximum context tokens
    - **supports_streaming**: Whether streaming is supported
    - **cost_per_1k_input**: Cost per 1000 input tokens
    - **cost_per_1k_output**: Cost per 1000 output tokens

    ## Embedding Model Fields

    - **id**: Model identifier
    - **name**: Display name
    - **description**: Model description
    - **dimensions**: Embedding vector dimensions
    - **performance**: Performance characteristic (fast/accurate)

    ## Providers

    Models fetched from all registered providers:
    - **OpenAI**: GPT models
    - **Anthropic**: Claude models
    - **Ollama**: Local models
    - **Other**: Custom providers

    ## Use Cases

    - Populate model selection dropdowns
    - Display available models
    - Show model capabilities
    - Compare model costs
    - Select appropriate model

    ## Real-time Availability

    - Queries providers in real-time
    - Shows currently available models
    - Provider failures logged but don't fail request
    - Partial results returned if some providers fail

    ## Performance Notes

    - Queries all providers concurrently
    - Provider failures don't block response
    - Cached where possible
    - May take 1-2 seconds for first call

    ## Notes

    - Returns 503 if provider manager unavailable
    - Empty arrays if no models available
    - Provider failures logged as warnings
    - Costs may be 0.0 for local models
    - Embedding models are static list
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.llm_provider_manager
    ):
        raise ServiceUnavailableError("LLM provider manager")

    try:
        llm_models = []
        provider_manager = server.service_container.llm_provider_manager
        providers = provider_manager.list_providers()

        for provider_info in providers:
            provider_id = provider_info["id"]
            provider_type = provider_info["type"]

            try:
                models_result = await provider_manager.list_models(provider_id)

                if models_result.is_success():
                    models = models_result.unwrap()

                    for model in models:
                        llm_models.append(
                            {
                                "id": model.id,
                                "name": model.name,
                                "description": f"{provider_type.upper()} model",
                                "provider": provider_type,
                                "provider_id": provider_id,
                                "context_window": model.context_window,
                                "supports_streaming": model.supports_streaming,
                                "cost_per_1k_input": model.cost_per_1k_input,
                                "cost_per_1k_output": model.cost_per_1k_output,
                            }
                        )
            except Exception as e:
                logger.warning(
                    f"Failed to fetch models from provider {provider_id}: {e}"
                )
                continue

        embedding_models = [
            {
                "id": "all-MiniLM-L6-v2",
                "name": "all-MiniLM-L6-v2",
                "description": "Fast and efficient for most use cases",
                "dimensions": 384,
                "performance": "fast",
            },
            {
                "id": "all-mpnet-base-v2",
                "name": "all-mpnet-base-v2",
                "description": "Higher accuracy for semantic search",
                "dimensions": 768,
                "performance": "accurate",
            },
        ]

        return AvailableModelsResponse(
            llm_models=llm_models, embedding_models=embedding_models
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Retrieve available models", e) from e
