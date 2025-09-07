"""
Document management endpoints.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents")
async def list_documents(
    status: Optional[str] = None, limit: int = 100, offset: int = 0
):
    """List documents from LlamaIndex service with UI-compatible formatting."""
    server = get_server()

    try:
        if not server.llamaindex_service:
            raise HTTPException(
                status_code=503, detail="LlamaIndex service not available"
            )
        # Use LlamaIndex service to query documents
        filters = {}
        if status:
            filters["status"] = status

        raw_documents = await server.llamaindex_service.query_documents_by_metadata(
            filters=filters, limit=limit, offset=offset
        )
        
        # Transform documents to UI-compatible format
        formatted_documents = []
        for doc in raw_documents:
            metadata = doc.get("metadata", {})
            
            # Extract fields from metadata with fallbacks
            formatted_doc = {
                "id": doc.get("document_id") or metadata.get("document_id"),
                "file_hash": metadata.get("file_hash", ""),
                "original_path": metadata.get("original_path", ""),
                "mime_type": metadata.get("mime_type"),
                "size_bytes": metadata.get("size_bytes", 0),
                "created_at": metadata.get("created_at", ""),
                "modified_at": metadata.get("modified_at"),
                "ingested_at": metadata.get("created_at", ""),  # Use created_at as ingested_at
                "status": metadata.get("status", "unknown"),
                "error_message": metadata.get("error_message"),
                "word_count": metadata.get("word_count"),
                "language": metadata.get("language"),
                "extraction_method": metadata.get("extraction_method"),
                "text_preview": doc.get("text_preview", ""),
                "has_content": metadata.get("has_content", False),
                "tags": metadata.get("tags", []),
                "tag_count": len(metadata.get("tags", [])),
            }
            formatted_documents.append(formatted_doc)
        
        result = {
            "documents": formatted_documents,
            "total": len(formatted_documents),
            "limit": limit,
            "offset": offset,
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/documents")
async def clear_all_documents():
    """Comprehensive clear all documents operation with progress tracking."""
    server = get_server()

    try:
        if server.llamaindex_service:
            try:
                llamaindex_metrics = (
                    await server.llamaindex_service.clear_all_data()
                )
            except Exception as llamaindex_error:
                llamaindex_metrics = {"error": str(llamaindex_error)}
        else:
            llamaindex_metrics = {"skipped": True}

        # Step 2: Clear vault files
        if not server.vault:
            raise HTTPException(status_code=500, detail="Vault not initialized")
        vault_metrics = await server.vault.clear_all_files(
            []
        )  # Empty list = clear all

        # Step 3: Clear progress tracking data
        if server.progress_manager:
            try:
                progress_metrics = (
                    await server.progress_manager.clear_all_progress()
                )
            except Exception as progress_error:
                progress_metrics = {"error": str(progress_error)}
        else:
            progress_metrics = {"skipped": True}

        # Compile comprehensive metrics
        vault_files_deleted = vault_metrics["files_deleted"] + vault_metrics.get(
            "orphaned_files_deleted", 0
        )
        vault_bytes_reclaimed = vault_metrics[
            "bytes_reclaimed"
        ] + vault_metrics.get("orphaned_bytes_reclaimed", 0)
        total_files_deleted = vault_files_deleted + llamaindex_metrics.get(
            "storage_files_deleted", 0
        )
        total_bytes_reclaimed = vault_bytes_reclaimed + llamaindex_metrics.get(
            "storage_bytes_reclaimed", 0
        )

        result = {
            "success": True,
            "operation": "comprehensive_clear_all",
            "summary": {
                "total_files_deleted": total_files_deleted,
                "total_bytes_reclaimed": total_bytes_reclaimed,
                "total_mb_reclaimed": round(
                    total_bytes_reclaimed / (1024 * 1024), 2
                ),
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
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/documents/{document_id}/llamaindex-analysis")
async def get_llamaindex_document_analysis(document_id: str):
    """Get comprehensive LlamaIndex analysis for a document."""
    server = get_server()
    try:
        if not server.llamaindex_service:
            raise HTTPException(
                status_code=503, detail="LlamaIndex service not available"
            )

        result = await server.llamaindex_service.get_document_analysis(document_id)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/documents/{document_id}/llamaindex-chunks")
async def get_llamaindex_document_chunks(
    document_id: str, limit: int = 100, offset: int = 0
):
    """Get paginated chunks for a document from LlamaIndex."""
    server = get_server()

    try:
        if not server.llamaindex_service:
            raise HTTPException(
                status_code=503, detail="LlamaIndex service not available"
            )

        # Validate pagination parameters
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 1000"
            )
        if offset < 0:
            raise HTTPException(
                status_code=400, detail="Offset must be non-negative"
            )

        result = await server.llamaindex_service.get_document_chunks(
            document_id=document_id, limit=limit, offset=offset
        )

        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/documents/{document_id}/llamaindex-neighbors")
async def get_llamaindex_document_neighbors(document_id: str, top_k: int = 10):
    """Get semantically similar documents for a given document."""
    server = get_server()
    try:
        if not server.llamaindex_service:
            raise HTTPException(
                status_code=503, detail="LlamaIndex service not available"
            )

        # Validate parameters
        if top_k < 1 or top_k > 100:
            raise HTTPException(
                status_code=400, detail="top_k must be between 1 and 100"
            )

        result = await server.llamaindex_service.get_document_neighbors(
            document_id=document_id, top_k=top_k
        )

        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
