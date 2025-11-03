"""
Set default provider endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from .request_models import SetDefaultRequest

router = APIRouter()


@router.post("/default")
async def set_default_provider(request: SetDefaultRequest):
    """
    Set the default provider and optionally a default model.

    The default provider is used when no explicit provider is specified.
    Admin providers cannot be set as default since they cannot provide inference.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        provider = server.llm_manager.get_provider(request.provider_id)
        if not provider:
            raise HTTPException(
                status_code=404, detail=f"Provider '{request.provider_id}' not found"
            )

        provider_info = next(
            (
                p
                for p in server.llm_manager.list_providers()
                if p["id"] == request.provider_id
            ),
            None,
        )

        if provider_info and provider_info.get("is_admin"):
            raise HTTPException(
                status_code=400,
                detail="Admin providers cannot be set as default. Admin keys are for analytics only and cannot provide inference.",
            )

        result = server.llm_manager.set_default_provider(request.provider_id)

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        if request.default_model:
            from lifearchivist.config import get_settings

            settings = get_settings()
            settings.llm_model = request.default_model

        return {
            "success": True,
            "provider_id": request.provider_id,
            "default_model": request.default_model,
            "message": "Default provider updated",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
