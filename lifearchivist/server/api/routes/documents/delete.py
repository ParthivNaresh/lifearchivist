"""
Delete document endpoint.
"""

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .response_models import DeleteDocumentResponse
from .utils import delete_vault_file_safe

router = APIRouter()

SINGLE_DOCUMENT_LIMIT = 1


@router.delete(
    "/{document_id}",
    response_model=DeleteDocumentResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Document not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Document not found: invalid-id"}
                }
            },
        },
        503: {
            "description": "LlamaIndex service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "LlamaIndex service not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Delete document failed: <error message>"}
                }
            },
        },
    },
)
async def delete_document(
    document_id: str = PathParam(..., description="Unique document identifier"),
) -> DeleteDocumentResponse:
    """
    Delete a document from the system.

    Removes document from vector index and optionally from file vault. Handles
    deduplication - only deletes vault file if no other documents reference it.

    ## Path Parameters

    - **document_id**: Unique identifier of the document to delete

    ## Response Fields

    - **document_id**: ID of deleted document
    - **index_deleted**: Whether removed from vector index
    - **vault_deleted**: Whether file removed from vault
    - **file_hash**: Hash of the deleted file (if available)
    - **chunks_deleted**: Number of text chunks removed

    ## Example Response

    ```json
    {
        "document_id": "doc_123",
        "index_deleted": true,
        "vault_deleted": true,
        "file_hash": "abc123def456",
        "chunks_deleted": 15
    }
    ```

    ## Deletion Process

    1. **Query Document**: Retrieve document metadata
    2. **Delete from Index**: Remove vectors and metadata
    3. **Check Deduplication**: See if other docs use same file
    4. **Delete from Vault**: Remove file only if not used elsewhere
    5. **Return Confirmation**: Report what was deleted

    ## Deduplication Handling

    The system handles file deduplication intelligently:
    - Multiple documents can reference the same file (by hash)
    - Vault file only deleted if no other documents use it
    - Prevents accidental deletion of shared files
    - `vault_deleted: false` means file still used by other docs

    ## Use Cases

    - Remove unwanted documents
    - Clean up duplicates
    - Free storage space
    - Delete outdated content
    - Remove sensitive documents

    ## Important Notes

    - **Permanent**: Cannot be undone
    - **Index Always Deleted**: Vector embeddings removed
    - **Vault Conditional**: File deleted only if not shared
    - **Metadata Lost**: All document metadata removed
    - **Search Impact**: Document no longer searchable

    ## Vault Deletion Logic

    - `vault_deleted: true`: File removed (not used by other docs)
    - `vault_deleted: false`: File kept (used by other docs)
    - Check file_hash to identify the physical file

    ## Performance Notes

    - Fast operation (single document)
    - Deduplication check adds minimal overhead
    - Vault deletion depends on file size
    - Index deletion is immediate

    ## Notes

    - Returns 404 if document doesn't exist
    - Safe to call multiple times (idempotent)
    - Chunks automatically deleted with document
    - Progress tracking updated automatically
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        documents_result = await server.llamaindex_service.query_documents_by_metadata(
            filters={"document_id": document_id},
            limit=SINGLE_DOCUMENT_LIMIT,
        )

        if documents_result.is_failure():
            error_msg = documents_result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Document", document_id)
            raise InternalServerError("Query document", Exception(error_msg))

        documents = documents_result.value or []
        if not documents:
            raise ResourceNotFoundError("Document", document_id)

        document_metadata = documents[0]
        file_hash = document_metadata.get("file_hash")

        delete_result = await server.llamaindex_service.delete_document(document_id)

        if delete_result.is_failure():
            error_msg = delete_result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Document", document_id)
            raise InternalServerError("Delete document", Exception(error_msg))

        delete_info = delete_result.value or {}

        vault_deleted = await delete_vault_file_safe(
            vault=server.vault,
            file_hash=file_hash,
            llamaindex_service=server.llamaindex_service,
        )

        return DeleteDocumentResponse(
            document_id=document_id,
            index_deleted=True,
            vault_deleted=vault_deleted,
            file_hash=file_hash or "",
            chunks_deleted=delete_info.get("chunks_deleted", 0),
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Delete document", e) from e
