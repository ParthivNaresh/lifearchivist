"""
Get document analysis endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..constants import (
    ErrorMessages,
    HTTPStatus,
    ServiceNames,
)
from ..shared.dependencies import get_server
from ..utils import unwrap_result_to_json_response

router = APIRouter()


@router.get("/{document_id}/llamaindex-analysis")
async def get_llamaindex_document_analysis(document_id: str):
    """
    Get comprehensive LlamaIndex analysis for a document.

    Returns chunk statistics, processing info, and storage details.
    """
    server = get_server()

    if not server.llamaindex_service:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=ErrorMessages.SERVICE_NOT_AVAILABLE.format(
                service=ServiceNames.LLAMAINDEX
            ),
        )

    try:
        result = await server.llamaindex_service.get_document_analysis(document_id)

        error_response = unwrap_result_to_json_response(result)
        if error_response:
            return error_response

        return result.value

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None
