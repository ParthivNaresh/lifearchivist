"""
Get document chunks endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..constants import (
    DocumentConstants,
    ErrorMessages,
    HTTPStatus,
    PaginationDefaults,
    ServiceNames,
    ValidationMessages,
)
from ..shared.dependencies import get_server
from ..utils import unwrap_result_to_json_response

router = APIRouter()


@router.get("/{document_id}/llamaindex-chunks")
async def get_llamaindex_document_chunks(
    document_id: str,
    limit: int = DocumentConstants.CHUNKS_DEFAULT_LIMIT,
    offset: int = PaginationDefaults.DEFAULT_OFFSET,
):
    """
    Get paginated chunks for a document from LlamaIndex.

    Returns the text chunks with their metadata and embeddings info.
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
        limit < DocumentConstants.CHUNKS_MIN_LIMIT
        or limit > DocumentConstants.CHUNKS_MAX_LIMIT
    ):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ValidationMessages.LIMIT_RANGE.format(
                min=DocumentConstants.CHUNKS_MIN_LIMIT,
                max=DocumentConstants.CHUNKS_MAX_LIMIT,
            ),
        )
    if offset < PaginationDefaults.DEFAULT_OFFSET:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ValidationMessages.OFFSET_NON_NEGATIVE,
        )

    try:
        result = await server.llamaindex_service.get_document_chunks(
            document_id=document_id, limit=limit, offset=offset
        )

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
