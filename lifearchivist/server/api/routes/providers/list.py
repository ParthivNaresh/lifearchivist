"""
List providers endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/")
async def list_providers():
    """
    List all registered LLM providers.

    Returns provider metadata including type, default status, and health.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        providers = server.llm_manager.list_providers()

        return {
            "success": True,
            "providers": providers,
            "total": len(providers),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
