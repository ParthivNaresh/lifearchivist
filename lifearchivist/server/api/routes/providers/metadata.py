"""
Get provider metadata endpoint.
"""

import json
from typing import Any, Dict, List, NoReturn, Optional, Set

from fastapi import APIRouter, HTTPException, Query, status

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


class MetadataHandler:
    """Handles provider metadata retrieval workflow."""

    def __init__(
        self,
        server: Any,
        provider_id: str,
        include: List[str],
        start_time: Optional[str],
        end_time: Optional[str],
    ):
        self.server = server
        self.provider_id = provider_id
        self.include = include
        self.start_time = start_time
        self.end_time = end_time
        self.response: Dict[str, Any] = {"provider_id": provider_id}

    def validate_and_get_provider(self) -> Any:
        """Validate LLM manager and get provider."""
        if not self.server.llm_manager:
            raise ServiceUnavailableError("LLM manager")

        provider = self.server.llm_manager.get_provider(self.provider_id)
        if provider is None:
            raise ResourceNotFoundError("Provider", self.provider_id)

        return provider

    def get_requested_metadata_types(self) -> Set[str]:
        """Get valid requested metadata types."""
        valid_includes = {"capabilities", "workspaces", "usage", "costs"}
        return set(self.include) & valid_includes

    async def fetch_capabilities(self, requested: Set[str]) -> None:
        """Fetch provider capabilities if requested."""
        if "capabilities" in requested:
            fetch_provider_capabilities(
                self.server.llm_manager, self.provider_id, self.response
            )

    async def fetch_workspaces(self, requested: Set[str], provider: Any) -> None:
        """Fetch provider workspaces if requested."""
        if "workspaces" not in requested:
            return

        error_response = await fetch_provider_workspaces(
            self.server.llm_manager, provider, self.provider_id, self.response
        )
        if error_response:
            self._handle_error_response(error_response)

    async def fetch_time_metadata(self, requested: Set[str]) -> None:
        """Fetch time-based metadata (usage/costs) if requested."""
        error_response = await fetch_time_based_metadata(
            self.server.llm_manager,
            self.provider_id,
            requested,
            self.start_time,
            self.end_time,
            self.response,
        )
        if error_response:
            self._handle_error_response(error_response)

    def _handle_error_response(self, error_response: Any) -> NoReturn:
        """Handle error response from fetch operations."""
        body_bytes = self._extract_body_bytes(error_response.body)
        content = json.loads(body_bytes.decode())
        error_msg = content.get("error", "Unknown error")
        raise HTTPException(status_code=error_response.status_code, detail=error_msg)

    def _extract_body_bytes(self, body: Any) -> bytes:
        """Extract bytes from response body."""
        if isinstance(body, memoryview):
            return bytes(body)
        if isinstance(body, bytes):
            return body
        # If it's neither memoryview nor bytes, convert to bytes
        return str(body).encode("utf-8")

    def build_response(self) -> ProviderMetadataResponse:
        """Build final metadata response."""
        return ProviderMetadataResponse(
            provider_id=self.provider_id,
            capabilities=self.response.get("capabilities"),
            workspaces=self._build_workspaces(),
            usage=self._build_usage(),
            costs=self._build_costs(),
        )

    def _build_workspaces(self) -> Optional[List[WorkspaceInfo]]:
        """Build workspace info list from response data."""
        workspaces_data = self.response.get("workspaces")
        if not workspaces_data:
            return None

        return [
            WorkspaceInfo(
                id=ws["id"],
                name=ws["name"],
                is_default=ws["is_default"],
                metadata=ws.get("metadata"),
            )
            for ws in workspaces_data
        ]

    def _build_usage(self) -> Optional[UsageInfo]:
        """Build usage info from response data."""
        usage_data = self.response.get("usage")
        if not usage_data:
            return None

        return UsageInfo(
            start_time=usage_data["start_time"],
            end_time=usage_data["end_time"],
            total_tokens=usage_data["total_tokens"],
            input_tokens=usage_data["input_tokens"],
            output_tokens=usage_data["output_tokens"],
            cached_tokens=usage_data.get("cached_tokens"),
            requests_count=usage_data["requests_count"],
            metadata=usage_data.get("metadata"),
        )

    def _build_costs(self) -> Optional[CostInfo]:
        """Build cost info from response data."""
        costs_data = self.response.get("costs")
        if not costs_data:
            return None

        return CostInfo(
            start_time=costs_data["start_time"],
            end_time=costs_data["end_time"],
            total_cost_usd=costs_data["total_cost_usd"],
            currency=costs_data["currency"],
            breakdown=costs_data.get("breakdown"),
            metadata=costs_data.get("metadata"),
        )


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
    try:
        server = get_server()
        handler = MetadataHandler(server, provider_id, include, start_time, end_time)

        provider = handler.validate_and_get_provider()
        requested = handler.get_requested_metadata_types()

        await handler.fetch_capabilities(requested)
        await handler.fetch_workspaces(requested, provider)
        await handler.fetch_time_metadata(requested)

        return handler.build_response()

    except (
        ServiceUnavailableError,
        ResourceNotFoundError,
        ValidationError,
        HTTPException,
    ):
        raise
    except Exception as e:
        raise InternalServerError("Get provider metadata", e) from e
