"""
Utility functions for search endpoints.
"""

from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse


def validate_search_params(
    mode: str, limit: int, offset: int
) -> Optional[JSONResponse]:
    """
    Validate search parameters.

    Returns JSONResponse with error if validation fails, None if valid.
    """
    valid_modes = ["keyword", "semantic", "hybrid"]
    if mode not in valid_modes:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if limit < 1 or limit > 100:
        return JSONResponse(
            content={
                "success": False,
                "error": "Limit must be between 1 and 100",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if offset < 0:
        return JSONResponse(
            content={
                "success": False,
                "error": "Offset must be non-negative",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

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
            similarity_threshold=0.3,
            filters=filters,
        )
    elif mode == "keyword":
        return await search_service.keyword_search(
            query=query,
            top_k=limit,
            filters=filters,
        )
    else:  # hybrid
        return await search_service.hybrid_search(
            query=query,
            top_k=limit,
            semantic_weight=0.6,
            filters=filters,
        )
