"""
Get document chunks endpoint.
"""

from fastapi import APIRouter

from ..constants import DocumentConstants, PaginationDefaults, ValidationMessages
from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, validation_error_response
from ..shared.utils import unwrap_result_to_json_response
from .utils import validate_llamaindex_service

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
    service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    assert service is not None

    if (
        limit < DocumentConstants.CHUNKS_MIN_LIMIT
        or limit > DocumentConstants.CHUNKS_MAX_LIMIT
    ):
        return validation_error_response(
            ValidationMessages.LIMIT_RANGE.format(
                min=DocumentConstants.CHUNKS_MIN_LIMIT,
                max=DocumentConstants.CHUNKS_MAX_LIMIT,
            )
        )

    if offset < PaginationDefaults.DEFAULT_OFFSET:
        return validation_error_response(ValidationMessages.OFFSET_NON_NEGATIVE)

    try:
        result = await service.get_document_chunks(
            document_id=document_id, limit=limit, offset=offset
        )

        error_response = unwrap_result_to_json_response(result)
        if error_response:
            return error_response

        return result.value

    except Exception as e:
        return internal_error_response("Get document chunks", e)
