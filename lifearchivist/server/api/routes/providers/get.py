"""
Get provider endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .response_models import GetProviderResponse

router = APIRouter()


@router.get(
    "/{provider_id}",
    response_model=GetProviderResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Provider not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Provider not found: invalid-provider"}
                }
            },
        },
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {"example": {"detail": "LLM manager not available"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Get provider failed: <error message>"}
                }
            },
        },
    },
)
async def get_provider(provider_id: str) -> GetProviderResponse:
    """
    Get details for a specific provider.

    Returns provider metadata without exposing credentials.

    ## Path Parameters

    - **provider_id**: Unique provider identifier (e.g., 'openai-main', 'anthropic-backup')

    ## Response Fields

    - **provider_id**: Unique provider identifier
    - **provider_type**: Provider type (openai, anthropic, ollama, etc)
    - **is_default**: Whether this is the default provider for requests
    - **is_initialized**: Whether provider has been initialized and is ready
    - **is_healthy**: Current health status from health monitor
    - **user_id**: User ID associated with this provider (for multi-tenant setups)

    ## Example Response

    ```json
    {
        "provider_id": "openai-main",
        "provider_type": "openai",
        "is_default": true,
        "is_initialized": true,
        "is_healthy": true,
        "user_id": "default"
    }
    ```

    ## Notes

    - Credentials are never exposed in the response
    - Health status is checked in real-time if health monitor is enabled
    - Returns 404 if provider doesn't exist
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    if not server.credential_service:
        raise ServiceUnavailableError("Credential service")

    try:
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise ResourceNotFoundError("Provider", provider_id)

        metadata_result = await server.credential_service.get_provider_metadata(
            provider_id
        )

        if metadata_result.is_failure():
            error = metadata_result.error_or("Unknown error")
            error_type = metadata_result.error_type

            if metadata_result.status_code == 404 or error_type == "NotFoundError":
                raise ResourceNotFoundError("Provider metadata", provider_id)
            else:
                raise InternalServerError(
                    "Get provider metadata", Exception(f"{error_type}: {error}")
                )

        metadata = metadata_result.unwrap()

        is_healthy = True
        if server.llm_manager.health_monitor:
            is_healthy = server.llm_manager.health_monitor.is_healthy(provider_id)

        return GetProviderResponse(
            provider_id=provider_id,
            provider_type=provider.provider_type.value,
            is_default=metadata.get("is_default", False),
            is_initialized=provider.is_initialized,
            is_healthy=is_healthy,
            user_id=metadata.get("user_id", "default"),
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Get provider", e) from e
