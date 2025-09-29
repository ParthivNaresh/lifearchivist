"""
Debug endpoints for testing.
"""

from fastapi import APIRouter
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

        success = await llamaindex_service.add_document(
            document_id=request.document_id, content=request.content, metadata=metadata
        )

        return {
            "success": success,
            "document_id": request.document_id,
            "content_length": len(request.content),
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

        # Check various components
        status = {
            "status": "initialized",
            "has_index": llamaindex_service.index is not None,
            "has_query_engine": llamaindex_service.query_engine is not None,
            "has_qdrant_client": hasattr(llamaindex_service, "qdrant_client"),
            "document_count": await llamaindex_service.get_document_count(),
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
