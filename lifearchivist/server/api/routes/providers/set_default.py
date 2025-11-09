"""
Set default provider endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .request_models import SetDefaultRequest
from .response_models import SetDefaultResponse

router = APIRouter()


@router.post(
    "/default",
    response_model=SetDefaultResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Admin providers cannot be set as default. Admin keys are for analytics only and cannot provide inference."
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
                    "example": {"detail": "Set default failed: <error message>"}
                }
            },
        },
    },
)
async def set_default_provider(request: SetDefaultRequest) -> SetDefaultResponse:
    """
    Set the default provider and optionally a default model.

    The default provider is used when no explicit provider is specified in requests.
    Admin providers cannot be set as default since they cannot provide inference.

    ## Request Body

    - **provider_id**: Provider ID to set as default
    - **default_model**: Optional default model to use with this provider

    ## Response Fields

    - **provider_id**: ID of the new default provider
    - **default_model**: Default model that was set (null if not provided)
    - **message**: Success confirmation message

    ## Example Request (Provider Only)

    ```json
    {
        "provider_id": "my-openai"
    }
    ```

    ## Example Request (Provider + Model)

    ```json
    {
        "provider_id": "my-openai",
        "default_model": "gpt-4o-mini"
    }
    ```

    ## Example Response

    ```json
    {
        "provider_id": "my-openai",
        "default_model": "gpt-4o-mini",
        "message": "Default provider updated"
    }
    ```

    ## Admin Provider Restriction

    Admin providers (using organization/admin keys) cannot be set as default because:
    - Admin keys are for analytics and usage tracking only
    - They cannot provide inference/generation capabilities
    - Attempting to set an admin provider as default returns 400 error

    ## Use Cases

    - Set default provider for all new conversations
    - Change default after adding a new provider
    - Set default model to use with the provider
    - Switch between different provider configurations

    ## Notes

    - Only one provider can be default at a time
    - Setting a new default automatically unsets the previous one
    - Provider must exist and be initialized
    - Admin providers are rejected (400 error)
    - Default model is optional and stored in settings
    - Changes take effect immediately for new requests
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    try:
        provider = server.llm_manager.get_provider(request.provider_id)
        if not provider:
            raise ResourceNotFoundError("Provider", request.provider_id)

        provider_info = next(
            (
                p
                for p in server.llm_manager.list_providers()
                if p["id"] == request.provider_id
            ),
            None,
        )

        if provider_info and provider_info.get("is_admin"):
            raise ValidationError(
                "Admin providers cannot be set as default. Admin keys are for analytics only and cannot provide inference."
            )

        result = server.llm_manager.set_default_provider(request.provider_id)

        if result.is_failure():
            error = result.error_or("Unknown error")
            error_type = result.error_type

            raise InternalServerError(
                "Set default provider", Exception(f"{error_type}: {error}")
            )

        if request.default_model:
            from lifearchivist.config import get_settings

            settings = get_settings()
            settings.llm_model = request.default_model

        return SetDefaultResponse(
            provider_id=request.provider_id,
            default_model=request.default_model,
            message="Default provider updated",
        )

    except (ServiceUnavailableError, ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Set default provider", e) from e
