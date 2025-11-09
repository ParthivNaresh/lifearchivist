"""
Get document chunks endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import Query, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from .constants import DEFAULT_CHUNKS_LIMIT, MAX_CHUNKS_LIMIT, MIN_CHUNKS_LIMIT
from .misc_models import DocumentChunk
from .response_models import DocumentChunksResponse

router = APIRouter()


@router.get(
    "/{document_id}/llamaindex-chunks",
    response_model=DocumentChunksResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid pagination parameters",
            "content": {
                "application/json": {
                    "example": {"detail": "Limit must be between 1 and 100"}
                }
            },
        },
        404: {
            "description": "Document not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Document not found: invalid-id"}
                }
            },
        },
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
                    "example": {"detail": "Get document chunks failed: <error message>"}
                }
            },
        },
    },
)
async def get_llamaindex_document_chunks(
    document_id: str = PathParam(..., description="Unique document identifier"),
    limit: int = Query(
        default=DEFAULT_CHUNKS_LIMIT,
        ge=MIN_CHUNKS_LIMIT,
        le=MAX_CHUNKS_LIMIT,
        description="Maximum number of chunks to return",
    ),
    offset: int = Query(
        default=0, ge=0, description="Number of chunks to skip for pagination"
    ),
) -> DocumentChunksResponse:
    """
    Get paginated text chunks for a document from LlamaIndex.

    Returns the text chunks created during document processing, including their
    content, metadata, and embedding information.

    ## Path Parameters

    - **document_id**: Unique identifier of the document

    ## Query Parameters

    - **limit**: Maximum chunks to return (1-100, default: 20)
    - **offset**: Number of chunks to skip (default: 0)

    ## Response Fields

    - **document_id**: Document identifier
    - **chunks**: Array of chunk objects, each containing:
      - chunk_id: Unique chunk identifier
      - text: Chunk text content
      - metadata: Chunk metadata (page numbers, positions, etc.)
      - embedding_info: Embedding details (optional)
    - **total**: Total number of chunks for this document
    - **limit**: Applied limit
    - **offset**: Applied offset

    ## Example Response

    ```json
    {
        "document_id": "doc_123",
        "chunks": [
            {
                "chunk_id": "chunk_1",
                "text": "This is the first chunk of text...",
                "metadata": {
                    "page": 1,
                    "position": 0
                },
                "token_count": 150
            },
            {
                "chunk_id": "chunk_2",
                "text": "This is the second chunk...",
                "metadata": {
                    "page": 1,
                    "position": 1
                },
                "token_count": 145
            }
        ],
        "total": 15,
        "limit": 20,
        "offset": 0
    }
    ```

    ## Use Cases

    - View document chunking results
    - Debug chunking strategy
    - Verify chunk quality
    - Analyze chunk boundaries
    - Review metadata extraction
    - Inspect embedding coverage

    ## Pagination

    Use limit and offset for pagination:
    - First page: `?limit=20&offset=0`
    - Second page: `?limit=20&offset=20`
    - Third page: `?limit=20&offset=40`

    ## Notes

    - Returns 404 if document doesn't exist
    - Chunks ordered by creation/position
    - Limit enforced: 1-100 chunks per request
    - Offset must be non-negative
    - Total indicates full chunk count
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        result = await server.llamaindex_service.get_document_chunks(
            document_id=document_id, limit=limit, offset=offset
        )

        if result.is_failure():
            error_msg = result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Document", document_id)
            raise InternalServerError("Get document chunks", Exception(error_msg))

        data = result.value

        chunks = [DocumentChunk(**chunk) for chunk in data.get("chunks", [])]

        return DocumentChunksResponse(
            document_id=data["document_id"],
            chunks=chunks,
            total=data["total"],
            limit=data["limit"],
            offset=data["offset"],
        )

    except (ServiceUnavailableError, ResourceNotFoundError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Get document chunks", e) from e
