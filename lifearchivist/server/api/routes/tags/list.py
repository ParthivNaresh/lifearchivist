"""
Get all tags endpoint.
"""

from fastapi import APIRouter, Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ServiceUnavailableError,
)
from .constants import (
    DEFAULT_LIMIT,
    DEFAULT_MIN_COUNT,
    MAX_LIMIT,
    MIN_LIMIT,
    MIN_MIN_COUNT,
)
from .response_models import TagsListResponse

router = APIRouter()


@router.get(
    "/",
    response_model=TagsListResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid parameters",
            "content": {
                "application/json": {
                    "example": {"detail": "min_count must be non-negative"}
                }
            },
        },
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {"example": {"detail": "Tag service not available"}}
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Retrieve tags failed: <error message>"}
                }
            },
        },
    },
)
async def get_all_tags(
    min_count: int = Query(
        default=DEFAULT_MIN_COUNT,
        ge=MIN_MIN_COUNT,
        description="Minimum number of documents a tag must have",
    ),
    limit: int = Query(
        default=DEFAULT_LIMIT,
        ge=MIN_LIMIT,
        le=MAX_LIMIT,
        description="Maximum number of tags to return",
    ),
) -> TagsListResponse:
    """
    Get all tags in the system with document counts.

    Returns list of tags extracted from document metadata with their usage counts.
    Supports filtering by minimum count and limiting results.

    ## Query Parameters

    - **min_count**: Minimum documents required (0+, default: 1)
    - **limit**: Maximum tags to return (1-1000, default: 100)

    ## Response Fields

    - **tags**: Array of tag objects with name, count, and metadata
    - **total**: Total number of tags returned
    - **min_count**: Applied minimum count filter
    - **limit**: Applied limit
    - **note**: Implementation status note

    ## Example Response

    ```json
    {
        "tags": [
            {
                "name": "AI",
                "count": 42,
                "metadata": {"category": "technology"}
            },
            {
                "name": "research",
                "count": 38,
                "metadata": {}
            }
        ],
        "total": 2,
        "min_count": 1,
        "limit": 100,
        "note": ""
    }
    ```

    ## Use Cases

    - Display tag cloud
    - Filter documents by tag
    - Show popular tags
    - Tag-based navigation
    - Content categorization

    ## Filtering

    - **min_count**: Only show tags with at least N documents
    - **limit**: Cap number of results for performance

    ## Sorting

    - Tags ordered by count (descending)
    - Most popular tags first

    ## Performance Notes

    - Fast metadata query
    - Cached where possible
    - Limit enforced for performance

    ## Notes

    - Returns 400 if parameters invalid
    - Returns 503 if service unavailable
    - Empty array if no tags found
    - Currently placeholder implementation
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("Tag service")

    try:
        return TagsListResponse(
            tags=[],
            total=0,
            min_count=min_count,
            limit=limit,
            note="Tag extraction not yet implemented. This is a placeholder.",
        )

    except ServiceUnavailableError:
        raise
    except Exception as e:
        raise InternalServerError("Retrieve tags", e) from e
