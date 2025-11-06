"""
Update provider endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .provider_utils import create_provider_config, parse_provider_type
from .request_models import UpdateProviderRequest
from .response_models import UpdateProviderResponse
from .utils import reload_provider_with_new_config, update_provider_default_status

router = APIRouter()


@router.patch(
    "/{provider_id}",
    response_model=UpdateProviderResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Must provide at least one of: config, set_as_default"
                    }
                }
            },
        },
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
                    "example": {"detail": "Update provider failed: <error message>"}
                }
            },
        },
    },
)
async def update_provider(
    provider_id: str, request: UpdateProviderRequest
) -> UpdateProviderResponse:
    """
    Update provider configuration and/or default status.

    Supports partial updates - can update configuration, default status, or both.
    Configuration updates trigger provider reload with new credentials.

    ## Path Parameters

    - **provider_id**: Unique provider identifier to update

    ## Request Body

    - **config**: Optional new provider configuration (API keys, endpoints, etc.)
    - **set_as_default**: Optional flag to set/unset as default provider

    ## Response Fields

    - **provider_id**: ID of the updated provider
    - **message**: Success confirmation message
    - **config_updated**: Whether configuration was updated
    - **default_updated**: Whether default status was updated

    ## Update Scenarios

    ### Update Configuration Only
    ```json
    {
        "config": {
            "api_key": "sk-new-key..."
        }
    }
    ```

    ### Update Default Status Only
    ```json
    {
        "set_as_default": true
    }
    ```

    ### Update Both
    ```json
    {
        "config": {
            "api_key": "sk-new-key..."
        },
        "set_as_default": true
    }
    ```

    ## Update Process (Configuration)

    1. Retrieve existing provider metadata
    2. Parse and validate new configuration
    3. Update credentials in secure storage
    4. Reload provider with new configuration
    5. Remove old provider instance
    6. Add new provider instance to manager
    7. Optionally update default status

    ## Update Process (Default Status Only)

    1. Update default flag in credential storage
    2. Update default provider in manager

    ## Example Response

    ```json
    {
        "provider_id": "my-openai",
        "message": "Provider updated successfully",
        "config_updated": true,
        "default_updated": false
    }
    ```

    ## Notes

    - At least one field (config or set_as_default) must be provided
    - Configuration updates trigger full provider reload
    - Provider is temporarily unavailable during reload
    - Old credentials are replaced, not merged
    - Returns 404 if provider doesn't exist
    - Validates new configuration before applying
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    if not server.credential_service:
        raise ServiceUnavailableError("Credential service")

    if request.config is None and request.set_as_default is None:
        raise ValidationError("Must provide at least one of: config, set_as_default")

    try:
        metadata_result = await server.credential_service.get_provider_metadata(
            provider_id
        )

        if metadata_result.is_failure():
            error = metadata_result.error_or("Unknown error")
            error_type = metadata_result.error_type
            status_code = metadata_result.status_code

            if status_code == 404 or error_type == "NotFoundError":
                raise ResourceNotFoundError("Provider", provider_id)
            else:
                raise InternalServerError(
                    "Get provider metadata", Exception(f"{error_type}: {error}")
                )

        metadata = metadata_result.unwrap()
        provider_type = parse_provider_type(metadata["provider_type"])

        new_config = None
        if request.config is not None:
            try:
                new_config = create_provider_config(provider_type, request.config)
            except ValueError as e:
                raise ValidationError(str(e)) from e

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
                import json

                body_bytes = (
                    bytes(error_response.body)
                    if isinstance(error_response.body, memoryview)
                    else error_response.body
                )
                content = json.loads(body_bytes.decode())
                error_msg = content.get("error", "Unknown error")
                raise InternalServerError("Reload provider", Exception(error_msg))
        else:
            if request.set_as_default is not None:
                error_response = await update_provider_default_status(
                    server.credential_service,
                    server.llm_manager,
                    provider_id,
                    request.set_as_default,
                )
                if error_response:
                    import json

                    body_bytes = (
                        bytes(error_response.body)
                        if isinstance(error_response.body, memoryview)
                        else error_response.body
                    )
                    content = json.loads(body_bytes.decode())
                    error_msg = content.get("error", "Unknown error")
                    raise InternalServerError(
                        "Update default status", Exception(error_msg)
                    )

        return UpdateProviderResponse(
            provider_id=provider_id,
            message="Provider updated successfully",
            config_updated=new_config is not None,
            default_updated=request.set_as_default is not None,
        )

    except (ServiceUnavailableError, ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Update provider", e) from e
