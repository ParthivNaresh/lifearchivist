"""
Update provider endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from ..utils import reload_provider_with_new_config, update_provider_default_status
from .provider_utils import create_provider_config, parse_provider_type
from .request_models import UpdateProviderRequest

router = APIRouter()


@router.patch("/{provider_id}")
async def update_provider(provider_id: str, request: UpdateProviderRequest):
    """
    Update provider configuration.

    Can update credentials and/or default status.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    if not server.credential_service:
        raise HTTPException(status_code=503, detail="Credential service not available")

    if request.config is None and request.set_as_default is None:
        raise HTTPException(
            status_code=400,
            detail="Must provide at least one of: config, set_as_default",
        )

    try:
        metadata_result = await server.credential_service.get_provider_metadata(
            provider_id
        )

        if metadata_result.is_failure():
            return JSONResponse(
                content=metadata_result.to_dict(),
                status_code=metadata_result.status_code,
            )

        metadata = metadata_result.unwrap()
        provider_type = parse_provider_type(metadata["provider_type"])

        new_config = None
        if request.config is not None:
            new_config = create_provider_config(provider_type, request.config)

        if new_config is not None and server.provider_loader:
            error_response = await reload_provider_with_new_config(
                server.credential_service,
                server.provider_loader,
                server.llm_manager,
                provider_id,
                new_config,
                request.set_as_default,
            )
            if error_response:
                return error_response
        else:
            if request.set_as_default is not None:
                error_response = await update_provider_default_status(
                    server.credential_service,
                    server.llm_manager,
                    provider_id,
                    request.set_as_default,
                )
                if error_response:
                    return error_response

        return {
            "success": True,
            "provider_id": provider_id,
            "message": "Provider updated successfully",
            "config_updated": new_config is not None,
            "default_updated": request.set_as_default is not None,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
