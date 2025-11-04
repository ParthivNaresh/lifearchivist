"""
Search documents POST endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from lifearchivist.models import SearchRequest

from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    success_response,
    validation_error_response,
)
from .utils import validate_llamaindex_service, validate_search_service

router = APIRouter()


@router.post("/")
async def search_documents_post(request: SearchRequest):
    """
    Search documents via POST request.

    Supports semantic, keyword, and hybrid search modes with metadata filtering.
    """
    server = get_server()
    llamaindex_service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    search_service, error_response = validate_search_service(llamaindex_service)
    if error_response:
        return error_response

    assert llamaindex_service is not None
    assert search_service is not None

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
            return validation_error_response(f"Invalid search mode: {mode}")

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        return success_response(
            {
                "results": result.value,
                "count": len(result.value),
                "mode": mode,
            }
        )

    except Exception as e:
        return internal_error_response("Search documents", e)
