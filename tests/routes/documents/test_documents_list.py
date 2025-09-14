"""
Tests for the GET /api/documents endpoint focusing on empty state, populated listing with status filter and shape, pagination, and service unavailability.
"""

import pytest

from factories.file.file_factory import FileFactory
from factories.file.temp_file_manager import TempFileManager
from factories.request_factory import RequestFactory


@pytest.mark.asyncio
async def test_documents_list_empty(async_client, test_server):
    await test_server.llamaindex_service.clear_all_data()
    resp = await async_client.get("/api/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("documents") == []
    assert data.get("total") == 0
    assert data.get("limit") == 100
    assert data.get("offset") == 0


@pytest.mark.asyncio
async def test_documents_list_populated_status_filter_and_shape(async_client, test_server):
    await test_server.llamaindex_service.clear_all_data()
    f1 = FileFactory.create_text_file(content="doc A alpha 111")
    f2 = FileFactory.create_text_file(content="doc B beta 222")
    f3 = FileFactory.create_text_file(content="doc C gamma 333")
    files = [f1, f2, f3]
    with TempFileManager() as tfm:
        for tf in files:
            p = tfm.create_temp_file(tf)
            body = RequestFactory.create_ingest_request_from_test_file(tf, temp_path=p)
            r = await async_client.post("/api/ingest", json=body)
            assert r.status_code == 200
    resp = await async_client.get("/api/documents", params={"status": "ready", "limit": 100, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    docs = data.get("documents", [])
    assert len(docs) >= 3
    for d in docs:
        for k in [
            "id",
            "file_hash",
            "original_path",
            "mime_type",
            "size_bytes",
            "created_at",
            "ingested_at",
            "status",
            "text_preview",
            "has_content",
            "tags",
            "tag_count",
        ]:
            assert k in d
        assert isinstance(d["tag_count"], int)
        assert isinstance(d["has_content"], bool)
        assert d["status"] == "ready"


@pytest.mark.asyncio
async def test_documents_list_pagination(async_client, test_server):
    await test_server.llamaindex_service.clear_all_data()
    f1 = FileFactory.create_text_file(content="pag one 111")
    f2 = FileFactory.create_text_file(content="pag two 222")
    f3 = FileFactory.create_text_file(content="pag three 333")
    with TempFileManager() as tfm:
        for tf in [f1, f2, f3]:
            p = tfm.create_temp_file(tf)
            body = RequestFactory.create_ingest_request_from_test_file(tf, temp_path=p)
            r = await async_client.post("/api/ingest", json=body)
            assert r.status_code == 200
    page1 = await async_client.get("/api/documents", params={"limit": 2, "offset": 0})
    assert page1.status_code == 200
    d1 = page1.json()
    docs1 = d1.get("documents", [])
    assert len(docs1) == 2
    page2 = await async_client.get("/api/documents", params={"limit": 2, "offset": 2})
    assert page2.status_code == 200
    d2 = page2.json()
    docs2 = d2.get("documents", [])
    ids1 = {d["id"] for d in docs1}
    ids2 = {d["id"] for d in docs2}
    assert ids1.isdisjoint(ids2)
    assert len(ids1.union(ids2)) >= 3


@pytest.mark.asyncio
async def test_documents_list_service_unavailable(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server, "llamaindex_service", None)
    resp = await async_client.get("/api/documents")
    assert resp.status_code == 503
    data = resp.json()
    assert "LlamaIndex service not available" in str(data.get("detail", ""))