"""
Utility functions for search endpoints.
"""

from typing import Any, Dict, Optional, Tuple

from fastapi.responses import JSONResponse

from ..shared.responses import service_unavailable_response, validation_error_response
from .constants import DEFAULT_SEMANTIC_WEIGHT, DEFAULT_SIMILARITY_THRESHOLD


def validate_llamaindex_service(
    server: Any,
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Validate LlamaIndex service availability.

    Args:
        server: Server instance

    Returns:
        Tuple of (service, error_response) where one is None
    """
    if not server.llamaindex_service:
        return None, service_unavailable_response("Search service")

    return server.llamaindex_service, None


def validate_search_service(
    llamaindex_service: Any,
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Validate search service availability.

    Args:
        llamaindex_service: LlamaIndex service instance

    Returns:
        Tuple of (service, error_response) where one is None
    """
    if not llamaindex_service.search_service:
        return None, service_unavailable_response(
            "Search service", message="Search service not initialized"
        )

    return llamaindex_service.search_service, None


def validate_query_service(
    llamaindex_service: Any,
) -> Tuple[Optional[Any], Optional[JSONResponse]]:
    """
    Validate query service availability.

    Args:
        llamaindex_service: LlamaIndex service instance

    Returns:
        Tuple of (service, error_response) where one is None
    """
    if not llamaindex_service.query_service:
        return None, service_unavailable_response(
            "Query service", message="Query service not initialized"
        )

    return llamaindex_service.query_service, None


def validate_search_params(
    mode: str, limit: int, offset: int
) -> Optional[JSONResponse]:
    """
    Validate search parameters.

    Returns JSONResponse with error if validation fails, None if valid.
    """
    valid_modes = ["keyword", "semantic", "hybrid"]
    if mode not in valid_modes:
        return validation_error_response(
            f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}"
        )

    if limit < 1 or limit > 100:
        return validation_error_response("Limit must be between 1 and 100")

    if offset < 0:
        return validation_error_response("Offset must be non-negative")

    return None


def build_search_filters(
    mime_type: Optional[str],
    status: Optional[str],
    tags: Optional[str],
) -> Dict[str, Any]:
    """Build metadata filters from query parameters."""
    filters: Dict[str, Any] = {}

    if mime_type:
        filters["mime_type"] = mime_type
    if status:
        filters["status"] = status
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        if tag_list:
            filters["tags"] = tag_list

    return filters


async def execute_search(
    search_service,
    mode: str,
    query: str,
    limit: int,
    filters: Dict[str, Any],
):
    """
    Execute search based on mode.

    Returns Result from the appropriate search method.
    """
    if mode == "semantic":
        return await search_service.semantic_search(
            query=query,
            top_k=limit,
            similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
            filters=filters,
        )
    elif mode == "keyword":
        return await search_service.keyword_search(
            query=query,
            top_k=limit,
            filters=filters,
        )
    else:
        return await search_service.hybrid_search(
            query=query,
            top_k=limit,
            semantic_weight=DEFAULT_SEMANTIC_WEIGHT,
            filters=filters,
        )
