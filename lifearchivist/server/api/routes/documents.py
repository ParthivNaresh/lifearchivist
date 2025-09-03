"""
Document management endpoints.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from lifearchivist.utils.logging import log_context
from lifearchivist.utils.logging.structured import MetricsCollector, log_event

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

        log_event(
            "api_list_documents_started",
            {
                "status_filter": status,
                "limit": limit,
                "offset": offset,
                "has_llamaindex_service": server.llamaindex_service is not None,
            },
        )

        try:
            if not server.llamaindex_service:
                log_event("api_list_documents_service_unavailable", {})
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

            log_event(
                "api_list_documents_successful",
                {
                    "documents_count": len(documents),
                    "status_filter": status,
                    "limit": limit,
                    "offset": offset,
                },
            )

            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_list_documents_failed")

            log_event(
                "api_list_documents_exception",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "status_filter": status,
                    "limit": limit,
                },
            )
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

        log_event(
            "api_clear_all_documents_started",
            {
                "has_llamaindex_service": server.llamaindex_service is not None,
                "has_vault": server.vault is not None,
                "has_progress_manager": server.progress_manager is not None,
            },
        )

        try:
            # Step 1: Clear LlamaIndex data
            log_event("clear_llamaindex_phase_started", {})
            llamaindex_metrics = {}
            if server.llamaindex_service:
                try:
                    llamaindex_metrics = (
                        await server.llamaindex_service.clear_all_data()
                    )
                    log_event(
                        "clear_llamaindex_completed",
                        {
                            "storage_files_deleted": llamaindex_metrics.get(
                                "storage_files_deleted", 0
                            ),
                            "storage_bytes_reclaimed": llamaindex_metrics.get(
                                "storage_bytes_reclaimed", 0
                            ),
                        },
                    )
                except Exception as llamaindex_error:
                    llamaindex_metrics = {"error": str(llamaindex_error)}
                    log_event(
                        "clear_llamaindex_failed",
                        {
                            "error_type": type(llamaindex_error).__name__,
                            "error_message": str(llamaindex_error),
                        },
                    )
            else:
                llamaindex_metrics = {"skipped": True}
                log_event(
                    "clear_llamaindex_skipped", {"reason": "service_not_available"}
                )

            # Step 2: Clear vault files
            log_event("clear_vault_phase_started", {})
            vault_metrics = await server.vault.clear_all_files(
                []
            )  # Empty list = clear all
            log_event(
                "clear_vault_completed",
                {
                    "files_deleted": vault_metrics["files_deleted"],
                    "bytes_reclaimed": vault_metrics["bytes_reclaimed"],
                    "mb_reclaimed": vault_metrics["bytes_reclaimed"] / (1024 * 1024),
                },
            )

            # Step 3: Clear progress tracking data
            log_event("clear_progress_phase_started", {})
            progress_metrics = {}
            if server.progress_manager:
                try:
                    progress_metrics = (
                        await server.progress_manager.clear_all_progress()
                    )
                    log_event(
                        "clear_progress_completed",
                        {
                            "redis_keys_deleted": progress_metrics.get(
                                "total_keys_deleted", 0
                            ),
                        },
                    )
                except Exception as progress_error:
                    progress_metrics = {"error": str(progress_error)}
                    log_event(
                        "clear_progress_failed",
                        {
                            "error_type": type(progress_error).__name__,
                            "error_message": str(progress_error),
                        },
                    )
            else:
                progress_metrics = {"skipped": True}
                log_event("clear_progress_skipped", {"reason": "service_not_available"})

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

            log_event(
                "api_clear_all_documents_successful",
                {
                    "total_files_deleted": total_files_deleted,
                    "total_mb_reclaimed": result["summary"]["total_mb_reclaimed"],
                    "vault_files_deleted": vault_files_deleted,
                    "llamaindex_files_deleted": llamaindex_metrics.get(
                        "storage_files_deleted", 0
                    ),
                },
            )

            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_clear_all_documents_failed")

            log_event(
                "api_clear_all_documents_exception",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
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

        log_event(
            "api_get_document_analysis_started",
            {
                "document_id": document_id,
                "has_llamaindex_service": server.llamaindex_service is not None,
            },
        )

        try:
            if not server.llamaindex_service:
                log_event(
                    "api_get_document_analysis_service_unavailable",
                    {"document_id": document_id},
                )
                metrics.set_error(RuntimeError("LlamaIndex service not available"))
                metrics.report("api_get_document_analysis_failed")
                raise HTTPException(
                    status_code=503, detail="LlamaIndex service not available"
                )

            result = await server.llamaindex_service.get_document_analysis(document_id)

            if "error" in result:
                log_event(
                    "api_get_document_analysis_not_found",
                    {"document_id": document_id, "error": result["error"]},
                )
                metrics.set_error(ValueError(result["error"]))
                metrics.report("api_get_document_analysis_failed")
                raise HTTPException(status_code=404, detail=result["error"])

            metrics.add_metric("analysis_status", result.get("status", "unknown"))
            metrics.add_metric("chunks_count", len(result.get("chunks_preview", [])))
            metrics.set_success(True)
            metrics.report("api_get_document_analysis_completed")

            log_event(
                "api_get_document_analysis_successful",
                {
                    "document_id": document_id,
                    "status": result.get("status", "unknown"),
                    "chunks_count": len(result.get("chunks_preview", [])),
                },
            )

            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_get_document_analysis_failed")

            log_event(
                "api_get_document_analysis_exception",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
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

        log_event(
            "api_get_document_chunks_started",
            {
                "document_id": document_id,
                "limit": limit,
                "offset": offset,
                "has_llamaindex_service": server.llamaindex_service is not None,
            },
        )

        try:
            if not server.llamaindex_service:
                log_event(
                    "api_get_document_chunks_service_unavailable",
                    {"document_id": document_id},
                )
                metrics.set_error(RuntimeError("LlamaIndex service not available"))
                metrics.report("api_get_document_chunks_failed")
                raise HTTPException(
                    status_code=503, detail="LlamaIndex service not available"
                )

            # Validate pagination parameters
            if limit < 1 or limit > 1000:
                log_event(
                    "api_get_document_chunks_invalid_limit",
                    {"document_id": document_id, "limit": limit},
                )
                metrics.set_error(ValueError("Invalid limit parameter"))
                metrics.report("api_get_document_chunks_failed")
                raise HTTPException(
                    status_code=400, detail="Limit must be between 1 and 1000"
                )
            if offset < 0:
                log_event(
                    "api_get_document_chunks_invalid_offset",
                    {"document_id": document_id, "offset": offset},
                )
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
                    log_event(
                        "api_get_document_chunks_not_found",
                        {"document_id": document_id, "error": result["error"]},
                    )
                    metrics.set_error(ValueError(result["error"]))
                    metrics.report("api_get_document_chunks_failed")
                    raise HTTPException(status_code=404, detail=result["error"])
                else:
                    log_event(
                        "api_get_document_chunks_error",
                        {"document_id": document_id, "error": result["error"]},
                    )
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

            log_event(
                "api_get_document_chunks_successful",
                {
                    "document_id": document_id,
                    "chunks_returned": chunks_returned,
                    "total_chunks": total_chunks,
                    "has_more": has_more,
                    "limit": limit,
                    "offset": offset,
                },
            )

            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_get_document_chunks_failed")

            log_event(
                "api_get_document_chunks_exception",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "limit": limit,
                    "offset": offset,
                },
            )
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

        log_event(
            "api_get_document_neighbors_started",
            {
                "document_id": document_id,
                "top_k": top_k,
                "has_llamaindex_service": server.llamaindex_service is not None,
            },
        )

        try:
            if not server.llamaindex_service:
                log_event(
                    "api_get_document_neighbors_service_unavailable",
                    {"document_id": document_id},
                )
                metrics.set_error(RuntimeError("LlamaIndex service not available"))
                metrics.report("api_get_document_neighbors_failed")
                raise HTTPException(
                    status_code=503, detail="LlamaIndex service not available"
                )

            # Validate parameters
            if top_k < 1 or top_k > 100:
                log_event(
                    "api_get_document_neighbors_invalid_top_k",
                    {"document_id": document_id, "top_k": top_k},
                )
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
                    log_event(
                        "api_get_document_neighbors_not_found",
                        {"document_id": document_id, "error": result["error"]},
                    )
                    metrics.set_error(ValueError(result["error"]))
                    metrics.report("api_get_document_neighbors_failed")
                    raise HTTPException(status_code=404, detail=result["error"])
                else:
                    log_event(
                        "api_get_document_neighbors_error",
                        {"document_id": document_id, "error": result["error"]},
                    )
                    metrics.set_error(RuntimeError(result["error"]))
                    metrics.report("api_get_document_neighbors_failed")
                    raise HTTPException(status_code=500, detail=result["error"])

            neighbors_found = len(result.get("neighbors", []))
            query_text_length = len(result.get("query_text", ""))

            metrics.add_metric("neighbors_found", neighbors_found)
            metrics.add_metric("query_text_length", query_text_length)
            metrics.set_success(True)
            metrics.report("api_get_document_neighbors_completed")

            log_event(
                "api_get_document_neighbors_successful",
                {
                    "document_id": document_id,
                    "neighbors_found": neighbors_found,
                    "top_k": top_k,
                    "query_text_length": query_text_length,
                },
            )

            return result

        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_get_document_neighbors_failed")

            log_event(
                "api_get_document_neighbors_exception",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "top_k": top_k,
                },
            )
            raise HTTPException(status_code=500, detail=str(e)) from None
