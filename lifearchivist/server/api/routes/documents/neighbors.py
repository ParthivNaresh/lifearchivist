"""
Get document neighbors endpoint.
"""

from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import Query, status
from pydantic import BaseModel, Field

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)

router = APIRouter()

MIN_TOP_K = 1
MAX_TOP_K = 50
DEFAULT_TOP_K = 10


class NeighborDocument(BaseModel):
    """Information about a neighboring document."""

    class Config:
        extra = "allow"


class DocumentNeighborsResponse(BaseModel):
    """Response containing similar documents."""

    document_id: str = Field(..., description="Source document ID")
    neighbors: List[Dict[str, Any]] = Field(
        ..., description="List of similar documents"
    )
    top_k: int = Field(..., description="Number of neighbors requested")

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "doc_123",
                "neighbors": [
                    {
                        "document_id": "doc_456",
                        "title": "Similar Document",
                        "similarity_score": 0.85,
                    }
                ],
                "top_k": 10,
            }
        }


@router.get(
    "/{document_id}/llamaindex-neighbors",
    response_model=DocumentNeighborsResponse,
    status_code=status.HTTP_200_OK,
    responses={
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
                    "example": {
                        "detail": "Get document neighbors failed: <error message>"
                    }
                }
            },
        },
    },
)
async def get_llamaindex_document_neighbors(
    document_id: str = PathParam(..., description="Unique document identifier"),
    top_k: int = Query(
        default=DEFAULT_TOP_K,
        ge=MIN_TOP_K,
        le=MAX_TOP_K,
        description="Number of similar documents to return",
    ),
) -> DocumentNeighborsResponse:
    """
    Get semantically similar documents using vector similarity.

    Finds documents with similar content based on embedding vectors in the
    vector database. Useful for discovering related content.

    ## Path Parameters

    - **document_id**: Unique identifier of the source document

    ## Query Parameters

    - **top_k**: Number of similar documents to return (1-50, default: 10)

    ## Response Fields

    - **document_id**: Source document ID
    - **neighbors**: Array of similar documents, each containing:
      - document_id: Neighbor document ID
      - title: Document title
      - similarity_score: Similarity score (0.0-1.0)
      - metadata: Additional document metadata
    - **top_k**: Number of neighbors requested

    ## Example Response

    ```json
    {
        "document_id": "doc_123",
        "neighbors": [
            {
                "document_id": "doc_456",
                "title": "Related Document.pdf",
                "similarity_score": 0.85,
                "file_hash": "def789",
                "status": "completed"
            },
            {
                "document_id": "doc_789",
                "title": "Another Similar Doc.pdf",
                "similarity_score": 0.78,
                "file_hash": "ghi012",
                "status": "completed"
            }
        ],
        "top_k": 10
    }
    ```

    ## Use Cases

    - Find related documents
    - Discover similar content
    - Build recommendation systems
    - Content exploration
    - Duplicate detection
    - Research assistance

    ## Similarity Scoring

    - Scores range from 0.0 (dissimilar) to 1.0 (identical)
    - Based on cosine similarity of embeddings
    - Higher scores indicate more similar content
    - Ordered by similarity (highest first)

    ## Performance Notes

    - Fast vector similarity search
    - Scales well with large document collections
    - Uses approximate nearest neighbor (ANN)
    - Results cached in vector database

    ## Notes

    - Returns 404 if source document doesn't exist
    - Neighbors exclude the source document itself
    - Empty array if no similar documents found
    - Top_k enforced: 1-50 neighbors
    - Similarity depends on embedding quality
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        result = await server.llamaindex_service.get_document_neighbors(
            document_id=document_id, top_k=top_k
        )

        if hasattr(result, "is_failure") and result.is_failure():
            error_msg = result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Document", document_id)
            raise InternalServerError("Get document neighbors", Exception(error_msg))

        if isinstance(result, dict):
            if "error" in result:
                error_msg = result["error"]
                if "not found" in error_msg.lower():
                    raise ResourceNotFoundError("Document", document_id)
                raise InternalServerError(
                    "Get document neighbors", RuntimeError(error_msg)
                )

            return DocumentNeighborsResponse(**result)

        if hasattr(result, "value"):
            return DocumentNeighborsResponse(**result.value)

        return DocumentNeighborsResponse(
            document_id=document_id, neighbors=result, top_k=top_k
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Get document neighbors", e) from e
