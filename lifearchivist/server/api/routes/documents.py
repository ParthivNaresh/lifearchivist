"""
Document management endpoints.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents")
async def list_documents(
    status: Optional[str] = None,
    limit: int = 50,  # Reduced default limit for better performance
    offset: int = 0,
    count_only: bool = False,  # Option to get count only
):
    """List documents from LlamaIndex service with UI-compatible formatting."""
    server = get_server()

    try:
        if not server.llamaindex_service:
            raise HTTPException(
                status_code=503, detail="LlamaIndex service not available"
            )

        # Validate pagination parameters
        if limit > 500:  # Max limit to prevent performance issues
            limit = 500
        if limit < 1:
            limit = 50
        if offset < 0:
            offset = 0

        filters = {}
        if status:
            filters["status"] = status

        # If only count is requested, return early
        if count_only:
            # For now, we'll need to query all to get count
            # TODO: Implement proper count method in LlamaIndex service
            all_docs_result = (
                await server.llamaindex_service.query_documents_by_metadata(
                    filters=filters, limit=10000, offset=0
                )
            )
            if all_docs_result.is_failure():
                raise HTTPException(status_code=500, detail=all_docs_result.error)
            all_docs = all_docs_result.unwrap()
            return {"total": len(all_docs), "filters": filters}

        raw_documents_result = (
            await server.llamaindex_service.query_documents_by_metadata(
                filters=filters, limit=limit, offset=offset
            )
        )
        if raw_documents_result.is_failure():
            raise HTTPException(status_code=500, detail=raw_documents_result.error)
        raw_documents = raw_documents_result.unwrap()

        formatted_documents = []
        for doc in raw_documents:
            metadata = doc.get("metadata", {})
            theme_metadata = metadata.get("classifications", {})
            formatted_doc = {
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
                # Handle theme data - it might be a dict (full metadata) or string (minimal metadata)
                "theme": theme_metadata.get("theme"),
                "theme_confidence": theme_metadata.get("confidence"),
                "confidence_level": theme_metadata.get("confidence_level"),
                "classification": theme_metadata.get("match_tier"),
                "pattern_or_phrase": theme_metadata.get("match_pattern"),
                # Subtheme level (e.g., Banking, Investment, Insurance)
                "subthemes": theme_metadata.get("subthemes", []),
                "primary_subtheme": theme_metadata.get("primary_subtheme"),
                # Subclassification level (e.g., Bank Statement, Brokerage Statement)
                "subclassifications": theme_metadata.get("subclassifications", []),
                "primary_subclassification": theme_metadata.get(
                    "primary_subclassification"
                ),
                "subclassification_confidence": theme_metadata.get(
                    "subclassification_confidence"
                ),
                # Category mapping for UI
                "category_mapping": theme_metadata.get("category_mapping", {}),
            }
            formatted_documents.append(formatted_doc)

        return {
            "documents": formatted_documents,
            "total": len(formatted_documents),
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a specific document from both LlamaIndex and vault."""
    server = get_server()

    try:
        # Step 1: Get document metadata to find file hash
        if not server.llamaindex_service:
            raise HTTPException(
                status_code=503, detail="LlamaIndex service not available"
            )

        # Get document metadata first
        documents_result = await server.llamaindex_service.query_documents_by_metadata(
            filters={"document_id": document_id}, limit=1
        )

        if documents_result.is_failure():
            raise HTTPException(status_code=500, detail=documents_result.error)

        documents = documents_result.unwrap()
        if not documents:
            raise HTTPException(
                status_code=404, detail=f"Document {document_id} not found"
            )

        document_metadata = documents[0].get("metadata", {})
        file_hash = document_metadata.get("file_hash")

        # Step 2: Delete from LlamaIndex (now returns Result)
        delete_result = await server.llamaindex_service.delete_document(document_id)

        if delete_result.is_failure():
            # Convert Result to HTTP response
            return JSONResponse(
                content=delete_result.to_dict(), status_code=delete_result.status_code
            )

        delete_info = delete_result.unwrap()

        # Step 3: Delete from vault if we have the file hash
        vault_deleted = False
        if file_hash and server.vault:
            try:
                # Check if any other documents use this file (deduplication check)
                other_docs_result = (
                    await server.llamaindex_service.query_documents_by_metadata(
                        filters={"file_hash": file_hash}, limit=2
                    )
                )
                other_docs = (
                    other_docs_result.unwrap() if other_docs_result.is_success() else []
                )

                # Only delete from vault if this is the only document using this file
                if (
                    len(other_docs) <= 1
                ):  # 1 or 0 because we might have already deleted from index
                    # Use the public method that finds files by hash pattern
                    # This is better because it doesn't require knowing the extension
                    metrics = {"files_deleted": 0, "bytes_reclaimed": 0, "errors": []}
                    await server.vault.delete_file_by_hash(file_hash, metrics)
                    vault_deleted = metrics["files_deleted"] > 0
            except Exception as e:
                # Log but don't fail if vault deletion fails
                print(f"Warning: Failed to delete file from vault: {e}")

        return {
            "success": True,
            **delete_info,  # Include info from Result
            "index_deleted": True,
            "vault_deleted": vault_deleted,
            "file_hash": file_hash,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.patch("/documents/{document_id}/subtheme")
async def update_document_subtheme(document_id: str, subtheme_data: dict):
    """Update document subtheme metadata."""
    server = get_server()

    try:
        if not server.llamaindex_service:
            raise HTTPException(
                status_code=503, detail="LlamaIndex service not available"
            )

        # Update document metadata with subtheme information
        success = await server.llamaindex_service.update_document_metadata(
            document_id=document_id, metadata_updates=subtheme_data, merge_mode="update"
        )

        if success:
            return {
                "success": True,
                "document_id": document_id,
                "updated_fields": list(subtheme_data.keys()),
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to update document metadata"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/documents")
async def clear_all_documents():
    """Comprehensive clear all documents operation with progress tracking."""
    server = get_server()

    try:
        # Step 1: Clear LlamaIndex data (now returns Result)
        if server.llamaindex_service:
            clear_result = await server.llamaindex_service.clear_all_data()

            if clear_result.is_failure():
                # Convert Result to HTTP response
                return JSONResponse(
                    content=clear_result.to_dict(), status_code=clear_result.status_code
                )

            llamaindex_metrics = clear_result.unwrap()
        else:
            llamaindex_metrics = {"skipped": True}

        # Step 2: Clear vault files
        if not server.vault:
            raise HTTPException(status_code=500, detail="Vault not initialized")
        vault_metrics = await server.vault.clear_all_files([])  # Empty list = clear all

        # Step 3: Clear progress tracking data
        if server.progress_manager:
            try:
                progress_metrics = await server.progress_manager.clear_all_progress()
            except Exception as progress_error:
                progress_metrics = {"error": str(progress_error)}
        else:
            progress_metrics = {"skipped": True}

        # Compile comprehensive metrics
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

        result = {
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

        if result.is_failure():
            # Convert Result to HTTP response
            return JSONResponse(
                content=result.to_dict(), status_code=result.status_code
            )

        # Return the success data
        return result.unwrap()

    except HTTPException:
        raise
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

        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 1000"
            )
        if offset < 0:
            raise HTTPException(status_code=400, detail="Offset must be non-negative")

        # get_document_chunks now returns Result
        result = await server.llamaindex_service.get_document_chunks(
            document_id=document_id, limit=limit, offset=offset
        )

        if result.is_failure():
            # Convert Result to HTTP response
            return JSONResponse(
                content=result.to_dict(), status_code=result.status_code
            )

        # Return the success data
        return result.unwrap()

    except HTTPException:
        raise
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
