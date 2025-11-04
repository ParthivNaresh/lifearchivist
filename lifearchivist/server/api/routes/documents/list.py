"""
List documents endpoint.
"""

from typing import Optional

from fastapi import APIRouter

from ..constants import DocumentConstants, PaginationDefaults
from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from ..shared.utils import extract_result_value, unwrap_result_to_json_response
from .utils import (
    format_document_for_ui,
    validate_llamaindex_service,
    validate_pagination,
)

router = APIRouter()


@router.get("/")
async def list_documents(
    status: Optional[str] = None,
    limit: int = PaginationDefaults.DEFAULT_LIMIT,
    offset: int = PaginationDefaults.DEFAULT_OFFSET,
    count_only: bool = False,
):
    """
    List documents from LlamaIndex service with UI-compatible formatting.

    Supports filtering by status and pagination.
    """
    server = get_server()
    service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        limit, offset = validate_pagination(
            limit,
            offset,
            PaginationDefaults.MAX_LIMIT,
            PaginationDefaults.MIN_LIMIT,
            PaginationDefaults.DEFAULT_LIMIT,
            PaginationDefaults.DEFAULT_OFFSET,
        )

        filters = {}
        if status:
            filters["status"] = status

        if count_only:
            all_docs_result = await service.query_documents_by_metadata(
                filters=filters,
                limit=DocumentConstants.COUNT_QUERY_LIMIT,
                offset=PaginationDefaults.DEFAULT_OFFSET,
            )
            error_response = unwrap_result_to_json_response(all_docs_result)
            if error_response:
                return error_response

            all_docs = extract_result_value(all_docs_result, list, [])
            return {"total": len(all_docs), "filters": filters}

        raw_documents_result = await service.query_documents_by_metadata(
            filters=filters, limit=limit, offset=offset
        )

        error_response = unwrap_result_to_json_response(raw_documents_result)
        if error_response:
            return error_response

        raw_documents = extract_result_value(raw_documents_result, list, [])
        formatted_documents = [format_document_for_ui(doc) for doc in raw_documents]

        return success_response(
            {
                "documents": formatted_documents,
                "total": len(formatted_documents),
                "limit": limit,
                "offset": offset,
            }
        )

    except Exception as e:
        return internal_error_response("List documents", e)
