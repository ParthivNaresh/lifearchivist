"""
Get document analysis endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response
from ..shared.utils import unwrap_result_to_json_response
from .utils import validate_llamaindex_service

router = APIRouter()


@router.get("/{document_id}/llamaindex-analysis")
async def get_llamaindex_document_analysis(document_id: str):
    """
    Get comprehensive LlamaIndex analysis for a document.

    Returns chunk statistics, processing info, and storage details.
    """
    server = get_server()
    service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        result = await service.get_document_analysis(document_id)

        error_response = unwrap_result_to_json_response(result)
        if error_response:
            return error_response

        return result.value

    except Exception as e:
        return internal_error_response("Get document analysis", e)
