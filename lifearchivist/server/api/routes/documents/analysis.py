"""
Get document analysis endpoint.
"""

from typing import Any, Dict

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status
from pydantic import BaseModel

from ..shared import unwrap_result_or_error
from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)

router = APIRouter()


class DocumentAnalysisResponse(BaseModel):
    """Response containing comprehensive document analysis."""

    analysis: Dict[str, Any]

    class Config:
        extra = "allow"


@router.get(
    "/{document_id}/llamaindex-analysis",
    response_model=DocumentAnalysisResponse,
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
                        "detail": "Get document analysis failed: <error message>"
                    }
                }
            },
        },
    },
)
async def get_llamaindex_document_analysis(
    document_id: str = PathParam(..., description="Unique document identifier"),
) -> DocumentAnalysisResponse:
    """
    Get comprehensive LlamaIndex analysis for a document.

    Returns detailed metrics and statistics about document processing, chunking,
    embeddings, and storage in the vector database.

    ## Path Parameters

    - **document_id**: Unique identifier of the document to analyze

    ## Response Fields

    Response structure varies based on document type and processing, but typically includes:
    - **chunk_count**: Number of text chunks created
    - **embedding_stats**: Embedding model and dimension info
    - **storage_info**: Vector database storage details
    - **processing_metadata**: Processing timestamps and status
    - **token_counts**: Token usage statistics
    - **relationships**: Document relationships and references

    ## Example Response

    ```json
    {
        "document_id": "doc_123",
        "chunk_count": 15,
        "total_tokens": 3500,
        "embedding_stats": {
            "model": "BAAI/bge-small-en-v1.5",
            "dimension": 384
        },
        "storage_info": {
            "collection": "documents",
            "points": 15
        },
        "processing_metadata": {
            "processed_at": "2025-01-08T14:30:00Z",
            "status": "completed"
        }
    }
    ```

    ## Use Cases

    - Debug document processing issues
    - Verify chunking strategy effectiveness
    - Check embedding quality
    - Monitor storage usage
    - Analyze document structure
    - Troubleshoot search relevance

    ## Notes

    - Returns 404 if document doesn't exist
    - Analysis includes LlamaIndex-specific metrics
    - Useful for debugging and optimization
    - Response structure may vary by document type
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        result = await server.llamaindex_service.get_document_analysis(document_id)

        if result.is_failure():
            error_msg = result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Document", document_id)
            raise InternalServerError("Get document analysis", Exception(error_msg))

        analysis_result = unwrap_result_or_error(result, dict)
        return DocumentAnalysisResponse(analysis=analysis_result)

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Get document analysis", e) from e
