"""
List provider models endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/{provider_id}/models")
async def list_provider_models(provider_id: str):
    """
    List available models for a provider.

    Returns model metadata including context window, cost, and capabilities.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        result = await server.llm_manager.list_models(provider_id=provider_id)

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        models = result.unwrap()

        formatted_models = [
            {
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "provider_id": model.provider_id,
                "context_window": model.context_window,
                "max_output_tokens": model.max_output_tokens,
                "supports_streaming": model.supports_streaming,
                "supports_functions": model.supports_functions,
                "supports_vision": model.supports_vision,
                "cost_per_1k_input": model.cost_per_1k_input,
                "cost_per_1k_output": model.cost_per_1k_output,
                "metadata": model.metadata,
            }
            for model in models
        ]

        return {
            "success": True,
            "provider_id": provider_id,
            "models": formatted_models,
            "total": len(formatted_models),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
