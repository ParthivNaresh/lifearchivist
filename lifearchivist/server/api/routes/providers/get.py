"""
Get provider endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/{provider_id}")
async def get_provider(provider_id: str):
    """
    Get details for a specific provider.

    Returns provider metadata without exposing credentials.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    if not server.credential_service:
        raise HTTPException(status_code=503, detail="Credential service not available")

    try:
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found",
            )

        metadata_result = await server.credential_service.get_provider_metadata(
            provider_id
        )

        if metadata_result.is_failure():
            return JSONResponse(
                content=metadata_result.to_dict(),
                status_code=metadata_result.status_code,
            )

        metadata = metadata_result.unwrap()

        is_healthy = True
        if server.llm_manager.health_monitor:
            is_healthy = server.llm_manager.health_monitor.is_healthy(provider_id)

        return {
            "success": True,
            "provider_id": provider_id,
            "provider_type": provider.provider_type.value,
            "is_default": metadata.get("is_default", False),
            "is_initialized": provider.is_initialized,
            "is_healthy": is_healthy,
            "user_id": metadata.get("user_id", "default"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
