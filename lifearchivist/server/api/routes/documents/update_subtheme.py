"""
Update document subtheme endpoint.
"""

from fastapi import APIRouter

from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from ..shared.utils import extract_result_value, unwrap_result_to_json_response
from .utils import validate_llamaindex_service

router = APIRouter()


@router.patch("/{document_id}/subtheme")
async def update_document_subtheme(document_id: str, subtheme_data: dict):
    """
    Update document subtheme metadata.

    Allows updating classification, theme, and subtheme information.
    """
    server = get_server()
    service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        result = await service.update_document_metadata(
            document_id=document_id, metadata_updates=subtheme_data, merge_mode="update"
        )

        error_response = unwrap_result_to_json_response(result)
        if error_response:
            return error_response

        update_info = extract_result_value(result, dict, {})

        return success_response(
            {
                "document_id": document_id,
                "updated_fields": list(subtheme_data.keys()),
                **update_info,
            }
        )

    except Exception as e:
        return internal_error_response("Update document subtheme", e)
