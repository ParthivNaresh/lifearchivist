"""
Get available models endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..shared.dependencies import get_server
from .models import AvailableModelsResponse

router = APIRouter()


@router.get("/models", response_model=AvailableModelsResponse)
async def get_available_models():
    """
    Get available LLM and embedding models from all providers.

    Returns lists of:
    - LLM models from all registered providers (Ollama, OpenAI, etc.)
    - Embedding models for semantic search

    Queries the provider manager to get real-time model availability.
    """
    server = get_server()

    try:
        llm_models = []

        if server.service_container and server.service_container.llm_provider_manager:
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
                    import logging

                    logging.warning(
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

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve available models: {str(e)}"
        ) from None
