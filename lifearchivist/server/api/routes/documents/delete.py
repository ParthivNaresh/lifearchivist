"""
Delete document endpoint.
"""

from fastapi import APIRouter, HTTPException

from ..constants import (
    DocumentConstants,
    ErrorMessages,
    HTTPStatus,
    ServiceNames,
)
from ..shared.dependencies import get_server
from ..utils import (
    delete_vault_file_safe,
    extract_document_metadata,
    extract_result_value,
    unwrap_result_to_json_response,
)

router = APIRouter()


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a specific document from both LlamaIndex and vault.

    Handles deduplication - only deletes from vault if no other documents use the same file.
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
        documents_result = await server.llamaindex_service.query_documents_by_metadata(
            filters={"document_id": document_id},
            limit=DocumentConstants.SINGLE_DOCUMENT_LIMIT,
        )

        error_response = unwrap_result_to_json_response(documents_result)
        if error_response:
            return error_response

        documents = extract_result_value(documents_result, list, [])
        document_metadata = extract_document_metadata(documents, document_id)
        file_hash = document_metadata.get("file_hash")

        delete_result = await server.llamaindex_service.delete_document(document_id)

        error_response = unwrap_result_to_json_response(delete_result)
        if error_response:
            return error_response

        delete_info = extract_result_value(delete_result, dict, {})

        vault_deleted = await delete_vault_file_safe(
            vault=server.vault,
            file_hash=file_hash,
            llamaindex_service=server.llamaindex_service,
        )

        return {
            "success": True,
            **delete_info,
            "index_deleted": True,
            "vault_deleted": vault_deleted,
            "file_hash": file_hash,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None
