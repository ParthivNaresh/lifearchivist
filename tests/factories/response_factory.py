"""
Factory for creating API response objects for testing.

All builders align with actual route/service outputs in the codebase and
integrate with DocumentFactory where appropriate. No legacy shapes are retained.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .document_factory import DocumentFactory


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResponseFactory:
    """Factory for creating aligned API response objects for testing."""

    # ------------------------------------------------------------------
    # Upload / Ingest
    # ------------------------------------------------------------------
    @classmethod
    def create_upload_response(
        cls,
        *,
        file_id: Optional[str] = None,
        file_hash: Optional[str] = None,
        size: int = 1024,
        mime_type: str = "text/plain",
        original_path: str = "test.txt",
        vault_path: str = "/tmp/test_vault/content/ab/cd/abcdef.txt",
        deduped: bool = False,
        created_at: Optional[str] = None,
        modified_at: Optional[str] = None,
        status: str = "ready",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Aligned with file.import success result returned by /api/upload or /api/ingest."""
        fid = file_id or f"file_{uuid.uuid4().hex[:12]}"
        fh = file_hash or f"hash_{uuid.uuid4().hex}"
        created = created_at or _now_iso()
        modified = modified_at or _now_iso()
        resp: Dict[str, Any] = {
            "file_id": fid,
            "hash": fh,
            "size": size,
            "mime_type": mime_type,
            "status": status,
            "original_path": original_path,
            "vault_path": vault_path,
            "created_at": created,
            "modified_at": modified,
            "deduped": deduped,
        }
        if extra:
            resp.update(extra)
        return resp

    @classmethod
    def create_ingest_response(
        cls,
        **kwargs,
    ) -> Dict[str, Any]:
        """Alias to upload response since /api/ingest returns the tool result directly."""
        return cls.create_upload_response(**kwargs)

    @classmethod
    def create_bulk_ingest_response(
        cls,
        *,
        total_files: int = 3,
        successful_paths: Optional[List[str]] = None,
        failed_paths: Optional[List[str]] = None,
        folder_path: str = "/tmp/test_folder",
    ) -> Dict[str, Any]:
        """Aligned with /api/bulk-ingest output."""
        if successful_paths is None:
            successful_paths = [f"{folder_path}/file_{i+1}.txt" for i in range(2)]
        if failed_paths is None:
            failed_paths = [f"{folder_path}/failed_{i+1}.txt" for i in range(1)]

        results: List[Dict[str, Any]] = []
        for p in successful_paths:
            results.append(
                {
                    "file_path": p,
                    "success": True,
                    "file_id": f"bulk_{uuid.uuid4().hex[:12]}",
                    "status": "ready",
                }
            )
        for p in failed_paths:
            results.append(
                {
                    "file_path": p,
                    "success": False,
                    "error": "File processing failed",
                }
            )

        return {
            "success": True,
            "total_files": total_files,
            "successful_count": len(successful_paths),
            "failed_count": len(failed_paths),
            "folder_path": folder_path,
            "results": results,
        }

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    @classmethod
    def create_search_response(
        cls,
        *,
        results: Optional[List[Dict[str, Any]]] = None,
        total: Optional[int] = None,
        query_time_ms: float = 45.0,
    ) -> Dict[str, Any]:
        """Aligned with IndexSearchTool.execute output returned by /api/search.
        Each result item should have: document_id, title, snippet, score, mime_type,
        size_bytes, word_count, match_type, created_at, ingested_at, tags, optional content.
        """
        if results is None:
            results = []
            for i in range(3):
                results.append(
                    {
                        "document_id": f"doc_{uuid.uuid4().hex[:12]}",
                        "title": f"Doc_{i+1}.txt",
                        "snippet": f"Snippet for result {i+1}...",
                        "score": max(0.0, 0.9 - i * 0.1),
                        "mime_type": "text/plain",
                        "size_bytes": 1024 + i * 100,
                        "word_count": 200 + i * 10,
                        "match_type": "semantic",
                        "created_at": _now_iso(),
                        "ingested_at": _now_iso(),
                        "tags": ["test"],
                    }
                )
        return {
            "results": results,
            "total": len(results) if total is None else total,
            "query_time_ms": query_time_ms,
        }

    # ------------------------------------------------------------------
    # Documents list
    # ------------------------------------------------------------------
    @classmethod
    def create_documents_list_response(
        cls,
        *,
        raw_documents: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Aligned with /api/documents response using DocumentFactory for formatting."""
        if raw_documents is None:
            raw_documents = []
            for i in range(3):
                meta = DocumentFactory.build_llamaindex_metadata(
                    document_id=f"doc_{uuid.uuid4().hex[:12]}",
                    file_hash=f"hash_{uuid.uuid4().hex[:16]}",
                    original_path=f"/tmp/doc_{i+1}.txt",
                    mime_type="text/plain",
                    size_bytes=1024 + i * 20,
                    status="ready",
                    tags=["test"],
                )
                raw_documents.append(
                    DocumentFactory.build_raw_document(
                        metadata=meta, text_preview=f"Document {i+1} preview...", node_count=3
                    )
                )
        return DocumentFactory.format_documents_for_route(
            raw_documents, limit=limit, offset=offset
        )

    # ------------------------------------------------------------------
    # Analysis / Chunks / Neighbors
    # ------------------------------------------------------------------
    @classmethod
    def create_document_analysis_response(
        cls,
        *,
        document_id: Optional[str] = None,
        total_chunks: int = 5,
        total_chars: int = 2000,
        total_words: int = 350,
        avg_chunk_size: int = 400,
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_dimension: Optional[int] = 384,
        text_splitter: str = "SentenceSplitter",
    ) -> Dict[str, Any]:
        """Aligned with LlamaIndexService.get_document_analysis output."""
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        return DocumentFactory.build_analysis_response(
            document_id=doc_id,
            status="indexed",
            total_chunks=total_chunks,
            total_chars=total_chars,
            total_words=total_words,
            avg_chunk_size=avg_chunk_size,
            embedding_model=embedding_model,
            embedding_dimension=embedding_dimension,
            storage_docstore_type="SimpleDocumentStore",
            storage_vector_store_type="SimpleVectorStore",
            text_splitter=text_splitter,
        )

    @classmethod
    def create_document_chunks_response(
        cls,
        *,
        document_id: Optional[str] = None,
        chunks_count: int = 10,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Aligned with LlamaIndexService.get_document_chunks output."""
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        # Build chunks
        chunks: List[Dict[str, Any]] = []
        for i in range(min(chunks_count, limit)):
            idx = offset + i
            chunks.append(
                DocumentFactory.build_chunk(
                    node_id=f"node_{uuid.uuid4().hex[:8]}",
                    document_id=doc_id,
                    text=f"Chunk {idx} content...",
                    chunk_index=idx,
                    start_char=idx * 200,
                    end_char=(idx + 1) * 200,
                )
            )
        return DocumentFactory.build_chunks_response(
            document_id=doc_id, chunks=chunks, total=chunks_count, limit=limit, offset=offset
        )

    @classmethod
    def create_document_neighbors_response(
        cls,
        *,
        document_id: Optional[str] = None,
        neighbors_count: int = 3,
    ) -> Dict[str, Any]:
        """Aligned with LlamaIndexService.get_document_neighbors output."""
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        neighbors: List[Dict[str, Any]] = []
        for i in range(neighbors_count):
            neighbors.append(
                DocumentFactory.build_neighbor(
                    document_id=f"doc_{uuid.uuid4().hex[:12]}",
                    similarity_score=max(0.0, 0.9 - i * 0.1),
                    text_preview=f"Neighbor {i+1} preview...",
                )
            )
        return DocumentFactory.build_neighbors_response(doc_id, neighbors)

    # ------------------------------------------------------------------
    # Vault
    # ------------------------------------------------------------------
    @classmethod
    def create_vault_info_response(
        cls,
        *,
        vault_path: str = "/tmp/test_vault",
        content_files: int = 10,
        thumbnails_files: int = 2,
        temp_files: int = 1,
        exports_files: int = 0,
        content_bytes: int = 1024 * 1024,
        thumbnails_bytes: int = 256 * 1024,
        temp_bytes: int = 0,
        exports_bytes: int = 0,
    ) -> Dict[str, Any]:
        """Aligned with /api/vault/info output (nested directories structure)."""
        directories = {
            "content": {
                "file_count": content_files,
                "total_size_bytes": content_bytes,
                "total_size_mb": round(content_bytes / (1024 * 1024), 2),
            },
            "thumbnails": {
                "file_count": thumbnails_files,
                "total_size_bytes": thumbnails_bytes,
                "total_size_mb": round(thumbnails_bytes / (1024 * 1024), 2),
            },
            "temp": {
                "file_count": temp_files,
                "total_size_bytes": temp_bytes,
                "total_size_mb": round(temp_bytes / (1024 * 1024), 2),
            },
            "exports": {
                "file_count": exports_files,
                "total_size_bytes": exports_bytes,
                "total_size_mb": round(exports_bytes / (1024 * 1024), 2),
            },
        }
        total_files = content_files + thumbnails_files + temp_files + exports_files
        total_size_bytes = content_bytes + thumbnails_bytes + temp_bytes + exports_bytes
        return {
            "vault_path": vault_path,
            "directories": directories,
            "total_files": total_files,
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_bytes / (1024 * 1024), 2),
        }

    @classmethod
    def create_vault_files_response(
        cls,
        *,
        files_count: int = 5,
        directory: str = "content",
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Aligned with /api/vault/files output."""
        files: List[Dict[str, Any]] = []
        for i in range(files_count):
            file_hash = f"{uuid.uuid4().hex}"
            files.append(
                {
                    "path": f"{directory}/{file_hash[:2]}/{file_hash[2:4]}/{file_hash[4:]}.txt",
                    "full_path": f"/tmp/test_vault/{directory}/{file_hash[:2]}/{file_hash[2:4]}/{file_hash[4:]}.txt",
                    "hash": file_hash,
                    "extension": "txt",
                    "size_bytes": 1024 + i * 100,
                    "created_at": datetime.now(timezone.utc).timestamp(),
                    "modified_at": datetime.now(timezone.utc).timestamp(),
                    "database_record": None,
                }
            )
        return {
            "files": files,
            "total": files_count,
            "directory": directory,
            "limit": limit,
            "offset": offset,
        }

    # ------------------------------------------------------------------
    # Progress & Clear-all
    # ------------------------------------------------------------------
    @classmethod
    def create_progress_response(
        cls,
        *,
        file_id: Optional[str] = None,
        stage: str = "upload",
        progress: float = 75.0,
        message: Optional[str] = None,
        eta_seconds: Optional[int] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Aligned with ProgressUpdate.to_dict as returned by /api/upload/{file_id}/progress."""
        fid = file_id or f"file_{uuid.uuid4().hex[:12]}"
        return {
            "file_id": fid,
            "stage": stage,
            "progress": progress,
            "message": message or f"{stage} in progress",
            "timestamp": datetime.now(timezone.utc).timestamp(),
            "eta_seconds": eta_seconds,
            "error": error,
            "metadata": metadata,
        }

    @classmethod
    def create_clear_all_response(
        cls,
        *,
        total_files_deleted: int = 15,
        total_bytes_reclaimed: int = 1536000,
        vault_metrics: Optional[Dict[str, Any]] = None,
        llamaindex_metrics: Optional[Dict[str, Any]] = None,
        progress_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Aligned with DELETE /api/documents output."""
        vault_metrics = vault_metrics or {
            "files_deleted": 10,
            "bytes_reclaimed": 1024000,
            "directories_cleaned": 2,
            "orphaned_files_deleted": 0,
            "orphaned_bytes_reclaimed": 0,
            "errors": [],
        }
        llamaindex_metrics = llamaindex_metrics or {
            "storage_files_deleted": 5,
            "storage_bytes_reclaimed": 512000,
            "index_reset": True,
            "errors": [],
        }
        progress_metrics = progress_metrics or {
            "progress_keys_deleted": 5,
            "session_keys_deleted": 3,
            "total_keys_deleted": 8,
            "errors": [],
        }
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
            "errors": [
                *vault_metrics.get("errors", []),
                *llamaindex_metrics.get("errors", []),
                *progress_metrics.get("errors", []),
            ],
        }

    # ------------------------------------------------------------------
    # Tags & Topics
    # ------------------------------------------------------------------
    @classmethod
    def create_tags_response(cls, *, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Aligned with /api/tags output."""
        tags = tags or [f"tag{i+1}" for i in range(3)]
        return {"tags": tags, "total": len(tags)}

    @classmethod
    def create_topics_response(
        cls, *, topics: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Aligned with /api/topics output."""
        if topics is None:
            topics = []
            for i in range(3):
                topics.append(
                    {
                        "topic": f"topic_{i+1}",
                        "name": f"Topic {i+1}",
                        "document_count": 10 - i,
                        "keywords": [f"k{i+1}a", f"k{i+1}b"],
                    }
                )
        return {"topics": topics, "total_topics": len(topics), "generated_at": _now_iso()}


# Convenience functions for creating error responses and WebSocket envelopes

def create_error_responses() -> Dict[str, Dict[str, Any]]:
    """Create common error responses for testing."""
    return {
        "bad_request": {"detail": "Invalid request parameters"},
        "not_found": {"detail": "Resource not found"},
        "internal_error": {"detail": "Internal server error occurred"},
        "service_unavailable": {"detail": "Service temporarily unavailable"},
        "validation_error": {
            "detail": [
                {"loc": ["body", "query"], "msg": "field required", "type": "value_error.missing"}
            ]
        },
    }


def create_websocket_responses() -> Dict[str, Dict[str, Any]]:
    """Create WebSocket responses for testing (envelopes match websocket route)."""
    return {
        "tool_result": {
            "type": "tool_result",
            "id": "msg_123",
            "result": {
                "success": True,
                "result": ResponseFactory.create_upload_response(file_id="ws_file_123"),
            },
        },
        "agent_result": {
            "type": "agent_result",
            "id": "agent_msg_456",
            "result": {
                "answer": "WebSocket agent response",
                "confidence": 0.9,
                "sources": [],
                "method": "llamaindex_tool",
                "metadata": {"question_length": 10, "original_sources_count": 0},
            },
        },
        "error_result": {"type": "error", "id": "error_msg_789", "error": "Tool execution failed"},
    }
