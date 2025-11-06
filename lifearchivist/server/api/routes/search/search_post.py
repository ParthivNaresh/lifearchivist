"""
Search documents POST endpoint.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ServiceUnavailableError,
    ValidationError,
)

router = APIRouter()

MIN_LIMIT = 1
MAX_LIMIT = 100
DEFAULT_LIMIT = 20
VALID_MODES = {"semantic", "keyword", "hybrid"}
DEFAULT_SIMILARITY_THRESHOLD = 0.3
DEFAULT_SEMANTIC_WEIGHT = 0.6


class SearchRequest(BaseModel):
    """Request to search documents."""

    query: str = Field(default="", description="Search query")
    mode: str = Field(default="semantic", description="Search mode")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    limit: int = Field(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description="Maximum results to return",
    )


class SearchDocumentsResponse(BaseModel):
    """Response from searching documents."""

    results: List[Dict[str, Any]] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results returned")
    mode: str = Field(..., description="Search mode used")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "document_id": "doc_123",
                        "title": "Example Document",
                        "score": 0.85,
                    }
                ],
                "count": 1,
                "mode": "semantic",
            }
        }


@router.post(
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
async def search_documents_post(request: SearchRequest) -> SearchDocumentsResponse:
    """
    Search documents via POST request with JSON body.

    Supports semantic, keyword, and hybrid search modes with advanced filtering.
    POST method allows complex filter objects.

    ## Request Body

    - **query**: Search query text (default: "")
    - **mode**: Search mode (semantic/keyword/hybrid, default: semantic)
    - **filters**: Filter object for metadata (default: {})
    - **limit**: Max results (1-100, default: 20)

    ## Response Fields

    - **results**: Array of search result objects
    - **count**: Number of results returned
    - **mode**: Search mode used

    ## Example Request (Semantic)

    ```json
    {
        "query": "artificial intelligence",
        "mode": "semantic",
        "limit": 10,
        "filters": {
            "mime_type": "application/pdf",
            "status": "completed"
        }
    }
    ```

    ## Example Request (Keyword)

    ```json
    {
        "query": "machine learning",
        "mode": "keyword",
        "limit": 20,
        "filters": {
            "tags": {"$in": ["research", "ai"]}
        }
    }
    ```

    ## Example Request (Hybrid)

    ```json
    {
        "query": "neural networks",
        "mode": "hybrid",
        "limit": 15,
        "filters": {}
    }
    ```

    ## Example Response

    ```json
    {
        "results": [
            {
                "document_id": "doc_123",
                "title": "AI Overview.pdf",
                "score": 0.92,
                "text": "Artificial intelligence is...",
                "metadata": {
                    "mime_type": "application/pdf",
                    "status": "completed"
                }
            }
        ],
        "count": 1,
        "mode": "semantic"
    }
    ```

    ## Search Modes

    ### Semantic Search
    - Vector similarity search
    - Best for meaning and concepts
    - Uses embeddings
    - Threshold: 0.3

    ### Keyword Search
    - BM25 keyword matching
    - Best for exact terms
    - Traditional full-text search
    - Fast and precise

    ### Hybrid Search
    - Combines semantic + keyword
    - Balanced approach
    - Semantic weight: 0.6
    - Keyword weight: 0.4

    ## Filters

    Complex filter objects supported:
    - **Equality**: `{"field": "value"}`
    - **In**: `{"field": {"$in": ["val1", "val2"]}}`
    - **Range**: `{"field": {"$gte": 0, "$lte": 100}}`
    - **Exists**: `{"field": {"$exists": true}}`

    ## Use Cases

    - Advanced document search
    - Complex filtering requirements
    - Programmatic search
    - API integrations
    - Batch operations

    ## Performance Notes

    - Semantic: Fast vector lookup
    - Keyword: Fast BM25 index
    - Hybrid: Combines both (slightly slower)
    - Filters applied efficiently

    ## Notes

    - Empty query returns all documents (filtered)
    - Limit enforced: 1-100 per request
    - Invalid mode returns 400 error
    - Results ordered by relevance
    """
    server = get_server()

    if request.mode not in VALID_MODES:
        raise ValidationError(
            f"Invalid search mode: {request.mode}. Must be one of: {', '.join(VALID_MODES)}"
        )

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    if not server.llamaindex_service.search_service:
        raise ServiceUnavailableError("Search service")

    try:
        search_service = server.llamaindex_service.search_service

        if request.mode == "semantic":
            result = await search_service.semantic_search(
                query=request.query,
                top_k=request.limit,
                similarity_threshold=DEFAULT_SIMILARITY_THRESHOLD,
                filters=request.filters,
            )
        elif request.mode == "keyword":
            result = await search_service.keyword_search(
                query=request.query,
                top_k=request.limit,
                filters=request.filters,
            )
        elif request.mode == "hybrid":
            result = await search_service.hybrid_search(
                query=request.query,
                top_k=request.limit,
                semantic_weight=DEFAULT_SEMANTIC_WEIGHT,
                filters=request.filters,
            )
        else:
            raise ValidationError(f"Invalid search mode: {request.mode}")

        if result.is_failure():
            raise InternalServerError("Search documents", Exception(result.error))

        return SearchDocumentsResponse(
            results=result.value,
            count=len(result.value),
            mode=request.mode,
        )

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Search documents", e) from e
