"""
Document factory utilities for generating data structures aligned with
LlamaIndexService outputs and the document routes.

These builders produce:
- Raw document entries as returned by LlamaIndexService.query_documents_by_metadata
- Route-formatted document lists for GET /api/documents
- Analysis payloads for GET /api/documents/{id}/llamaindex-analysis
- Chunk payloads for GET /api/documents/{id}/llamaindex-chunks
- Neighbor payloads for GET /api/documents/{id}/llamaindex-neighbors
"""

from __future__ import annotations

import math
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .file.file_factory import TestFile


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text_preview(text: str, max_len: int = 200) -> str:
    """Return a single-line preview by stripping newlines and truncating with ellipsis."""
    if not text:
        return ""
    one_line = text.replace("\n", " ").strip()
    return one_line if len(one_line) <= max_len else one_line[: max_len - 3] + "..."


class DocumentFactory:
    """Builders for document- and route-shaped payloads used in tests."""

    @classmethod
    def build_llamaindex_metadata(
        cls,
        *,
        document_id: Optional[str] = None,
        file_hash: str = "",
        original_path: str = "",
        mime_type: str = "text/plain",
        size_bytes: int = 0,
        status: str = "ready",
        tags: Optional[List[str]] = None,
        has_content: bool = True,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "document_id": document_id or f"doc_{uuid.uuid4().hex[:12]}",
            "file_hash": file_hash,
            "original_path": original_path,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "created_at": _now_iso(),
            "modified_at": None,
            "status": status,
            "error_message": None,
            "word_count": None,
            "language": "en",
            "extraction_method": None,
            "has_content": has_content,
            "tags": tags or [],
        }
        if extra:
            metadata.update(extra)
        return metadata

    @classmethod
    def from_test_file(
        cls,
        tf: TestFile,
        *,
        document_id: Optional[str] = None,
        status: str = "ready",
        extra_metadata: Optional[Dict[str, Any]] = None,
        text_content: Optional[str] = None,
        node_count: int = 3,
    ) -> Dict[str, Any]:
        """Create a raw document entry from a TestFile for service/query tests."""
        doc_id = document_id or f"doc_{uuid.uuid4().hex[:12]}"
        text = (text_content if text_content is not None else tf.content.decode("utf-8", errors="ignore"))
        metadata = cls.build_llamaindex_metadata(
            document_id=doc_id,
            file_hash=tf.hash,
            original_path=tf.filename,
            mime_type=tf.mime_type,
            size_bytes=tf.size,
            status=status,
            tags=getattr(tf, "expected_tags", []),
            has_content=bool(text),
            extra=extra_metadata or {},
        )
        return {
            "document_id": doc_id,
            "metadata": metadata,
            "text_preview": _text_preview(text, 200),
            "node_count": node_count,
        }

    @classmethod
    def build_raw_document(
        cls,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        text_preview: str = "",
        node_count: int = 1,
    ) -> Dict[str, Any]:
        if not metadata:
            metadata = cls.build_llamaindex_metadata()
        return {
            "document_id": metadata.get("document_id"),
            "metadata": metadata,
            "text_preview": text_preview,
            "node_count": node_count,
        }

    @classmethod
    def format_documents_for_route(
        cls, raw_documents: List[Dict[str, Any]], *, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        formatted_documents: List[Dict[str, Any]] = []
        for doc in raw_documents:
            metadata = doc.get("metadata", {})
            formatted = {
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
            }
            formatted_documents.append(formatted)

        return {
            "documents": formatted_documents,
            "total": len(formatted_documents),
            "limit": limit,
            "offset": offset,
        }

    @classmethod
    def build_analysis_response(
        cls,
        document_id: str,
        *,
        status: str = "indexed",
        total_chunks: int = 5,
        total_chars: int = 2000,
        total_words: int = 350,
        avg_chunk_size: int = 400,
        embedding_model: str = "all-MiniLM-L6-v2",
        embedding_dimension: Optional[int] = 384,
        storage_docstore_type: str = "SimpleDocumentStore",
        storage_vector_store_type: str = "SimpleVectorStore",
        text_splitter: str = "SentenceSplitter",
        original_metadata: Optional[Dict[str, Any]] = None,
        chunks_preview: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if chunks_preview is None:
            chunks_preview = [
                cls.build_chunk(
                    node_id=f"node_{i}",
                    document_id=document_id,
                    text=f"Chunk {i} preview text for document {document_id}.",
                    chunk_index=i,
                )
                for i in range(min(total_chunks, 3))
            ]

        return {
            "document_id": document_id,
            "status": status,
            "original_metadata": original_metadata or {},
            "processing_info": {
                "total_chunks": total_chunks,
                "total_chars": total_chars,
                "total_words": total_words,
                "avg_chunk_size": avg_chunk_size,
                "embedding_model": embedding_model,
                "embedding_dimension": embedding_dimension,
            },
            "storage_info": {
                "docstore_type": storage_docstore_type,
                "vector_store_type": storage_vector_store_type,
                "text_splitter": text_splitter,
            },
            "chunks_preview": chunks_preview,
        }

    @classmethod
    def build_chunk(
        cls,
        *,
        node_id: Optional[str] = None,
        document_id: Optional[str] = None,
        text: str = "",
        chunk_index: int = 0,
        start_char: Optional[int] = None,
        end_char: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        relationships: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        text_length = len(text)
        word_count = len(text.split()) if text else 0
        return {
            "chunk_index": chunk_index,
            "node_id": node_id or f"node_{uuid.uuid4().hex[:8]}",
            "text": text,
            "text_length": text_length,
            "word_count": word_count,
            "start_char": start_char if start_char is not None else chunk_index * 200,
            "end_char": end_char if end_char is not None else (chunk_index + 1) * 200,
            "metadata": metadata or ({"document_id": document_id} if document_id else {}),
            "relationships": relationships or {},
        }

    @classmethod
    def build_chunks_response(
        cls,
        document_id: str,
        chunks: List[Dict[str, Any]],
        *,
        total: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        total_chunks = total if total is not None else len(chunks)
        return {
            "document_id": document_id,
            "chunks": chunks,
            "total": total_chunks,
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < total_chunks,
        }

    @classmethod
    def build_neighbor(
        cls,
        document_id: str,
        *,
        similarity_score: float = 0.85,
        text_preview: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "document_id": document_id,
            "similarity_score": float(similarity_score),
            "text_preview": text_preview or _text_preview("Neighbor document content preview."),
            "metadata": metadata or {},
        }

    @classmethod
    def build_neighbors_response(
        cls,
        document_id: str,
        neighbors: List[Dict[str, Any]],
        *,
        query_text: str = "",
    ) -> Dict[str, Any]:
        return {
            "document_id": document_id,
            "neighbors": neighbors,
            "total_found": len(neighbors),
            "query_text": _text_preview(query_text or f"Representative content from {document_id}"),
        }

    @classmethod
    def build_raw_documents_set(cls, count: int = 3) -> List[Dict[str, Any]]:
        docs: List[Dict[str, Any]] = []
        for i in range(count):
            meta = cls.build_llamaindex_metadata(
                document_id=f"doc_{uuid.uuid4().hex[:12]}",
                file_hash=f"hash_{uuid.uuid4().hex[:10]}",
                original_path=f"/tmp/doc_{i}.txt",
                size_bytes=1024 + i * 10,
                status="ready",
                tags=["test", f"tag{i}"],
            )
            docs.append(
                cls.build_raw_document(
                    metadata=meta, text_preview=f"Document {i} preview text.", node_count=3
                )
            )
        return docs

    @classmethod
    def build_neighbors_set(cls, base_document_id: str, count: int = 3) -> Dict[str, Any]:
        neighbors = [
            cls.build_neighbor(
                document_id=f"doc_{uuid.uuid4().hex[:12]}",
                similarity_score=0.9 - i * 0.1,
                text_preview=f"Neighbor {i} text preview.",
            )
            for i in range(count)
        ]
        return cls.build_neighbors_response(
            document_id=base_document_id,
            neighbors=neighbors,
            query_text=f"Representative content from {base_document_id}",
        )

    # -----------------------------------
    # Integration with TestFile factory
    # -----------------------------------

    @classmethod
    def build_semantic_node_from_test_file(
        cls,
        tf: TestFile,
        *,
        score: float = 0.85,
        text: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a node compatible with llamaindex_service.retrieve_similar output.

        IndexSearchTool expects nodes shaped like:
          { "text": str, "score": float, "metadata": { ... } }
        """
        content_text = (
            text if text is not None else tf.content.decode("utf-8", errors="ignore")
        )
        meta: Dict[str, Any] = {
            "document_id": tf.test_id,
            "mime_type": tf.mime_type,
            "size_bytes": tf.size,
            "original_path": tf.filename,
            "tags": getattr(tf, "expected_tags", []),
            "created_at": tf.metadata.get("created_at"),
        }
        if extra_metadata:
            meta.update(extra_metadata)
        return {
            "text": content_text,
            "score": float(score),
            "metadata": meta,
        }

    @classmethod
    def build_semantic_nodes_for_files(
        cls, files: List[TestFile], *, start_score: float = 0.9, step: float = 0.05
    ) -> List[Dict[str, Any]]:
        nodes: List[Dict[str, Any]] = []
        cur = start_score
        for tf in files:
            nodes.append(cls.build_semantic_node_from_test_file(tf, score=cur))
            cur = max(0.0, cur - step)
        return nodes

    @classmethod
    def build_search_result_from_test_file(
        cls,
        tf: TestFile,
        *,
        match_type: str = "semantic",
        score: float = 0.85,
        include_content: bool = False,
        snippet_len: int = 300,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a result shaped like IndexSearchTool final output entry."""
        text = tf.content.decode("utf-8", errors="ignore")
        snippet = cls._text_preview(text, snippet_len)
        meta_created = tf.metadata.get("created_at", _now_iso())
        tags = getattr(tf, "expected_tags", [])
        result = {
            "document_id": tf.test_id,
            "title": tf.filename.split("/")[-1],
            "snippet": snippet,
            "score": float(score),
            "mime_type": tf.mime_type,
            "size_bytes": tf.size,
            "match_type": match_type,
            "created_at": meta_created,
            "ingested_at": meta_created,
            "tags": tags,
        }
        if include_content:
            result["content"] = text
        if extra_metadata:
            # Attach extra metadata at top-level as some route tests do
            result.update(extra_metadata)
        return result

    @classmethod
    def build_search_results_for_files(
        cls,
        files: List[TestFile],
        *,
        match_type: str = "semantic",
        start_score: float = 0.9,
        step: float = 0.05,
        include_content: bool = False,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        cur = start_score
        for tf in files:
            results.append(
                cls.build_search_result_from_test_file(
                    tf,
                    match_type=match_type,
                    score=cur,
                    include_content=include_content,
                )
            )
            cur = max(0.0, cur - step)
        return results

    @classmethod
    def build_chunks_from_test_file(
        cls,
        tf: TestFile,
        *,
        chunk_size: Optional[int] = None,
        overlap: int = 100,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Split a TestFile's text content into chunk structures similar to
        LlamaIndexService.get_document_chunks output.
        """
        text = tf.content.decode("utf-8", errors="ignore")
        if chunk_size is None:
            # Respect test override, else align with service default
            try:
                chunk_size = int(os.getenv("TEST_CHUNK_SIZE", "800"))
            except (TypeError, ValueError):
                chunk_size = 800

        # Build windowed chunks
        chunks: List[Dict[str, Any]] = []
        start = 0
        idx = 0
        n = len(text)
        while start < n:
            end = min(n, start + chunk_size)
            chunk_text = text[start:end]
            chunk = cls.build_chunk(
                node_id=f"node_{tf.test_id}_{idx}",
                document_id=tf.test_id,
                text=chunk_text,
                chunk_index=idx,
                start_char=start,
                end_char=end,
                metadata={
                    "document_id": tf.test_id,
                    "mime_type": tf.mime_type,
                    "size_bytes": tf.size,
                    "original_path": tf.filename,
                    "tags": getattr(tf, "expected_tags", []),
                },
            )
            chunks.append(chunk)
            if end == n:
                break
            # advance with overlap
            start = end - max(0, min(overlap, chunk_size - 1))
            idx += 1

        total = len(chunks)
        lo = offset
        hi = total if limit is None else min(total, offset + limit)
        window = chunks[lo:hi]
        return cls.build_chunks_response(
            document_id=tf.test_id, chunks=window, total=total, limit=hi - lo, offset=lo
        )

    @classmethod
    def build_ingest_request_from_test_file(
        cls,
        tf: TestFile,
        *,
        temp_path: Optional[str] = None,
        tags: Optional[List[str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build a JSON body for POST /api/ingest using a TestFile persisted to disk.

        temp_path should be the filesystem path where the test wrote tf.content.
        """
        if not temp_path:
            # For safety, tests should pass explicit temp_path from TempFileManager
            temp_path = tf.metadata.get("temp_path") or tf.metadata.get("path") or tf.filename
        base_meta = {
            "original_filename": tf.filename,
        }
        if extra_metadata:
            base_meta.update(extra_metadata)
        return {
            "path": str(temp_path),
            "tags": tags if tags is not None else getattr(tf, "expected_tags", []),
            "metadata": base_meta,
        }


def create_medical_documents() -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for title in [
        "Patient Care Guidelines",
        "Lab Results Analysis",
        "Blood Pressure Monitoring Report",
    ]:
        meta = DocumentFactory.build_llamaindex_metadata(
            mime_type="application/pdf" if "Guidelines" in title else "text/plain",
            tags=["medical"],
            extra={"title": title, "category": "medical"},
        )
        docs.append(
            DocumentFactory.build_raw_document(
                metadata=meta, text_preview=f"{title} preview text.", node_count=3
            )
        )
    return docs


def create_financial_documents() -> List[Dict[str, Any]]:
    docs: List[Dict[str, Any]] = []
    for title in [
        "Bank of America Quarterly Report",
        "Mortgage Rate Information",
    ]:
        meta = DocumentFactory.build_llamaindex_metadata(
            mime_type="application/pdf" if "Report" in title else "text/plain",
            tags=["financial"],
            extra={"title": title, "category": "financial"},
        )
        docs.append(
            DocumentFactory.build_raw_document(
                metadata=meta, text_preview=f"{title} preview text.", node_count=3
            )
        )
    return docs


def create_mixed_document_set() -> List[Dict[str, Any]]:
    documents: List[Dict[str, Any]] = []
    documents.extend(create_medical_documents()[:2])
    documents.extend(create_financial_documents())
    meta = DocumentFactory.build_llamaindex_metadata(
        mime_type="text/plain",
        tags=["general", "testing"],
        extra={"title": "General Information Document", "category": "general"},
    )
    documents.append(
        DocumentFactory.build_raw_document(
            metadata=meta,
            text_preview="This document contains general information for testing purposes...",
            node_count=2,
        )
    )
    return documents
