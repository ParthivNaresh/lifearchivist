"""
Update provider endpoint.
"""

import json
from typing import Any, NoReturn, Optional

from fastapi import APIRouter, status

from ..shared.constants import UNKNOWN_ERROR
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


class ProviderUpdateHandler:
    """Handles provider update workflow."""

    def __init__(self, server: Any, provider_id: str, request: UpdateProviderRequest):
        self.server = server
        self.provider_id = provider_id
        self.request = request
        self.config_updated = False
        self.default_updated = False

    def validate_services(self) -> None:
        """Validate required services are available."""
        if not self.server.llm_manager:
            raise ServiceUnavailableError("LLM manager")
        if not self.server.credential_service:
            raise ServiceUnavailableError("Credential service")

    def validate_request(self) -> None:
        """Validate that at least one update field is provided."""
        if self.request.config is None and self.request.set_as_default is None:
            raise ValidationError(
                "Must provide at least one of: config, set_as_default"
            )

    async def get_provider_type(self) -> Any:
        """Retrieve and validate provider type from metadata."""
        metadata_result = await self.server.credential_service.get_provider_metadata(
            self.provider_id
        )

        if metadata_result.is_failure():
            self._handle_metadata_failure(metadata_result)

        metadata = metadata_result.unwrap()
        provider_type = parse_provider_type(metadata["provider_type"])
        return provider_type

    def _handle_metadata_failure(self, metadata_result: Any) -> NoReturn:
        """Handle metadata retrieval failure."""
        error = metadata_result.error_or(UNKNOWN_ERROR)
        error_type = metadata_result.error_type
        status_code = metadata_result.status_code

        if status_code == 404 or error_type == "NotFoundError":
            raise ResourceNotFoundError("Provider", self.provider_id)
        else:
            raise InternalServerError(
                "Get provider metadata", Exception(f"{error_type}: {error}")
            )

    def prepare_new_config(self, provider_type: Any) -> Optional[Any]:
        """Prepare new configuration if provided."""
        if self.request.config is None:
            return None

        try:
            return create_provider_config(provider_type, self.request.config)
        except ValueError as e:
            raise ValidationError(str(e)) from e

    async def update_configuration(self, new_config: Optional[Any]) -> None:
        """Update provider configuration if new config provided."""
        if new_config is None or not self.server.provider_loader:
            return

        error_response = await reload_provider_with_new_config(
            self.server.credential_service,
            self.server.provider_loader,
            self.server.llm_manager,
            self.provider_id,
            new_config,
            self.request.set_as_default,
        )

        if error_response:
            self._handle_error_response(error_response, "Reload provider")

        self.config_updated = True
        if self.request.set_as_default is not None:
            self.default_updated = True

    async def update_default_status_only(self) -> None:
        """Update only the default status if no config changes."""
        if self.config_updated or self.request.set_as_default is None:
            return

        error_response = await update_provider_default_status(
            self.server.credential_service,
            self.server.llm_manager,
            self.provider_id,
            self.request.set_as_default,
        )

        if error_response:
            self._handle_error_response(error_response, "Update default status")

        self.default_updated = True

    def _handle_error_response(self, error_response: Any, operation: str) -> NoReturn:
        """Handle error response from update operations."""
        body_bytes = self._extract_body_bytes(error_response.body)
        content = json.loads(body_bytes.decode())
        error_msg = content.get("error", UNKNOWN_ERROR)
        raise InternalServerError(operation, Exception(error_msg))

    def _extract_body_bytes(self, body: Any) -> bytes:
        """Extract bytes from response body."""
        if isinstance(body, memoryview):
            return bytes(body)
        if isinstance(body, bytes):
            return body
        # If it's neither memoryview nor bytes, convert to bytes
        return str(body).encode("utf-8")

    def create_response(self) -> UpdateProviderResponse:
        """Create update response."""
        return UpdateProviderResponse(
            provider_id=self.provider_id,
            message="Provider updated successfully",
            config_updated=self.config_updated,
            default_updated=self.default_updated,
        )


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
    try:
        server = get_server()
        handler = ProviderUpdateHandler(server, provider_id, request)

        handler.validate_services()
        handler.validate_request()

        provider_type = await handler.get_provider_type()
        new_config = handler.prepare_new_config(provider_type)

        await handler.update_configuration(new_config)
        await handler.update_default_status_only()

        return handler.create_response()

    except (ServiceUnavailableError, ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Update provider", e) from e
