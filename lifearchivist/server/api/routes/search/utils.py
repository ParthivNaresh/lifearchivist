"""
Utility functions for search endpoints.
"""

from typing import Any, Dict, Optional

from .constants import DEFAULT_SEMANTIC_WEIGHT, DEFAULT_SIMILARITY_THRESHOLD


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
