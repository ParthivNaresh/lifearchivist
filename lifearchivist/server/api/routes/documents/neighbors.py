"""
Get document neighbors endpoint.
"""

from fastapi import APIRouter

from ..constants import DocumentConstants, ValidationMessages
from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    not_found_response,
    validation_error_response,
)
from ..shared.utils import handle_service_result
from .utils import validate_llamaindex_service

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
    service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    assert service is not None

    if (
        top_k < DocumentConstants.NEIGHBORS_MIN_TOP_K
        or top_k > DocumentConstants.NEIGHBORS_MAX_TOP_K
    ):
        return validation_error_response(
            ValidationMessages.TOP_K_RANGE.format(
                min=DocumentConstants.NEIGHBORS_MIN_TOP_K,
                max=DocumentConstants.NEIGHBORS_MAX_TOP_K,
            )
        )

    try:
        result = await service.get_document_neighbors(
            document_id=document_id, top_k=top_k
        )

        if hasattr(result, "is_failure"):
            error_response = handle_service_result(result)
            if error_response:
                return error_response
            return result.value

        if isinstance(result, dict) and "error" in result:
            if "not found" in result["error"].lower():
                return not_found_response("Document", document_id)
            else:
                return internal_error_response(
                    "Get document neighbors", RuntimeError(result["error"])
                )

        return result

    except Exception as e:
        return internal_error_response("Get document neighbors", e)
