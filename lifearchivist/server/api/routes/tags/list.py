"""
Get all tags endpoint.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

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
        return JSONResponse(
            content={
                "success": False,
                "error": "Tag service not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    if min_count is not None and min_count < 0:
        raise HTTPException(status_code=400, detail="min_count must be non-negative")

    if limit is not None and (limit < 1 or limit > 1000):
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")

    try:
        return {
            "success": True,
            "tags": [],
            "total": 0,
            "min_count": min_count,
            "limit": limit,
            "note": "Tag extraction not yet implemented. This is a placeholder.",
        }

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to retrieve tags: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
