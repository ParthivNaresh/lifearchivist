"""
Tests for GET /api/documents/{document_id}/llamaindex-neighbors focusing on success and exception paths.
"""

import pytest
from unittest.mock import AsyncMock

from factories.document_factory import DocumentFactory


@pytest.mark.asyncio
async def test_document_neighbors_success_returns_payload(async_client, test_server, monkeypatch):
    document_id = "doc_neighbors"
    neighbors = [
        DocumentFactory.build_neighbor(document_id=f"doc_{i}", similarity_score=0.9 - i * 0.1, text_preview=f"n{i}")
        for i in range(3)
    ]
    payload = DocumentFactory.build_neighbors_response(document_id, neighbors, query_text="repr")
    monkeypatch.setattr(
        test_server.llamaindex_service,
        "get_document_neighbors",
        AsyncMock(return_value=payload),
    )
    resp = await async_client.get(f"/api/documents/{document_id}/llamaindex-neighbors", params={"top_k": 3})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("document_id") == document_id
    assert data.get("total_found") == 3
    assert isinstance(data.get("neighbors"), list)
    if data["neighbors"]:
        first = data["neighbors"][0]
        for k in ["document_id", "similarity_score", "text_preview", "metadata"]:
            assert k in first
        assert isinstance(first["similarity_score"], float)
        assert isinstance(first["metadata"], dict)


@pytest.mark.asyncio
async def test_document_neighbors_exception_returns_500(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server.llamaindex_service, "get_document_neighbors", AsyncMock(side_effect=Exception("boom")))
    resp = await async_client.get("/api/documents/doc_err/llamaindex-neighbors", params={"top_k": 3})
    assert resp.status_code == 500
    data = resp.json()
    assert "boom" in str(data.get("detail", ""))