"""
Get provider endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    not_found_response,
    success_response,
)
from .utils import validate_credential_service, validate_llm_manager

router = APIRouter()


@router.get("/{provider_id}")
async def get_provider(provider_id: str):
    """
    Get details for a specific provider.

    Returns provider metadata without exposing credentials.
    """
    server = get_server()
    llm_manager, error_response = validate_llm_manager(server)
    if error_response:
        return error_response

    credential_service, error_response = validate_credential_service(server)
    if error_response:
        return error_response

    assert llm_manager is not None
    assert credential_service is not None

    try:
        provider = llm_manager.get_provider(provider_id)

        if provider is None:
            return not_found_response("Provider", provider_id)

        metadata_result = await credential_service.get_provider_metadata(provider_id)

        if metadata_result.is_failure():
            return JSONResponse(
                content=metadata_result.to_dict(),
                status_code=metadata_result.status_code,
            )

        metadata = metadata_result.unwrap()

        is_healthy = True
        if llm_manager.health_monitor:
            is_healthy = llm_manager.health_monitor.is_healthy(provider_id)

        return success_response(
            {
                "provider_id": provider_id,
                "provider_type": provider.provider_type.value,
                "is_default": metadata.get("is_default", False),
                "is_initialized": provider.is_initialized,
                "is_healthy": is_healthy,
                "user_id": metadata.get("user_id", "default"),
            }
        )

    except Exception as e:
        return internal_error_response("Get provider", e)
