"""
Add provider endpoint.
"""

from typing import Any, NoReturn

from fastapi import APIRouter, status

from ..shared.constants import UNKNOWN_ERROR
from ..shared.dependencies import get_server
from ..shared.exceptions import (
    ConflictError,
    InternalServerError,
    ServiceUnavailableError,
    ValidationError,
)
from .provider_utils import create_provider_config, parse_provider_type
from .request_models import AddProviderRequest
from .response_models import AddProviderResponse

router = APIRouter()


class ProviderAdditionHandler:
    """Handles the provider addition workflow with automatic rollback."""

    def __init__(self, server: Any, request: AddProviderRequest):
        self.server = server
        self.request = request
        self.provider_id = request.provider_id
        self.set_as_default = request.set_as_default

    def validate_services(self) -> None:
        """Validate required services are available."""
        if not self.server.llm_manager:
            raise ServiceUnavailableError("LLM manager")
        if not self.server.credential_service:
            raise ServiceUnavailableError("Credential service")

    def parse_configuration(self) -> tuple[Any, Any]:
        """Parse and validate provider configuration."""
        try:
            provider_type = parse_provider_type(self.request.provider_type)
            config = create_provider_config(provider_type, self.request.config)
            return provider_type, config
        except ValueError as e:
            raise ValidationError(str(e)) from e
        except Exception as e:
            raise InternalServerError("Parse provider configuration", e) from e

    async def store_credentials(self, provider_type: Any, config: Any) -> None:
        """Store provider credentials in secure storage."""
        store_result = await self.server.credential_service.add_provider(
            provider_id=self.provider_id,
            provider_type=provider_type,
            config=config,
            is_default=self.set_as_default,
        )

        if store_result.is_failure():
            self._handle_store_failure(store_result)

    def _handle_store_failure(self, store_result: Any) -> NoReturn:
        """Handle credential storage failure."""
        error = store_result.error_or(UNKNOWN_ERROR)
        error_type = store_result.error_type
        status_code = store_result.status_code

        if status_code == 409 or error_type == "ConflictError":
            raise ConflictError(f"Provider already exists: {self.provider_id}")
        elif status_code == 400 or error_type == "ValidationError":
            raise ValidationError(error)
        else:
            raise InternalServerError(
                "Store credentials", Exception(f"{error_type}: {error}")
            )

    async def load_and_add_provider(self) -> Any:
        """Load provider and add to manager with rollback on failure."""
        if not self.server.provider_loader:
            return None

        provider = await self._load_provider()
        await self._add_to_manager(provider)
        return provider

    async def _load_provider(self) -> Any:
        """Load provider instance from stored configuration."""
        load_result = await self.server.provider_loader.load_provider(self.provider_id)

        if load_result.is_failure():
            await self._rollback_credentials()
            self._handle_load_failure(load_result)

        return load_result.unwrap()

    def _handle_load_failure(self, load_result: Any) -> NoReturn:
        """Handle provider loading failure."""
        error = load_result.error_or(UNKNOWN_ERROR)
        error_type = load_result.error_type
        status_code = load_result.status_code

        if status_code == 400 or error_type == "ValidationError":
            raise ValidationError(f"Failed to load provider: {error}")
        else:
            raise InternalServerError(
                "Load provider", Exception(f"{error_type}: {error}")
            )

    async def _add_to_manager(self, provider: Any) -> None:
        """Add provider to LLM manager."""
        add_result = await self.server.llm_manager.add_provider(
            provider, set_as_default=self.set_as_default
        )

        if add_result.is_failure():
            await self._rollback_credentials()
            self._handle_add_failure(add_result)

    def _handle_add_failure(self, add_result: Any) -> NoReturn:
        """Handle manager addition failure."""
        error = add_result.error_or(UNKNOWN_ERROR)
        error_type = add_result.error_type
        raise InternalServerError("Add to manager", Exception(f"{error_type}: {error}"))

    async def _rollback_credentials(self) -> None:
        """Rollback stored credentials on failure."""
        await self.server.credential_service.delete_provider(self.provider_id)

    def create_response(self, provider_type: Any) -> AddProviderResponse:
        """Create successful response."""
        return AddProviderResponse(
            provider_id=self.provider_id,
            provider_type=provider_type.value,
            is_default=self.set_as_default,
            message="Provider added successfully",
        )


@router.post(
    "/",
    response_model=AddProviderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "description": "Invalid configuration",
            "content": {
                "application/json": {"example": {"detail": "Invalid API key format"}}
            },
        },
        409: {
            "description": "Provider already exists",
            "content": {
                "application/json": {
                    "example": {"detail": "Provider already exists: my-openai"}
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
                    "example": {"detail": "Add provider failed: <error message>"}
                }
            },
        },
    },
)
async def add_provider(request: AddProviderRequest) -> AddProviderResponse:
    """
    Add a new LLM provider with automatic rollback on failure.

    Validates configuration, stores encrypted credentials, loads provider instance,
    and initializes it in the manager. Automatically rolls back on any failure.

    ## Request Body

    - **provider_id**: Unique identifier for the provider (e.g., 'my-openai', 'work-anthropic')
    - **provider_type**: Provider type (openai, anthropic, ollama, google, groq, mistral)
    - **config**: Provider-specific configuration (API keys, endpoints, etc.)
    - **set_as_default**: Whether to set as default provider (default: false)

    ## Response Fields

    - **provider_id**: ID of the added provider
    - **provider_type**: Provider type
    - **is_default**: Whether this is the default provider
    - **message**: Success confirmation message

    ## Provider Configuration Examples

    ### OpenAI
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

    ### Anthropic
    ```json
    {
        "provider_id": "my-anthropic",
        "provider_type": "anthropic",
        "config": {
            "api_key": "sk-ant-..."
        }
    }
    ```

    ### Ollama
    ```json
    {
        "provider_id": "local-ollama",
        "provider_type": "ollama",
        "config": {
            "base_url": "http://localhost:11434"
        }
    }
    ```

    ## Addition Process (with Automatic Rollback)

    1. **Validate** configuration and parse provider type
    2. **Store** encrypted credentials in secure storage
    3. **Load** provider instance from configuration
    4. **Initialize** provider in LLM manager
    5. **Rollback** automatically if any step fails

    ## Example Response

    ```json
    {
        "provider_id": "my-openai",
        "provider_type": "openai",
        "is_default": true,
        "message": "Provider added successfully"
    }
    ```

    ## Notes

    - Credentials are encrypted before storage
    - Provider is validated before being added
    - Automatic rollback on failure (credentials deleted)
    - Cannot add duplicate provider IDs (409 error)
    - Configuration is provider-specific
    - Returns 201 Created on success
    """
    try:
        server = get_server()
        handler = ProviderAdditionHandler(server, request)

        handler.validate_services()
        provider_type, config = handler.parse_configuration()

        await handler.store_credentials(provider_type, config)
        await handler.load_and_add_provider()

        return handler.create_response(provider_type)

    except (ServiceUnavailableError, ValidationError, ConflictError):
        raise
    except Exception as e:
        raise InternalServerError("Add provider", e) from e
