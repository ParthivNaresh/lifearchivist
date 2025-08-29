"""
Search and query endpoints.
"""

import logging
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException

from lifearchivist.models import SearchRequest

from ..dependencies import get_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
async def search_documents_post(request: SearchRequest):
    """Search documents via POST request."""
    server = get_server()

    result = await server.execute_tool("index.search", request.dict())
    if result["success"]:
        return result["result"]
    else:
        error = result["error"] if result else "Search tool returned None"
        raise HTTPException(status_code=500, detail=error)


@router.get("/search")
async def search_documents_get(
    q: str = "",
    mode: str = "keyword",
    limit: int = 20,
    offset: int = 0,
    include_content: bool = False,
    mime_type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
):
    """Search documents using GET with query parameters and optional tag filtering."""
    server = get_server()

    try:
        # Prepare filters
        filters = {}
        if mime_type:
            filters["mime_type"] = mime_type
        if status:
            filters["status"] = status
        if tags:
            # Parse comma-separated tags
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            if tag_list:
                filters["tags"] = tag_list

        # Execute search using the search tool
        result = await server.execute_tool(
            "index.search",
            {
                "query": q,
                "mode": mode,
                "filters": filters,
                "limit": limit,
                "offset": offset,
                "include_content": include_content,
            },
        )

        if result.get("success"):
            return result["result"]
        else:
            raise HTTPException(
                status_code=500, detail=result.get("error", "Search failed")
            )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/ask")
async def ask_question(request: Dict[str, str]):
    """Ask a question using RAG Q&A."""
    server = get_server()

    try:
        question = request.get("question", "")
        context_limit = request.get("context_limit", 5)

        if not question:
            raise HTTPException(status_code=400, detail="Question is required")

        # Use the query agent for Q&A
        result = await server.query_agent.answer_question(
            question=question, context_limit=context_limit
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Q&A failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None
