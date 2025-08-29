"""
Document management endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..dependencies import get_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents")
async def list_documents(
    status: Optional[str] = None, limit: int = 100, offset: int = 0
):
    """List documents from LlamaIndex service."""
    server = get_server()

    logger.error(
        f"✅ Starting document list - status: {status}, limit: {limit}, offset: {offset}"
    )

    try:
        if not server.llamaindex_service:
            logger.error("❌ LlamaIndex service not available")
            raise HTTPException(
                status_code=503, detail="LlamaIndex service not available"
            )

        # Use LlamaIndex service to query documents
        filters = {}
        if status:
            filters["status"] = status
            logger.error(f"✅ Applying status filter: {status}")

        logger.error(f"✅ Querying documents with filters: {filters}")
        documents = await server.llamaindex_service.query_documents_by_metadata(
            filters=filters, limit=limit, offset=offset
        )

        logger.error(f"✅ Found {len(documents)} documents")
        for i, doc in enumerate(documents):
            doc_id = doc.get("document_id", "unknown")
            file_hash = doc.get("metadata", {}).get("file_hash", "missing")
            doc_status = doc.get("metadata", {}).get("status", "missing")
            original_path = doc.get("metadata", {}).get("original_path", "missing")
            logger.error(
                f"✅ Document {i+1}: ID={doc_id}, hash={file_hash[:16]}..., status={doc_status}, path={original_path}"
            )

        result = {
            "documents": documents,
            "total": len(documents),
            "limit": limit,
            "offset": offset,
        }

        logger.error(
            f"✅ Returning {len(documents)} documents (total: {len(documents)})"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Failed to list documents: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/documents")
async def clear_all_documents():
    """Comprehensive clear all documents operation with progress tracking."""
    server = get_server()

    try:
        logger.error("✅ Starting comprehensive Clear All operation")

        # Step 1: Clear LlamaIndex data
        logger.error("✅ Phase 1/3: Clearing LlamaIndex data...")
        llamaindex_metrics = {}
        if server.llamaindex_service:
            try:
                llamaindex_metrics = await server.llamaindex_service.clear_all_data()
                logger.error(
                    f"✅ LlamaIndex cleared: {llamaindex_metrics.get('storage_files_deleted', 0)} files"
                )
            except Exception as llamaindex_error:
                logger.error(f"❌ LlamaIndex clearing failed: {llamaindex_error}")
                llamaindex_metrics = {"error": str(llamaindex_error)}
        else:
            logger.error("❌ LlamaIndex service not available, skipping")
            llamaindex_metrics = {"skipped": True}

        # Step 2: Clear vault files (no specific hashes since we don't have database)
        logger.error("✅ Phase 2/3: Clearing vault storage...")
        vault_metrics = await server.vault.clear_all_files([])  # Empty list = clear all
        logger.error(
            f"✅ Vault cleared: {vault_metrics['files_deleted']} files, {vault_metrics['bytes_reclaimed'] / (1024*1024):.2f} MB reclaimed"
        )

        # Step 3: Clear progress tracking data
        logger.error("✅ Phase 3/3: Clearing progress tracking data...")
        progress_metrics = {}
        if server.progress_manager:
            try:
                progress_metrics = await server.progress_manager.clear_all_progress()
                logger.error(
                    f"✅ Progress data cleared: {progress_metrics.get('total_keys_deleted', 0)} Redis keys"
                )
            except Exception as progress_error:
                logger.error(f"❌ Progress data clearing failed: {progress_error}")
                progress_metrics = {"error": str(progress_error)}
        else:
            logger.error("❌ Progress manager not available, skipping")
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

        logger.error(
            f"✅ Clear All completed: {total_files_deleted} files deleted, {result['summary']['total_mb_reclaimed']} MB reclaimed"
        )
        return result

    except Exception as e:
        logger.error(f"❌ Clear All operation failed: {e}")
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LlamaIndex analysis failed for {document_id}: {e}")
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
            raise HTTPException(status_code=400, detail="Offset must be non-negative")

        result = await server.llamaindex_service.get_document_chunks(
            document_id=document_id, limit=limit, offset=offset
        )

        if "error" in result:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=result["error"])
            else:
                raise HTTPException(status_code=500, detail=result["error"])

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunks for {document_id}: {e}")
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get neighbors for {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None
