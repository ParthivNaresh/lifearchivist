"""
Search and query endpoints.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lifearchivist.models import SearchRequest

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
async def search_documents_post(request: SearchRequest):
    """Search documents via POST request."""
    server = get_server()

    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Search service not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        result = await server.execute_tool("index.search", request.dict())

        if not result.get("success"):
            error = result.get("error", "Search failed")
            return JSONResponse(
                content={"success": False, "error": error, "error_type": "SearchError"},
                status_code=500,
            )

        return result["result"]

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )


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

    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Search service not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        # Prepare filters
        filters: Dict[str, Any] = {}
        if mime_type:
            filters["mime_type"] = mime_type
        if status:
            filters["status"] = status
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            if tag_list:
                filters["tags"] = tag_list

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

        if not result.get("success"):
            error = result.get("error", "Search failed")
            return JSONResponse(
                content={"success": False, "error": error, "error_type": "SearchError"},
                status_code=500,
            )

        return result["result"]

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )


@router.post("/ask")
async def ask_question(request: Dict[str, Any]):
    """Ask a question using RAG Q&A."""
    server = get_server()

    question = request.get("question", "").strip()
    context_limit = request.get("context_limit", 5)

    if not question:
        return JSONResponse(
            content={
                "success": False,
                "error": "Question is required",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if len(question) < 3:
        return JSONResponse(
            content={
                "success": False,
                "error": "Question must be at least 3 characters long",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    # Convert and validate context_limit
    if isinstance(context_limit, str):
        try:
            context_limit = int(context_limit)
        except ValueError:
            return JSONResponse(
                content={
                    "success": False,
                    "error": "context_limit must be a number",
                    "error_type": "ValidationError",
                },
                status_code=400,
            )

    if context_limit < 1 or context_limit > 20:
        return JSONResponse(
            content={
                "success": False,
                "error": "context_limit must be between 1 and 20",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Q&A service not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        result = await server.execute_tool(
            "llamaindex.query",
            {
                "question": question,
                "similarity_top_k": context_limit,
                "response_mode": "tree_summarize",
            },
        )

        if not result.get("success"):
            error = result.get("error", "Q&A tool failed")
            return JSONResponse(
                content={"success": False, "error": error, "error_type": "QueryError"},
                status_code=500,
            )

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

        return {
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
            "method": tool_result.get("method", "llamaindex_tool"),
            "context_length": len(citations),
        }

    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e), "error_type": type(e).__name__},
            status_code=500,
        )
