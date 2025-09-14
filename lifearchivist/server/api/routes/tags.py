"""
Tag management endpoints.
"""

from fastapi import APIRouter, HTTPException

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["tags"])


@router.get("/tags")
async def get_all_tags():
    """Get all tags in the system with document counts."""
    _ = get_server()

    try:
        # Since we no longer have database, return empty list for now
        # TODO: Implement tag extraction from LlamaIndex metadata
        return {"tags": [], "total": 0}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/topics")
async def get_topic_landscape():
    """Get aggregated topic data for the landscape visualization."""
    _ = get_server()

    try:
        # Since we no longer have database, return empty topics for now
        # TODO: Implement topic extraction from LlamaIndex metadata
        return {
            "topics": [],
            "total_topics": 0,
            "generated_at": "2024-01-01T00:00:00",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
