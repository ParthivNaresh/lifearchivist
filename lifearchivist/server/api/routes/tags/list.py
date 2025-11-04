"""
Get all tags endpoint.
"""

from typing import Optional

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    service_unavailable_response,
    success_response,
    validation_error_response,
)

router = APIRouter()


@router.get("/")
async def get_all_tags(
    min_count: Optional[int] = 1,
    limit: Optional[int] = 100,
):
    """
    Get all tags in the system with document counts.

    Args:
        min_count: Minimum number of documents a tag must have (default: 1)
        limit: Maximum number of tags to return (default: 100)

    Returns:
        List of tags with their document counts and metadata.

    Note: Currently returns empty list. Full implementation will:
    - Extract tags from document metadata
    - Count documents per tag
    - Support filtering and sorting
    """
    server = get_server()

    if not server.llamaindex_service:
        return service_unavailable_response("Tag service")

    if min_count is not None and min_count < 0:
        return validation_error_response("min_count must be non-negative")

    if limit is not None and (limit < 1 or limit > 1000):
        return validation_error_response("limit must be between 1 and 1000")

    try:
        return success_response(
            {
                "tags": [],
                "total": 0,
                "min_count": min_count,
                "limit": limit,
                "note": "Tag extraction not yet implemented. This is a placeholder.",
            }
        )

    except Exception as e:
        return internal_error_response("Retrieve tags", e)
