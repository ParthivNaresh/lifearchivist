"""
Add provider endpoint.
"""

from fastapi import APIRouter, status

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
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    if not server.credential_service:
        raise ServiceUnavailableError("Credential service")

    try:
        provider_type = parse_provider_type(request.provider_type)
        config = create_provider_config(provider_type, request.config)
    except ValueError as e:
        raise ValidationError(str(e)) from e
    except Exception as e:
        raise InternalServerError("Parse provider configuration", e) from e

    try:
        store_result = await server.credential_service.add_provider(
            provider_id=request.provider_id,
            provider_type=provider_type,
            config=config,
            is_default=request.set_as_default,
        )

        if store_result.is_failure():
            error = store_result.error_or("Unknown error")
            error_type = store_result.error_type
            status_code = store_result.status_code

            if status_code == 409 or error_type == "ConflictError":
                raise ConflictError(f"Provider already exists: {request.provider_id}")
            elif status_code == 400 or error_type == "ValidationError":
                raise ValidationError(error)
            else:
                raise InternalServerError(
                    "Store credentials", Exception(f"{error_type}: {error}")
                )

        if server.provider_loader:
            load_result = await server.provider_loader.load_provider(
                request.provider_id
            )

            if load_result.is_failure():
                await server.credential_service.delete_provider(request.provider_id)

                error = load_result.error_or("Unknown error")
                error_type = load_result.error_type
                status_code = load_result.status_code

                if status_code == 400 or error_type == "ValidationError":
                    raise ValidationError(f"Failed to load provider: {error}")
                else:
                    raise InternalServerError(
                        "Load provider", Exception(f"{error_type}: {error}")
                    )

            provider = load_result.unwrap()

            add_result = await server.llm_manager.add_provider(
                provider, set_as_default=request.set_as_default
            )

            if add_result.is_failure():
                await server.credential_service.delete_provider(request.provider_id)

                error = add_result.error_or("Unknown error")
                error_type = add_result.error_type

                raise InternalServerError(
                    "Add to manager", Exception(f"{error_type}: {error}")
                )

        return AddProviderResponse(
            provider_id=request.provider_id,
            provider_type=provider_type.value,
            is_default=request.set_as_default,
            message="Provider added successfully",
        )

    except (ServiceUnavailableError, ValidationError, ConflictError):
        raise
    except Exception as e:
        raise InternalServerError("Add provider", e) from e
