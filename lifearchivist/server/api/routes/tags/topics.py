"""
Get topic landscape endpoint.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/topics")
async def get_topic_landscape(
    min_documents: Optional[int] = 1,
    max_topics: Optional[int] = 50,
):
    """
    Get aggregated topic data for the landscape visualization.

    Args:
        min_documents: Minimum documents required for a topic (default: 1)
        max_topics: Maximum number of topics to return (default: 50)

    Returns:
        Topic hierarchy with document counts and relationships.

    Note: Currently returns empty list. Full implementation will:
    - Extract themes and subthemes from documents
    - Build topic hierarchy
    - Calculate document distributions
    - Support interactive visualization
    """
    server = get_server()

    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Topic service not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    if min_documents is not None and min_documents < 1:
        raise HTTPException(status_code=400, detail="min_documents must be at least 1")

    if max_topics is not None and (max_topics < 1 or max_topics > 200):
        raise HTTPException(
            status_code=400, detail="max_topics must be between 1 and 200"
        )

    try:
        return {
            "success": True,
            "topics": [],
            "total_topics": 0,
            "total_documents": 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "min_documents": min_documents,
            "max_topics": max_topics,
            "note": "Topic extraction not yet implemented. This is a placeholder.",
        }

    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Failed to retrieve topics: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
