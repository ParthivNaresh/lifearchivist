"""
Delete document endpoint.
"""

from fastapi import APIRouter

from ..constants import DocumentConstants
from ..shared.dependencies import get_server
from ..shared.responses import internal_error_response, success_response
from ..shared.utils import extract_result_value, unwrap_result_to_json_response
from .utils import (
    delete_vault_file_safe,
    extract_document_metadata,
    validate_llamaindex_service,
)

router = APIRouter()


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a specific document from both LlamaIndex and vault.

    Handles deduplication - only deletes from vault if no other documents use the same file.
    """
    server = get_server()
    service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    assert service is not None

    try:
        documents_result = await service.query_documents_by_metadata(
            filters={"document_id": document_id},
            limit=DocumentConstants.SINGLE_DOCUMENT_LIMIT,
        )

        error_response = unwrap_result_to_json_response(documents_result)
        if error_response:
            return error_response

        documents = extract_result_value(documents_result, list, [])
        document_metadata, error_response = extract_document_metadata(
            documents, document_id
        )
        if error_response:
            return error_response

        assert document_metadata is not None

        file_hash = document_metadata.get("file_hash")

        delete_result = await service.delete_document(document_id)

        error_response = unwrap_result_to_json_response(delete_result)
        if error_response:
            return error_response

        delete_info = extract_result_value(delete_result, dict, {})

        vault_deleted = await delete_vault_file_safe(
            vault=server.vault,
            file_hash=file_hash,
            llamaindex_service=service,
        )

        return success_response(
            {
                **delete_info,
                "index_deleted": True,
                "vault_deleted": vault_deleted,
                "file_hash": file_hash,
            }
        )

    except Exception as e:
        return internal_error_response("Delete document", e)
