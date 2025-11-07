"""
Ingest document endpoint.
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from .request_models import IngestRequest

router = APIRouter()


@router.post("/ingest")
async def ingest_document(request: IngestRequest):
    """
    Ingest a document from a file path.

    Processes a document from the local filesystem:
    - Validates file exists and is readable
    - Calculates file hash for deduplication
    - Extracts text content
    - Generates embeddings
    - Stores in vector database

    Supports progress tracking via session_id.
    """
    server = get_server()

    try:
        params = request.model_dump()
        session_id = params.pop("session_id", None)

        if session_id:
            params["session_id"] = session_id

        result = await server.execute_tool("file.import", params)

        if not result.get("success"):
            error_msg = result.get("error", "Import failed")
            return JSONResponse(
                content={
                    "success": False,
                    "error": error_msg,
                    "error_type": "ImportError",
                },
                status_code=500,
            )

        return {"success": True, **result["result"]}

    except KeyError as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Missing required field: {str(e)}",
                "error_type": "ValidationError",
            },
            status_code=400,
        )
    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Document ingestion failed: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
