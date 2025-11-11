"""
Ingest document endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import InternalServerError, ValidationError
from .request_models import IngestRequest
from .response_models import IngestResponse

router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Missing required field: path"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Document ingestion failed: <error>"}
                }
            },
        },
    },
)
async def ingest_document(request: IngestRequest) -> IngestResponse:
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
            return IngestResponse(
                success=False,
                document_id=None,
                file_hash=None,
                status=None,
                metadata={},
                error=error_msg,
                error_type="ImportError",
            )

        result_data = result.get("result", {})
        return IngestResponse(
            success=True,
            document_id=result_data.get("file_id") or result_data.get("document_id"),
            file_hash=result_data.get("hash") or result_data.get("file_hash"),
            status=result_data.get("status"),
            metadata=result_data.get("metadata", {}),
            error=None,
            error_type=None,
        )

    except KeyError as e:
        raise ValidationError(f"Missing required field: {str(e)}") from e
    except Exception as e:
        raise InternalServerError("Document ingestion", e) from e
