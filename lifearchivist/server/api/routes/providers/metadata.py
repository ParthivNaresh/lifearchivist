"""
Get provider metadata endpoint.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .misc_models import CostInfo, UsageInfo, WorkspaceInfo
from .response_models import (
    ProviderMetadataResponse,
)
from .utils import (
    fetch_provider_capabilities,
    fetch_provider_workspaces,
    fetch_time_based_metadata,
)

router = APIRouter()


@router.get(
    "/{provider_id}/metadata",
    response_model=ProviderMetadataResponse,
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
        501: {
            "description": "Feature not supported",
            "content": {
                "application/json": {
                    "example": {"detail": "Provider does not support metadata"}
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
                    "example": {"detail": "Get metadata failed: <error message>"}
                }
            },
        },
    },
)
async def get_provider_metadata(
    provider_id: str,
    include: List[str] = Query(  # noqa: B008
        default=["capabilities"], description="Metadata types to include"
    ),
    start_time: Optional[str] = Query(  # noqa: B008
        None, description="Start time for usage/cost reports (ISO 8601)"
    ),
    end_time: Optional[str] = Query(  # noqa: B008
        None, description="End time for usage/cost reports (ISO 8601)"
    ),
) -> ProviderMetadataResponse:
    """
    Get provider metadata including capabilities, workspaces, usage, and costs.

    Supports selective metadata retrieval based on provider capabilities.
    Some providers may not support all metadata types (returns 501 for unsupported features).

    ## Path Parameters

    - **provider_id**: Unique provider identifier

    ## Query Parameters

    - **include**: List of metadata types to include (default: ["capabilities"])
      - Valid values: capabilities, workspaces, usage, costs
      - Can specify multiple: `?include=capabilities&include=workspaces`
    - **start_time**: Start time for usage/cost reports (ISO 8601 format)
      - Required if requesting usage or costs
    - **end_time**: End time for usage/cost reports (ISO 8601 format)
      - Required if requesting usage or costs

    ## Response Fields

    - **provider_id**: Provider identifier
    - **capabilities**: List of supported capabilities (if requested)
    - **workspaces**: List of workspaces (if requested and supported)
    - **usage**: Usage statistics (if requested and supported)
    - **costs**: Cost information (if requested and supported)

    ## Example Requests

    ### Get Capabilities Only (Default)
    ```
    GET /api/providers/anthropic-work/metadata
    ```

    ### Get Capabilities and Workspaces
    ```
    GET /api/providers/anthropic-work/metadata?include=capabilities&include=workspaces
    ```

    ### Get Usage and Costs
    ```
    GET /api/providers/anthropic-work/metadata?include=usage&include=costs&start_time=2025-01-01T00:00:00Z&end_time=2025-01-08T00:00:00Z
    ```

    ## Example Response

    ```json
    {
        "provider_id": "anthropic-work",
        "capabilities": ["workspaces", "usage_tracking", "cost_tracking"],
        "workspaces": [
            {
                "id": "ws-123",
                "name": "My Workspace",
                "is_default": true,
                "metadata": {}
            }
        ],
        "usage": null,
        "costs": null
    }
    ```

    ## Provider Support

    - **OpenAI**: capabilities, usage, costs (with admin keys)
    - **Anthropic**: capabilities, workspaces, usage, costs (with admin keys)
    - **Ollama**: capabilities only
    - **Google**: capabilities, usage, costs
    - **Groq**: capabilities, usage, costs
    - **Mistral**: capabilities, usage, costs

    ## Notes

    - Returns 501 if provider doesn't support requested metadata type
    - Usage and costs require start_time and end_time parameters
    - Admin keys required for usage/cost tracking on some providers
    - Capabilities are always available for all providers
    - Null fields indicate feature not requested or not supported
    """
    server = get_server()

    if not server.llm_manager:
        raise ServiceUnavailableError("LLM manager")

    try:
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise ResourceNotFoundError("Provider", provider_id)

        response: Dict[str, Any] = {
            "provider_id": provider_id,
        }

        valid_includes = {"capabilities", "workspaces", "usage", "costs"}
        requested = set(include) & valid_includes

        if "capabilities" in requested:
            await fetch_provider_capabilities(server.llm_manager, provider_id, response)

        if "workspaces" in requested:
            error_response = await fetch_provider_workspaces(
                server.llm_manager, provider, provider_id, response
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
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=error_response.status_code, detail=error_msg
                )

        try:
            error_response = await fetch_time_based_metadata(
                server.llm_manager,
                provider_id,
                requested,
                start_time,
                end_time,
                response,
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
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=error_response.status_code, detail=error_msg
                )
        except ValidationError:
            raise

        capabilities = response.get("capabilities")
        workspaces_data = response.get("workspaces")
        usage_data = response.get("usage")
        costs_data = response.get("costs")

        workspaces = None
        if workspaces_data:
            workspaces = [
                WorkspaceInfo(
                    id=ws["id"],
                    name=ws["name"],
                    is_default=ws["is_default"],
                    metadata=ws.get("metadata"),
                )
                for ws in workspaces_data
            ]

        usage = None
        if usage_data:
            usage = UsageInfo(
                start_time=usage_data["start_time"],
                end_time=usage_data["end_time"],
                total_tokens=usage_data["total_tokens"],
                input_tokens=usage_data["input_tokens"],
                output_tokens=usage_data["output_tokens"],
                cached_tokens=usage_data.get("cached_tokens"),
                requests_count=usage_data["requests_count"],
                metadata=usage_data.get("metadata"),
            )

        costs = None
        if costs_data:
            costs = CostInfo(
                start_time=costs_data["start_time"],
                end_time=costs_data["end_time"],
                total_cost_usd=costs_data["total_cost_usd"],
                currency=costs_data["currency"],
                breakdown=costs_data.get("breakdown"),
                metadata=costs_data.get("metadata"),
            )

        return ProviderMetadataResponse(
            provider_id=provider_id,
            capabilities=capabilities,
            workspaces=workspaces,
            usage=usage,
            costs=costs,
        )

    except (ServiceUnavailableError, ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Get provider metadata", e) from e
