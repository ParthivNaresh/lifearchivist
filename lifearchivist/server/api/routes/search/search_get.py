"""
Search documents GET endpoint.
"""

from typing import Optional

from fastapi import APIRouter, Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ServiceUnavailableError,
    ValidationError,
)
from .constants import (
    DEFAULT_LIMIT,
    DEFAULT_OFFSET,
    MAX_LIMIT,
    MIN_LIMIT,
    VALID_MODES,
)
from .misc_models import SearchResult
from .response_models import SearchDocumentsResponse
from .utils import build_search_filters, execute_search

router = APIRouter()


@router.get(
    "/",
    response_model=SearchDocumentsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid search parameters",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid search mode: invalid"}
                }
            },
        },
        503: {
            "description": "Required service unavailable",
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
                    "example": {"detail": "Search documents failed: <error message>"}
                }
            },
        },
    },
)
async def search_documents_get(
    q: str = Query(default="", description="Search query"),
    mode: str = Query(
        default="semantic",
        description="Search mode: semantic, keyword, or hybrid",
    ),
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description="Maximum results to return",
    ),
    offset: int = Query(
        default=DEFAULT_OFFSET, ge=0, description="Number of results to skip"
    ),
    include_content: bool = Query(
        default=False, description="Include full document content"
    ),
    mime_type: Optional[str] = Query(None, description="Filter by MIME type"),
    status: Optional[str] = Query(None, description="Filter by document status"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
) -> SearchDocumentsResponse:
    """
    Search documents using query parameters.

    Supports semantic, keyword, and hybrid search with metadata filtering.
    Returns ranked results based on relevance.

    ## Query Parameters

    - **q**: Search query text
    - **mode**: Search mode (semantic/keyword/hybrid, default: semantic)
    - **limit**: Max results (1-100, default: 20)
    - **offset**: Results to skip (default: 0)
    - **include_content**: Include full content (default: false)
    - **mime_type**: Filter by MIME type
    - **status**: Filter by document status
    - **tags**: Filter by tags (comma-separated)

    ## Response Fields

    - **results**: Array of search result objects
    - **count**: Number of results returned
    - **mode**: Search mode used
    - **query**: Search query

    ## Example Request

    ```
    GET /search?q=artificial+intelligence&mode=semantic&limit=10
    ```

    ## Example Response

    ```json
    {
        "results": [
            {
                "document_id": "doc_123",
                "title": "AI Overview.pdf",
                "score": 0.92,
                "snippet": "Artificial intelligence is...",
                "metadata": {
                    "mime_type": "application/pdf",
                    "status": "completed"
                }
            },
            {
                "document_id": "doc_456",
                "title": "Machine Learning.pdf",
                "score": 0.87,
                "snippet": "ML is a subset of AI...",
                "metadata": {
                    "mime_type": "application/pdf",
                    "status": "completed"
                }
            }
        ],
        "count": 2,
        "mode": "semantic",
        "query": "artificial intelligence"
    }
    ```

    ## Search Modes

    - **semantic**: Vector similarity search (best for meaning)
    - **keyword**: BM25 keyword search (best for exact terms)
    - **hybrid**: Combines semantic + keyword (balanced)

    ## Filtering

    - **mime_type**: Filter by document type (e.g., "application/pdf")
    - **status**: Filter by processing status (e.g., "completed")
    - **tags**: Filter by tags (e.g., "work,important")

    ## Pagination

    Use limit and offset for pagination:
    - First page: `?limit=20&offset=0`
    - Second page: `?limit=20&offset=20`
    - Third page: `?limit=20&offset=40`

    ## Result Ordering

    - Results ordered by relevance score (highest first)
    - Score range: 0.0 (low) to 1.0 (high)
    - Semantic mode uses cosine similarity
    - Keyword mode uses BM25 score

    ## Use Cases

    - Full-text document search
    - Semantic similarity search
    - Filtered document discovery
    - Content exploration
    - Research queries

    ## Performance Notes

    - Semantic search: Fast vector lookup
    - Keyword search: Fast BM25 index
    - Hybrid search: Slightly slower (combines both)
    - Limit affects response time

    ## Notes

    - Empty query returns all documents (filtered)
    - Limit enforced: 1-100 per request
    - Offset must be non-negative
    - Results may be empty if no matches
    - include_content increases response size
    """
    server = get_server()

    if mode not in VALID_MODES:
        raise ValidationError(
            f"Invalid search mode: {mode}. Must be one of: {', '.join(VALID_MODES)}"
        )

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    if not server.llamaindex_service.search_service:
        raise ServiceUnavailableError("Search service")

    try:
        filters = build_search_filters(mime_type, status, tags)

        result = await execute_search(
            server.llamaindex_service.search_service, mode, q, limit, filters
        )

        if result.is_failure():
            raise InternalServerError("Search documents", Exception(result.error))

        search_results_raw = result.value
        if offset > 0:
            search_results_raw = search_results_raw[offset:]

        search_results = [
            SearchResult(
                document_id=r.get("document_id", ""),
                title=r.get("title", "Unknown Document"),
                score=r.get("score", 0.0),
                snippet=r.get("snippet"),
                metadata=r.get("metadata", {}),
            )
            for r in search_results_raw
        ]

        return SearchDocumentsResponse(
            results=search_results,
            count=len(search_results),
            mode=mode,
            query=q,
        )

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Search documents", e) from e
