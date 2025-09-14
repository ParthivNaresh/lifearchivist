"""
Tests for GET /api/documents/{document_id}/llamaindex-analysis focusing on success, service unavailable, not found, and exception paths.
"""

import pytest
from unittest.mock import AsyncMock

from factories.document_factory import DocumentFactory


@pytest.mark.asyncio
async def test_document_analysis_success_returns_payload(async_client, test_server, monkeypatch):
    document_id = "doc_test123"
    analysis = DocumentFactory.build_analysis_response(
        document_id=document_id,
        status="indexed",
        total_chunks=4,
        total_chars=1500,
        total_words=250,
        avg_chunk_size=375,
        embedding_model="all-MiniLM-L6-v2",
        embedding_dimension=384,
        storage_docstore_type="SimpleDocumentStore",
        storage_vector_store_type="SimpleVectorStore",
        text_splitter="SentenceSplitter",
    )
    monkeypatch.setattr(
        test_server.llamaindex_service,
        "get_document_analysis",
        AsyncMock(return_value=analysis),
    )
    resp = await async_client.get(f"/api/documents/{document_id}/llamaindex-analysis")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("document_id") == document_id
    assert data.get("status") == "indexed"
    p = data.get("processing_info", {})
    for k in ["total_chunks", "total_chars", "total_words", "avg_chunk_size", "embedding_model", "embedding_dimension"]:
        assert k in p
    s = data.get("storage_info", {})
    for k in ["docstore_type", "vector_store_type", "text_splitter"]:
        assert k in s
    cp = data.get("chunks_preview", [])
    assert isinstance(cp, list)


@pytest.mark.asyncio
async def test_document_analysis_service_unavailable(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server, "llamaindex_service", None)
    resp = await async_client.get("/api/documents/doc_x/llamaindex-analysis")
    assert resp.status_code == 503
    data = resp.json()
    assert "LlamaIndex service not available" in str(data.get("detail", ""))


@pytest.mark.asyncio
async def test_document_analysis_not_found_returns_404(async_client, test_server, monkeypatch):
    async def _not_found(doc_id):
        return {"error": f"Document {doc_id} not found in LlamaIndex"}

    monkeypatch.setattr(test_server.llamaindex_service, "get_document_analysis", AsyncMock(side_effect=_not_found))
    resp = await async_client.get("/api/documents/doc_missing/llamaindex-analysis")
    assert resp.status_code == 404
    data = resp.json()
    assert "not found" in str(data.get("detail", "")).lower()


@pytest.mark.asyncio
async def test_document_analysis_exception_returns_500(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server.llamaindex_service, "get_document_analysis", AsyncMock(side_effect=Exception("boom")))
    resp = await async_client.get("/api/documents/doc_err/llamaindex-analysis")
    assert resp.status_code == 500
    data = resp.json()
    assert "boom" in str(data.get("detail", ""))
