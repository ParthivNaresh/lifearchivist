"""
Search and query endpoints with Result type unwrapping.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lifearchivist.models import SearchRequest

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["search"])


def _validate_search_params(
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


def _build_search_filters(
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


async def _execute_search(
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


@router.post("/search")
async def search_documents_post(request: SearchRequest):
    """
    Search documents via POST request.

    Supports semantic, keyword, and hybrid search modes with metadata filtering.
    """
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

    search_service = server.llamaindex_service.search_service
    if not search_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Search service not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        # Extract parameters from request
        query = request.query or ""
        mode = request.mode or "semantic"
        filters = request.filters or {}
        limit = request.limit or 20

        # Call appropriate search method based on mode
        if mode == "semantic":
            result = await search_service.semantic_search(
                query=query,
                top_k=limit,
                similarity_threshold=0.3,
                filters=filters,
            )
        elif mode == "keyword":
            result = await search_service.keyword_search(
                query=query,
                top_k=limit,
                filters=filters,
            )
        elif mode == "hybrid":
            result = await search_service.hybrid_search(
                query=query,
                top_k=limit,
                semantic_weight=0.6,
                filters=filters,
            )
        else:
            return JSONResponse(
                content={
                    "success": False,
                    "error": f"Invalid search mode: {mode}",
                    "error_type": "ValidationError",
                },
                status_code=400,
            )

        # Unwrap Result
        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        # Return search results
        return {
            "success": True,
            "results": result.value,
            "count": len(result.value),
            "mode": mode,
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Search failed: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.get("/search")
async def search_documents_get(
    q: str = "",
    mode: str = "semantic",
    limit: int = 20,
    offset: int = 0,
    include_content: bool = False,
    mime_type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
):
    """
    Search documents using GET with query parameters.

    Supports semantic, keyword, and hybrid search with metadata filtering.
    """
    server = get_server()

    # Validate parameters using helper
    validation_error = _validate_search_params(mode, limit, offset)
    if validation_error:
        return validation_error

    # Check service availability
    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Search service not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    search_service = server.llamaindex_service.search_service
    if not search_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Search service not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        # Build filters using helper
        filters = _build_search_filters(mime_type, status, tags)

        # Execute search using helper
        result = await _execute_search(search_service, mode, q, limit, filters)

        # Unwrap Result
        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        # Apply offset manually (service doesn't support it yet)
        search_results = result.value
        if offset > 0:
            search_results = search_results[offset:]

        # Return search results
        return {
            "success": True,
            "results": search_results,
            "count": len(search_results),
            "mode": mode,
            "query": q,
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Search failed: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )


@router.post("/ask")
async def ask_question(request: Dict[str, Any]):
    """
    Ask a question using RAG Q&A.

    Uses the query service to retrieve relevant context and generate answers.
    """
    server = get_server()

    question = request.get("question", "").strip()
    context_limit = request.get("context_limit", 5)
    filters = request.get("filters")

    # Validate question
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

    # Check service availability
    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Q&A service not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    query_service = server.llamaindex_service.query_service
    if not query_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Query service not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    try:
        # Call query service directly (returns Result)
        result = await query_service.query(
            question=question,
            similarity_top_k=context_limit,
            response_mode="tree_summarize",
            filters=filters,
        )

        # Unwrap Result
        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        # Extract query response
        query_response = result.value
        answer = query_response.get("answer", "")
        sources = query_response.get("sources", [])
        confidence = query_response.get("confidence_score", 0.0)

        # Create citations with proper validation
        citations = []
        for source in sources:
            snippet = source.get("text", "")[:200] if source.get("text") else ""
            citations.append(
                {
                    "doc_id": source.get("document_id", ""),
                    "title": source.get("metadata", {}).get(
                        "title", "Unknown Document"
                    ),
                    "snippet": snippet,
                    "score": source.get("score", 0.0),
                }
            )

        return {
            "success": True,
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
            "method": query_response.get("method", "llamaindex_rag"),
            "context_length": len(citations),
            "statistics": query_response.get("statistics", {}),
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Q&A failed: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
