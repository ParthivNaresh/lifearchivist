"""
List documents endpoint.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from ..constants import (
    DocumentConstants,
    ErrorMessages,
    HTTPStatus,
    PaginationDefaults,
    ServiceNames,
)
from ..shared.dependencies import get_server
from ..utils import extract_result_value, unwrap_result_to_json_response
from .utils import format_document_for_ui, validate_pagination

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

    if not server.llamaindex_service:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=ErrorMessages.SERVICE_NOT_AVAILABLE.format(
                service=ServiceNames.LLAMAINDEX
            ),
        )

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
            all_docs_result = (
                await server.llamaindex_service.query_documents_by_metadata(
                    filters=filters,
                    limit=DocumentConstants.COUNT_QUERY_LIMIT,
                    offset=PaginationDefaults.DEFAULT_OFFSET,
                )
            )
            error_response = unwrap_result_to_json_response(all_docs_result)
            if error_response:
                return error_response

            all_docs = extract_result_value(all_docs_result, list, [])
            return {"total": len(all_docs), "filters": filters}

        raw_documents_result = (
            await server.llamaindex_service.query_documents_by_metadata(
                filters=filters, limit=limit, offset=offset
            )
        )

        error_response = unwrap_result_to_json_response(raw_documents_result)
        if error_response:
            return error_response

        raw_documents = extract_result_value(raw_documents_result, list, [])
        formatted_documents = [format_document_for_ui(doc) for doc in raw_documents]

        return {
            "success": True,
            "documents": formatted_documents,
            "total": len(formatted_documents),
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None
