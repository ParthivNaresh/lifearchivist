"""
Tests for GET /api/documents/{document_id}/llamaindex-chunks focusing on success, validation errors, service unavailable, not found, and exception paths.
"""

import pytest
from unittest.mock import AsyncMock

from factories.document_factory import DocumentFactory


@pytest.mark.asyncio
async def test_document_chunks_success_with_pagination(async_client, test_server, monkeypatch):
    document_id = "doc_chunky"
    chunks = [
        DocumentFactory.build_chunk(
            node_id=f"node_{i}", document_id=document_id, text=f"chunk {i}", chunk_index=i
        )
        for i in range(5)
    ]
    payload = DocumentFactory.build_chunks_response(document_id, chunks[:2], total=5, limit=2, offset=0)
    monkeypatch.setattr(
        test_server.llamaindex_service,
        "get_document_chunks",
        AsyncMock(return_value=payload),
    )
    resp = await async_client.get(f"/api/documents/{document_id}/llamaindex-chunks", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("document_id") == document_id
    assert data.get("total") == 5
    assert len(data.get("chunks", [])) == 2
    first = data.get("chunks", [])[0]
    for k in [
        "chunk_index",
        "node_id",
        "text",
        "text_length",
        "word_count",
        "start_char",
        "end_char",
        "metadata",
        "relationships",
    ]:
        assert k in first


@pytest.mark.asyncio
@pytest.mark.parametrize("limit,offset", [(0, 0), (1001, 0), (10, -1)])
async def test_document_chunks_validation_errors(async_client, limit, offset):
    resp = await async_client.get(
        "/api/documents/any/llamaindex-chunks", params={"limit": limit, "offset": offset}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_document_chunks_service_unavailable(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server, "llamaindex_service", None)
    resp = await async_client.get("/api/documents/doc_x/llamaindex-chunks")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_document_chunks_not_found_returns_404(async_client, test_server, monkeypatch):
    async def _not_found(document_id: str, limit: int, offset: int):
        return {"error": f"Document {document_id} not found in LlamaIndex"}

    monkeypatch.setattr(test_server.llamaindex_service, "get_document_chunks", AsyncMock(side_effect=_not_found))
    resp = await async_client.get("/api/documents/missing/llamaindex-chunks")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_document_chunks_exception_returns_500(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server.llamaindex_service, "get_document_chunks", AsyncMock(side_effect=Exception("boom")))
    resp = await async_client.get("/api/documents/doc_err/llamaindex-chunks")
    assert resp.status_code == 500
    data = resp.json()
    assert "boom" in str(data.get("detail", ""))