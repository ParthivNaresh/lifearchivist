"""
Generate text endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from lifearchivist.llm import LLMMessage

from ..shared.dependencies import get_server
from .request_models import GenerateRequest

router = APIRouter()


@router.post("/generate")
async def generate_text(request: GenerateRequest):
    """
    Generate text using a provider.

    Example:
        ```json
        {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "model": "gpt-4o-mini",
            "provider_id": "my-openai",
            "temperature": 0.7,
            "max_tokens": 500
        }
        ```
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        llm_messages = [
            LLMMessage(
                role=msg["role"],
                content=msg["content"],
                name=msg.get("name"),
            )
            for msg in request.messages
        ]

        result = await server.llm_manager.generate(
            messages=llm_messages,
            model=request.model,
            provider_id=request.provider_id,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        response = result.unwrap()

        return {
            "success": True,
            "content": response.content,
            "model": response.model,
            "provider": response.provider,
            "tokens_used": response.tokens_used,
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "cost_usd": response.cost_usd,
            "finish_reason": response.finish_reason,
            "metadata": response.metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
