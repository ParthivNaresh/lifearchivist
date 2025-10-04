"""
Debug endpoints for testing.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..dependencies import get_server

router = APIRouter(prefix="/api/debug", tags=["debug"])


class TestDocumentRequest(BaseModel):
    content: str = "This is a test document for debugging purposes."
    document_id: str = "test-doc-001"


@router.post("/test-llamaindex")
async def test_llamaindex_add(request: TestDocumentRequest):
    """Test adding a document directly to LlamaIndex."""
    server = get_server()

    try:
        # Get the LlamaIndex service
        llamaindex_service = server.llamaindex_service

        if not llamaindex_service:
            return {"error": "LlamaIndex service not available"}

        # Try to add a simple document
        metadata = {
            "test": True,
            "source": "debug_endpoint",
        }

        # add_document now returns Result
        result = await llamaindex_service.add_document(
            document_id=request.document_id, content=request.content, metadata=metadata
        )

        if result.is_failure():
            # Convert Result to HTTP response
            return JSONResponse(
                content=result.to_dict(), status_code=result.status_code
            )

        doc_info = result.unwrap()

        return {
            "success": True,
            **doc_info,  # Include all info from Result
            "metadata": metadata,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }


@router.get("/check-llamaindex")
async def check_llamaindex_status():
    """Check LlamaIndex service status."""
    server = get_server()

    try:
        llamaindex_service = server.llamaindex_service

        if not llamaindex_service:
            return {
                "status": "not_initialized",
                "error": "LlamaIndex service not available",
            }

        # Get document count (now returns Result)
        count_result = await llamaindex_service.get_document_count()
        document_count = count_result.unwrap_or(0)  # Use 0 if failed

        # Check various components
        status = {
            "status": "initialized",
            "has_index": llamaindex_service.index is not None,
            "has_query_engine": llamaindex_service.query_engine is not None,
            "has_qdrant_client": hasattr(llamaindex_service, "qdrant_client"),
            "document_count": document_count,
            "document_count_error": (
                count_result.error if count_result.is_failure() else None
            ),
        }

        # Check Qdrant connection
        if hasattr(llamaindex_service, "qdrant_client"):
            try:
                collection_info = llamaindex_service.qdrant_client.get_collection(
                    "lifearchivist"
                )
                status["qdrant_status"] = {
                    "connected": True,
                    "points_count": collection_info.points_count,
                    "vectors_count": (
                        collection_info.vectors_count
                        if hasattr(collection_info, "vectors_count")
                        else "N/A"
                    ),
                }
            except Exception as e:
                status["qdrant_status"] = {
                    "connected": False,
                    "error": str(e),
                }

        return status

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
        }
