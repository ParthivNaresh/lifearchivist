"""
Get document neighbors endpoint.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..constants import (
    DocumentConstants,
    ErrorMessages,
    HTTPStatus,
    ServiceNames,
    ValidationMessages,
)
from ..shared.dependencies import get_server

router = APIRouter()


@router.get("/{document_id}/llamaindex-neighbors")
async def get_llamaindex_document_neighbors(
    document_id: str, top_k: int = DocumentConstants.NEIGHBORS_DEFAULT_TOP_K
):
    """
    Get semantically similar documents for a given document.

    Uses vector similarity to find related documents.
    """
    server = get_server()

    if not server.llamaindex_service:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=ErrorMessages.SERVICE_NOT_AVAILABLE.format(
                service=ServiceNames.LLAMAINDEX
            ),
        )

    if (
        top_k < DocumentConstants.NEIGHBORS_MIN_TOP_K
        or top_k > DocumentConstants.NEIGHBORS_MAX_TOP_K
    ):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ValidationMessages.TOP_K_RANGE.format(
                min=DocumentConstants.NEIGHBORS_MIN_TOP_K,
                max=DocumentConstants.NEIGHBORS_MAX_TOP_K,
            ),
        )

    try:
        result = await server.llamaindex_service.get_document_neighbors(
            document_id=document_id, top_k=top_k
        )

        if hasattr(result, "is_failure"):
            if result.is_failure():
                return JSONResponse(
                    content=result.to_dict(),
                    status_code=result.status_code,
                )
            return result.value

        if isinstance(result, dict) and "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND, detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=result["error"]
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None
