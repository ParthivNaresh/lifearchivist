"""
Document management endpoints with Result type unwrapping.

Provides CRUD operations for documents including:
- Listing and filtering documents
- Deleting documents from index and vault
- Updating document metadata
- Analyzing document structure and chunks
- Finding similar documents
"""

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..dependencies import get_server
from .constants import (
    DocumentConstants,
    ErrorMessages,
    HTTPStatus,
    PaginationDefaults,
    ServiceNames,
    ValidationMessages,
)
from .utils import (
    delete_vault_file_safe,
    extract_document_metadata,
    extract_result_value,
    unwrap_result_to_json_response,
)

router = APIRouter(prefix="/api", tags=["documents"])


def _format_document_for_ui(doc: Dict) -> Dict:
    """
    Format a document for UI consumption.

    Extracts and flattens metadata for easier frontend access.
    """
    metadata = doc.get("metadata", {})
    theme_metadata = metadata.get("classifications", {})

    return {
        "id": doc.get("document_id") or metadata.get("document_id"),
        "file_hash": metadata.get("file_hash", ""),
        "original_path": metadata.get("original_path", ""),
        "mime_type": metadata.get("mime_type"),
        "size_bytes": metadata.get("size_bytes", 0),
        "created_at": metadata.get("created_at", ""),
        "modified_at": metadata.get("modified_at"),
        "ingested_at": metadata.get("created_at", ""),
        "status": metadata.get("status", "unknown"),
        "error_message": metadata.get("error_message"),
        "word_count": metadata.get("word_count"),
        "language": metadata.get("language"),
        "extraction_method": metadata.get("extraction_method"),
        "text_preview": doc.get("text_preview", ""),
        "has_content": metadata.get("has_content", False),
        "tags": metadata.get("tags", []),
        "tag_count": len(metadata.get("tags", [])),
        "theme": theme_metadata.get("theme"),
        "theme_confidence": theme_metadata.get("confidence"),
        "confidence_level": theme_metadata.get("confidence_level"),
        "classification": theme_metadata.get("match_tier"),
        "pattern_or_phrase": theme_metadata.get("match_pattern"),
        "subthemes": theme_metadata.get("subthemes", []),
        "primary_subtheme": theme_metadata.get("primary_subtheme"),
        "subclassifications": theme_metadata.get("subclassifications", []),
        "primary_subclassification": theme_metadata.get("primary_subclassification"),
        "subclassification_confidence": theme_metadata.get(
            "subclassification_confidence"
        ),
        "category_mapping": theme_metadata.get("category_mapping", {}),
    }


def _validate_pagination(limit: int, offset: int) -> tuple[int, int]:
    """
    Validate and normalize pagination parameters.

    Returns normalized (limit, offset) tuple.
    """
    if limit > PaginationDefaults.MAX_LIMIT:
        limit = PaginationDefaults.MAX_LIMIT
    elif limit < PaginationDefaults.MIN_LIMIT:
        limit = PaginationDefaults.DEFAULT_LIMIT

    if offset < PaginationDefaults.DEFAULT_OFFSET:
        offset = PaginationDefaults.DEFAULT_OFFSET

    return limit, offset


@router.get("/documents")
async def list_documents(
    status: Optional[str] = None,
    limit: int = PaginationDefaults.DEFAULT_LIMIT,
    offset: int = PaginationDefaults.DEFAULT_OFFSET,
    count_only: bool = False,
):
    """
    List documents from LlamaIndex service with UI-compatible formatting.

    Supports filtering by status and pagination.
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
        limit, offset = _validate_pagination(limit, offset)

        filters = {}
        if status:
            filters["status"] = status

        if count_only:
            all_docs_result = (
                await server.llamaindex_service.query_documents_by_metadata(
                    filters=filters,
                    limit=DocumentConstants.COUNT_QUERY_LIMIT,
                    offset=PaginationDefaults.DEFAULT_OFFSET,
                )
            )
            error_response = unwrap_result_to_json_response(all_docs_result)
            if error_response:
                return error_response

            all_docs = extract_result_value(all_docs_result, list, [])
            return {"total": len(all_docs), "filters": filters}

        raw_documents_result = (
            await server.llamaindex_service.query_documents_by_metadata(
                filters=filters, limit=limit, offset=offset
            )
        )

        error_response = unwrap_result_to_json_response(raw_documents_result)
        if error_response:
            return error_response

        raw_documents = extract_result_value(raw_documents_result, list, [])
        formatted_documents = [_format_document_for_ui(doc) for doc in raw_documents]

        return {
            "success": True,
            "documents": formatted_documents,
            "total": len(formatted_documents),
            "limit": limit,
            "offset": offset,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None


@router.delete("/documents/{document_id}")
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


@router.patch("/documents/{document_id}/subtheme")
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


@router.delete("/documents")
async def clear_all_documents():
    """
    Comprehensive clear all documents operation with progress tracking.

    Clears data from:
    - LlamaIndex (vectors, metadata, docstore)
    - Vault (files)
    - Progress tracking
    """
    server = get_server()

    try:
        if server.llamaindex_service:
            clear_result = await server.llamaindex_service.clear_all_data()

            error_response = unwrap_result_to_json_response(clear_result)
            if error_response:
                return error_response

            llamaindex_metrics = extract_result_value(clear_result, dict, {})
        else:
            llamaindex_metrics = {"skipped": True}

        if not server.vault:
            raise HTTPException(
                status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                detail=ErrorMessages.VAULT_NOT_INITIALIZED,
            )
        vault_metrics = await server.vault.clear_all_files([])

        if server.progress_manager:
            try:
                progress_metrics = await server.progress_manager.clear_all_progress()
            except Exception as progress_error:
                progress_metrics = {"error": str(progress_error)}
        else:
            progress_metrics = {"skipped": True}

        vault_files_deleted = vault_metrics["files_deleted"] + vault_metrics.get(
            "orphaned_files_deleted", 0
        )
        vault_bytes_reclaimed = vault_metrics["bytes_reclaimed"] + vault_metrics.get(
            "orphaned_bytes_reclaimed", 0
        )
        total_files_deleted = vault_files_deleted + llamaindex_metrics.get(
            "storage_files_deleted", 0
        )
        total_bytes_reclaimed = vault_bytes_reclaimed + llamaindex_metrics.get(
            "storage_bytes_reclaimed", 0
        )

        return {
            "success": True,
            "operation": "comprehensive_clear_all",
            "summary": {
                "total_files_deleted": total_files_deleted,
                "total_bytes_reclaimed": total_bytes_reclaimed,
                "total_mb_reclaimed": round(total_bytes_reclaimed / (1024 * 1024), 2),
            },
            "vault_metrics": vault_metrics,
            "llamaindex_metrics": llamaindex_metrics,
            "progress_metrics": progress_metrics,
            "errors": (
                vault_metrics.get("errors", [])
                + llamaindex_metrics.get("errors", [])
                + progress_metrics.get("errors", [])
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None


@router.get("/documents/{document_id}/llamaindex-analysis")
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


@router.get("/documents/{document_id}/llamaindex-chunks")
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


@router.get("/documents/{document_id}/llamaindex-neighbors")
async def get_llamaindex_document_neighbors(
    document_id: str, top_k: int = DocumentConstants.NEIGHBORS_DEFAULT_TOP_K
):
    """
    Get semantically similar documents for a given document.

    Uses vector similarity to find related documents.
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
        top_k < DocumentConstants.NEIGHBORS_MIN_TOP_K
        or top_k > DocumentConstants.NEIGHBORS_MAX_TOP_K
    ):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=ValidationMessages.TOP_K_RANGE.format(
                min=DocumentConstants.NEIGHBORS_MIN_TOP_K,
                max=DocumentConstants.NEIGHBORS_MAX_TOP_K,
            ),
        )

    try:
        result = await server.llamaindex_service.get_document_neighbors(
            document_id=document_id, top_k=top_k
        )

        if hasattr(result, "is_failure"):
            if result.is_failure():
                return JSONResponse(
                    content=result.to_dict(),
                    status_code=result.status_code,
                )
            return result.value

        if isinstance(result, dict) and "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(
                    status_code=HTTPStatus.NOT_FOUND, detail=result["error"]
                )
            else:
                raise HTTPException(
                    status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=result["error"]
                )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=str(e)
        ) from None
