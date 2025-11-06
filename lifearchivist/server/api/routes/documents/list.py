"""
List documents endpoint.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query, status
from pydantic import BaseModel, Field

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ServiceUnavailableError
from .utils import format_document_for_ui

router = APIRouter()

MIN_LIMIT = 1
MAX_LIMIT = 10000
DEFAULT_LIMIT = 20
DEFAULT_OFFSET = 0
COUNT_QUERY_LIMIT = 10000


class DocumentListResponse(BaseModel):
    """Response containing list of documents."""

    documents: List[Dict[str, Any]] = Field(..., description="List of documents")
    total: int = Field(..., description="Number of documents returned")
    limit: int = Field(..., description="Applied limit")
    offset: int = Field(..., description="Applied offset")

    class Config:
        json_schema_extra = {
            "example": {
                "documents": [
                    {
                        "document_id": "doc_123",
                        "title": "Example Document",
                        "status": "completed",
                    }
                ],
                "total": 1,
                "limit": 20,
                "offset": 0,
            }
        }


class DocumentCountResponse(BaseModel):
    """Response containing document count."""

    total: int = Field(..., description="Total number of documents")
    filters: Dict[str, Any] = Field(..., description="Applied filters")

    class Config:
        json_schema_extra = {
            "example": {"total": 150, "filters": {"status": "completed"}}
        }


@router.get(
    "/",
    response_model=None,
    status_code=status.HTTP_200_OK,
    responses={
        503: {
            "description": "LlamaIndex service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "LlamaIndex service not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "List documents failed: <error message>"}
                }
            },
        },
    },
)
async def list_documents(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by document status"
    ),
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description="Maximum documents to return",
    ),
    offset: int = Query(
        default=DEFAULT_OFFSET, ge=0, description="Number of documents to skip"
    ),
    count_only: bool = Query(
        default=False, description="Return only count, not documents"
    ),
):
    """
    List documents with filtering and pagination.

    Returns documents from the vector index with UI-compatible formatting.
    Supports filtering by status and optional count-only mode.

    ## Query Parameters

    - **status**: Filter by document status (e.g., "completed", "processing")
    - **limit**: Maximum documents to return (1-100, default: 20)
    - **offset**: Number of documents to skip (default: 0)
    - **count_only**: Return only count without documents (default: false)

    ## Response (Normal Mode)

    ```json
    {
        "documents": [
            {
                "document_id": "doc_123",
                "title": "Example Document.pdf",
                "status": "completed",
                "file_hash": "abc123",
                "created_at": "2025-01-08T14:30:00Z"
            }
        ],
        "total": 1,
        "limit": 20,
        "offset": 0
    }
    ```

    ## Response (Count Only Mode)

    ```json
    {
        "total": 150,
        "filters": {"status": "completed"}
    }
    ```

    ## Use Cases

    - Browse all documents
    - Filter by processing status
    - Paginate through large collections
    - Get quick document counts
    - Dashboard document lists

    ## Filtering

    - **status**: Filter by processing status
      - "completed": Fully processed documents
      - "processing": Currently being processed
      - "failed": Processing failed
      - No filter: All documents

    ## Pagination

    - Use limit and offset for pagination
    - First page: `?limit=20&offset=0`
    - Second page: `?limit=20&offset=20`
    - Third page: `?limit=20&offset=40`

    ## Count Only Mode

    - Set `count_only=true` to get just the count
    - Faster than fetching all documents
    - Useful for pagination UI
    - Returns total matching filter

    ## Notes

    - Documents formatted for UI display
    - Limit enforced: 1-100 per request
    - Offset must be non-negative
    - Count mode queries up to 10,000 docs
    - Empty array if no documents found
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        filters = {}
        if status_filter:
            filters["status"] = status_filter

        if count_only:
            all_docs_result = (
                await server.llamaindex_service.query_documents_by_metadata(
                    filters=filters,
                    limit=COUNT_QUERY_LIMIT,
                    offset=DEFAULT_OFFSET,
                )
            )

            if all_docs_result.is_failure():
                raise InternalServerError(
                    "Query documents", Exception(all_docs_result.error)
                )

            all_docs = all_docs_result.value or []
            return DocumentCountResponse(total=len(all_docs), filters=filters)

        raw_documents_result = (
            await server.llamaindex_service.query_documents_by_metadata(
                filters=filters, limit=limit, offset=offset
            )
        )

        if raw_documents_result.is_failure():
            raise InternalServerError(
                "Query documents", Exception(raw_documents_result.error)
            )

        raw_documents = raw_documents_result.value or []
        formatted_documents = [format_document_for_ui(doc) for doc in raw_documents]

        return DocumentListResponse(
            documents=formatted_documents,
            total=len(formatted_documents),
            limit=limit,
            offset=offset,
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("List documents", e) from e
