"""
Document management endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from lifearchivist.utils.logging import log_context
from lifearchivist.utils.logging.structured import MetricsCollector

from ..dependencies import get_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents")
async def list_documents(
    status: Optional[str] = None, limit: int = 100, offset: int = 0
):
    """List documents from LlamaIndex service."""
    with log_context(
        operation="api_list_documents",
        status_filter=status,
        limit=limit,
        offset=offset,
    ):
        metrics = MetricsCollector("api_list_documents")
        metrics.start()

        server = get_server()

        metrics.add_metric("status_filter", status)
        metrics.add_metric("limit", limit)
        metrics.add_metric("offset", offset)

        try:
            if not server.llamaindex_service:
                metrics.set_error(RuntimeError("LlamaIndex service not available"))
                metrics.report("api_list_documents_failed")
                raise HTTPException(
                    status_code=503, detail="LlamaIndex service not available"
                )

            # Use LlamaIndex service to query documents
            filters = {}
            if status:
                filters["status"] = status

            documents = await server.llamaindex_service.query_documents_by_metadata(
                filters=filters, limit=limit, offset=offset
            )

            metrics.add_metric("documents_found", len(documents))
            metrics.set_success(True)
            metrics.report("api_list_documents_completed")

            result = {
                "documents": documents,
                "total": len(documents),
                "limit": limit,
                "offset": offset,
            }
            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_list_documents_failed")
            raise HTTPException(status_code=500, detail=str(e)) from None


@router.delete("/documents")
async def clear_all_documents():
    """Comprehensive clear all documents operation with progress tracking."""
    with log_context(
        operation="api_clear_all_documents",
    ):
        metrics = MetricsCollector("api_clear_all_documents")
        metrics.start()

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

            # Add comprehensive metrics to the metrics collector
            metrics.add_metric("total_files_deleted", total_files_deleted)
            metrics.add_metric("total_bytes_reclaimed", total_bytes_reclaimed)
            metrics.add_metric("vault_files_deleted", vault_files_deleted)
            metrics.add_metric(
                "llamaindex_files_deleted",
                llamaindex_metrics.get("storage_files_deleted", 0),
            )
            metrics.set_success(True)
            metrics.report("api_clear_all_documents_completed")

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
            metrics.set_error(e)
            metrics.report("api_clear_all_documents_failed")

            raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/documents/{document_id}/llamaindex-analysis")
async def get_llamaindex_document_analysis(document_id: str):
    """Get comprehensive LlamaIndex analysis for a document."""
    with log_context(
        operation="api_get_document_analysis",
        document_id=document_id,
    ):
        metrics = MetricsCollector("api_get_document_analysis")
        metrics.start()

        server = get_server()

        metrics.add_metric("document_id", document_id)

        try:
            if not server.llamaindex_service:
                metrics.set_error(RuntimeError("LlamaIndex service not available"))
                metrics.report("api_get_document_analysis_failed")
                raise HTTPException(
                    status_code=503, detail="LlamaIndex service not available"
                )

            result = await server.llamaindex_service.get_document_analysis(document_id)

            if "error" in result:
                metrics.set_error(ValueError(result["error"]))
                metrics.report("api_get_document_analysis_failed")
                raise HTTPException(status_code=404, detail=result["error"])

            metrics.add_metric("analysis_status", result.get("status", "unknown"))
            metrics.add_metric("chunks_count", len(result.get("chunks_preview", [])))
            metrics.set_success(True)
            metrics.report("api_get_document_analysis_completed")
            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_get_document_analysis_failed")
            raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/documents/{document_id}/llamaindex-chunks")
async def get_llamaindex_document_chunks(
    document_id: str, limit: int = 100, offset: int = 0
):
    """Get paginated chunks for a document from LlamaIndex."""
    with log_context(
        operation="api_get_document_chunks",
        document_id=document_id,
        limit=limit,
        offset=offset,
    ):
        metrics = MetricsCollector("api_get_document_chunks")
        metrics.start()

        server = get_server()

        metrics.add_metric("document_id", document_id)
        metrics.add_metric("limit", limit)
        metrics.add_metric("offset", offset)

        try:
            if not server.llamaindex_service:
                metrics.set_error(RuntimeError("LlamaIndex service not available"))
                metrics.report("api_get_document_chunks_failed")
                raise HTTPException(
                    status_code=503, detail="LlamaIndex service not available"
                )

            # Validate pagination parameters
            if limit < 1 or limit > 1000:
                metrics.set_error(ValueError("Invalid limit parameter"))
                metrics.report("api_get_document_chunks_failed")
                raise HTTPException(
                    status_code=400, detail="Limit must be between 1 and 1000"
                )
            if offset < 0:
                metrics.set_error(ValueError("Invalid offset parameter"))
                metrics.report("api_get_document_chunks_failed")
                raise HTTPException(
                    status_code=400, detail="Offset must be non-negative"
                )

            result = await server.llamaindex_service.get_document_chunks(
                document_id=document_id, limit=limit, offset=offset
            )

            if "error" in result:
                if "not found" in result["error"].lower():
                    metrics.set_error(ValueError(result["error"]))
                    metrics.report("api_get_document_chunks_failed")
                    raise HTTPException(status_code=404, detail=result["error"])
                else:
                    metrics.set_error(RuntimeError(result["error"]))
                    metrics.report("api_get_document_chunks_failed")
                    raise HTTPException(status_code=500, detail=result["error"])

            chunks_returned = len(result.get("chunks", []))
            total_chunks = result.get("total", 0)
            has_more = result.get("has_more", False)

            metrics.add_metric("chunks_returned", chunks_returned)
            metrics.add_metric("total_chunks", total_chunks)
            metrics.add_metric("has_more", has_more)
            metrics.set_success(True)
            metrics.report("api_get_document_chunks_completed")
            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_get_document_chunks_failed")
            raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/documents/{document_id}/llamaindex-neighbors")
async def get_llamaindex_document_neighbors(document_id: str, top_k: int = 10):
    """Get semantically similar documents for a given document."""
    with log_context(
        operation="api_get_document_neighbors",
        document_id=document_id,
        top_k=top_k,
    ):
        metrics = MetricsCollector("api_get_document_neighbors")
        metrics.start()

        server = get_server()

        metrics.add_metric("document_id", document_id)
        metrics.add_metric("top_k", top_k)

        try:
            if not server.llamaindex_service:
                metrics.set_error(RuntimeError("LlamaIndex service not available"))
                metrics.report("api_get_document_neighbors_failed")
                raise HTTPException(
                    status_code=503, detail="LlamaIndex service not available"
                )

            # Validate parameters
            if top_k < 1 or top_k > 100:
                metrics.set_error(ValueError("Invalid top_k parameter"))
                metrics.report("api_get_document_neighbors_failed")
                raise HTTPException(
                    status_code=400, detail="top_k must be between 1 and 100"
                )

            result = await server.llamaindex_service.get_document_neighbors(
                document_id=document_id, top_k=top_k
            )

            if "error" in result:
                if "not found" in result["error"].lower():
                    metrics.set_error(ValueError(result["error"]))
                    metrics.report("api_get_document_neighbors_failed")
                    raise HTTPException(status_code=404, detail=result["error"])
                else:
                    metrics.set_error(RuntimeError(result["error"]))
                    metrics.report("api_get_document_neighbors_failed")
                    raise HTTPException(status_code=500, detail=result["error"])

            neighbors_found = len(result.get("neighbors", []))
            query_text_length = len(result.get("query_text", ""))

            metrics.add_metric("neighbors_found", neighbors_found)
            metrics.add_metric("query_text_length", query_text_length)
            metrics.set_success(True)
            metrics.report("api_get_document_neighbors_completed")
            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_get_document_neighbors_failed")
            raise HTTPException(status_code=500, detail=str(e)) from None
