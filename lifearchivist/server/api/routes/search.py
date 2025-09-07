"""
Search and query endpoints.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from lifearchivist.models import SearchRequest
from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
async def search_documents_post(request: SearchRequest):
    """Search documents via POST request."""
    server = get_server()
    try:
        result = await server.execute_tool("index.search", request.dict())

        if result.get("success"):
            search_result = result["result"]
            return search_result
        else:
            error = result.get("error", "Search tool returned None")
            raise HTTPException(status_code=500, detail=error)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


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

    # Validate parameters
    valid_modes = ["keyword", "semantic", "hybrid"]
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}",
        )

    if limit < 1 or limit > 100:
        raise HTTPException(
            status_code=400, detail="Limit must be between 1 and 100"
        )

    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative")

    try:
        # Prepare filters
        filters: Dict[str, Any] = {}
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
            search_result = result["result"]
            return search_result
        else:
            error = result.get("error", "Search failed")
            raise HTTPException(status_code=500, detail=error)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/ask")
async def ask_question(request: Dict[str, Any]):
    """Ask a question using RAG Q&A."""
    server = get_server()

    question = request.get("question", "").strip()
    context_limit = request.get("context_limit", 5)

    # Validate question
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    if len(question) < 3:
        raise HTTPException(
            status_code=400, detail="Question must be at least 3 characters long"
        )

    # Convert and validate context_limit
    if isinstance(context_limit, str):
        try:
            context_limit = int(context_limit)
        except ValueError:
            raise HTTPException(
                status_code=400, detail="context_limit must be a number"
            ) from None

    if context_limit < 1 or context_limit > 20:
        raise HTTPException(
            status_code=400, detail="context_limit must be between 1 and 20"
        )

    try:
        # Use the llamaindex.query tool directly instead of query_agent
        result = await server.execute_tool(
            "llamaindex.query",
            {
                "question": question,
                "similarity_top_k": context_limit,
                "response_mode": "tree_summarize",
            },
        )

        if result.get("success"):
            # Transform the result to match the expected format for the UI
            tool_result = result["result"]
            answer = tool_result.get("answer", "")
            confidence = tool_result.get("confidence", 0.0)
            sources = tool_result.get("sources", [])

            # Create citations with proper validation
            citations = []
            for source in sources:
                snippet = source.get("text", "")[:200] if source.get("text") else ""
                citations.append(
                    {
                        "doc_id": source.get("document_id", ""),
                        "title": source.get("title", "Unknown Document"),
                        "snippet": snippet,
                        "score": source.get("score", 0.0),
                    }
                )

            final_response = {
                "answer": answer,
                "confidence": confidence,
                "citations": citations,
                "method": tool_result.get("method", "llamaindex_tool"),
                "context_length": len(citations),
            }
            return final_response
        else:
            error = result.get("error", "Q&A tool failed")
            raise HTTPException(status_code=500, detail=error)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
