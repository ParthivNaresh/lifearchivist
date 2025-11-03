"""
Search documents POST endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lifearchivist.models import SearchRequest

from ..shared.dependencies import get_server

router = APIRouter()


@router.post("/")
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
        query = request.query or ""
        mode = request.mode or "semantic"
        filters = request.filters or {}
        limit = request.limit or 20

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

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

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
