"""
List providers endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .misc_models import ProviderInfo
from .response_models import ListProvidersResponse

router = APIRouter()


@router.get(
    "/",
    response_model=ListProvidersResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "LLM Manager service unavailable",
            "content": {
                "application/json": {"example": {"detail": "LLM manager not available"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "List providers failed: <error message>"}
                }
            },
        },
    },
)
async def list_providers() -> ListProvidersResponse:
    """
    List all registered LLM providers.

    Returns provider metadata including type, default status, and health.

    ## Response Fields

    - **id**: Unique provider identifier
    - **type**: Provider type (openai, anthropic, ollama, etc)
    - **name**: Human-readable provider name
    - **is_default**: Whether this is the default provider for requests
    - **is_healthy**: Current health status from health monitor
    - **is_admin**: Whether provider uses an admin/organization key

    ## Example Response

    ```json
    {
        "providers": [
            {
                "id": "openai-main",
                "type": "openai",
                "name": "OpenAI",
                "is_default": true,
                "is_healthy": true,
                "is_admin": false
            }
        ],
        "total": 1
    }
    ```
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    try:
        providers_data = server.llm_manager.list_providers()

        providers = [
            ProviderInfo(
                id=p["id"],
                type=p["type"],
                name=p["name"],
                is_default=p["is_default"],
                is_healthy=p["is_healthy"],
                is_admin=p["is_admin"],
            )
            for p in providers_data
        ]

        return ListProvidersResponse(providers=providers, total=len(providers))

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("List providers", e) from e
