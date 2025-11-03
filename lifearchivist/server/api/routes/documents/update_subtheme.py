"""
Update document subtheme endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..constants import (
    ErrorMessages,
    HTTPStatus,
    ServiceNames,
)
from ..shared.dependencies import get_server
from ..utils import extract_result_value, unwrap_result_to_json_response

router = APIRouter()


@router.patch("/{document_id}/subtheme")
async def update_document_subtheme(document_id: str, subtheme_data: dict):
    """
    Update document subtheme metadata.

    Allows updating classification, theme, and subtheme information.
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
        result = await server.llamaindex_service.update_document_metadata(
            document_id=document_id, metadata_updates=subtheme_data, merge_mode="update"
        )

        error_response = unwrap_result_to_json_response(result)
        if error_response:
            return error_response

        update_info = extract_result_value(result, dict, {})

        return {
            "success": True,
            "document_id": document_id,
            "updated_fields": list(subtheme_data.keys()),
            **update_info,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None
