"""
Get provider metadata endpoint.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..shared.dependencies import get_server
from ..utils import (
    fetch_provider_capabilities,
    fetch_provider_workspaces,
    fetch_time_based_metadata,
)

router = APIRouter()


@router.get("/{provider_id}/metadata")
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
):
    """
    Get provider metadata including capabilities, workspaces, usage, and costs.

    Query Parameters:
        - include: List of metadata types to include (capabilities, workspaces, usage, costs)
        - start_time: Start time for usage/cost reports (ISO 8601 format)
        - end_time: End time for usage/cost reports (ISO 8601 format)

    Examples:
        - GET /api/providers/anthropic-work/metadata
        - GET /api/providers/anthropic-work/metadata?include=capabilities&include=workspaces
        - GET /api/providers/anthropic-work/metadata?include=usage&include=costs&start_time=2025-01-01T00:00:00Z&end_time=2025-01-08T00:00:00Z

    Returns:
        Metadata object with requested fields. Unsupported features return 501.
    """
    server = get_server()

    if not server.llm_manager:
        raise HTTPException(status_code=503, detail="LLM manager not available")

    try:
        provider = server.llm_manager.get_provider(provider_id)

        if provider is None:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider_id}' not found",
            )

        response: Dict[str, Any] = {
            "success": True,
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
                return error_response

        error_response = await fetch_time_based_metadata(
            server.llm_manager, provider_id, requested, start_time, end_time, response
        )
        if error_response:
            return error_response

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
