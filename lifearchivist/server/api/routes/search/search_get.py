"""
Search documents GET endpoint.
"""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from .utils import build_search_filters, execute_search, validate_search_params

router = APIRouter()


@router.get("/")
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

    validation_error = validate_search_params(mode, limit, offset)
    if validation_error:
        return validation_error

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
        filters = build_search_filters(mime_type, status, tags)

        result = await execute_search(search_service, mode, q, limit, filters)

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        search_results = result.value
        if offset > 0:
            search_results = search_results[offset:]

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
