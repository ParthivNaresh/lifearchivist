"""
Test provider endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .response_models import TestProviderResponse

router = APIRouter()


@router.post(
    "/{provider_id}/test",
    response_model=TestProviderResponse,
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
                    "example": {"detail": "Test provider failed: <error message>"}
                }
            },
        },
    },
)
async def test_provider(provider_id: str) -> TestProviderResponse:
    """
    Test provider credentials and connectivity.

    Validates that the provider can be reached and credentials are valid.
    This is useful for verifying configuration before using the provider.

    ## Path Parameters

    - **provider_id**: Unique provider identifier to test

    ## Response Fields

    - **provider_id**: ID of the tested provider
    - **is_valid**: Whether credentials are valid and provider is reachable
    - **message**: Human-readable test result message

    ## Test Process

    1. Retrieve provider from manager
    2. Call provider's `validate_credentials()` method
    3. Return validation result

    ## Example Response (Success)

    ```json
    {
        "provider_id": "my-openai",
        "is_valid": true,
        "message": "Credentials valid"
    }
    ```

    ## Example Response (Failure)

    ```json
    {
        "provider_id": "my-openai",
        "is_valid": false,
        "message": "Credentials invalid"
    }
    ```

    ## Use Cases

    - Verify API keys are correct after adding a provider
    - Check connectivity before making expensive API calls
    - Diagnose authentication issues
    - Validate configuration changes

    ## Notes

    - Returns 200 OK even if credentials are invalid (check `is_valid` field)
    - Returns 404 if provider doesn't exist
    - Does not consume API credits (no actual generation)
    - Fast operation (typically < 1 second)
    - Provider-specific validation (API key check, endpoint ping, etc.)
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    try:
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise ResourceNotFoundError("Provider", provider_id)

        is_valid = await provider.validate_credentials()

        return TestProviderResponse(
            provider_id=provider_id,
            is_valid=is_valid,
            message="Credentials valid" if is_valid else "Credentials invalid",
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Test provider", e) from e
