"""
Search documents GET endpoint.
"""

from typing import Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from .utils import (
    build_search_filters,
    execute_search,
    validate_llamaindex_service,
    validate_search_params,
    validate_search_service,
)

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

    llamaindex_service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    search_service, error_response = validate_search_service(llamaindex_service)
    if error_response:
        return error_response

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

        return success_response(
            {
                "results": search_results,
                "count": len(search_results),
                "mode": mode,
                "query": q,
            }
        )

    except Exception as e:
        return internal_error_response("Search documents", e)
