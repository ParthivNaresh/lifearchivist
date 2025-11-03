"""
Add provider endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from .provider_utils import create_provider_config, parse_provider_type
from .request_models import AddProviderRequest

router = APIRouter()


@router.post("/")
async def add_provider(request: AddProviderRequest):
    """
    Add a new LLM provider.

    Validates configuration, stores encrypted credentials, and initializes the provider.

    Example:
        ```json
        {
            "provider_id": "my-openai",
            "provider_type": "openai",
            "config": {
                "api_key": "sk-...",
                "organization": "org-..."
            },
            "set_as_default": true
        }
        ```
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    if not server.credential_service:
        raise HTTPException(status_code=503, detail="Credential service not available")

    try:
        provider_type = parse_provider_type(request.provider_type)

        config = create_provider_config(provider_type, request.config)

        store_result = await server.credential_service.add_provider(
            provider_id=request.provider_id,
            provider_type=provider_type,
            config=config,
            is_default=request.set_as_default,
        )

        if store_result.is_failure():
            return JSONResponse(
                content=store_result.to_dict(),
                status_code=store_result.status_code,
            )

        if server.provider_loader:
            load_result = await server.provider_loader.load_provider(
                request.provider_id
            )

            if load_result.is_failure():
                await server.credential_service.delete_provider(request.provider_id)
                return JSONResponse(
                    content=load_result.to_dict(),
                    status_code=load_result.status_code,
                )

            provider = load_result.unwrap()

            add_result = await server.llm_manager.add_provider(
                provider, set_as_default=request.set_as_default
            )

            if add_result.is_failure():
                await server.credential_service.delete_provider(request.provider_id)
                return JSONResponse(
                    content=add_result.to_dict(),
                    status_code=add_result.status_code,
                )

        return {
            "success": True,
            "provider_id": request.provider_id,
            "provider_type": provider_type.value,
            "is_default": request.set_as_default,
            "message": "Provider added successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
