"""
Tests for the POST /api/search endpoint focusing on endpoint behavior, result shape, and error handling.
"""

import pytest
from unittest.mock import AsyncMock

from factories.file.file_factory import FileFactory
from factories.file.temp_file_manager import TempFileManager
from factories.request_factory import RequestFactory


@pytest.mark.asyncio
async def test_search_post_success_with_content(async_client):
    f1 = FileFactory.create_text_file(content="alpha beta gamma searchtoken")
    f2 = FileFactory.create_text_file(content="delta epsilon zeta")
    with TempFileManager() as tfm:
        p1 = tfm.create_temp_file(f1)
        p2 = tfm.create_temp_file(f2)
        b1 = RequestFactory.create_ingest_request_from_test_file(f1, temp_path=p1)
        b2 = RequestFactory.create_ingest_request_from_test_file(f2, temp_path=p2)
        r1 = await async_client.post("/api/ingest", json=b1)
        r2 = await async_client.post("/api/ingest", json=b2)
        assert r1.status_code == 200 and r2.status_code == 200
    payload = RequestFactory.create_search_request(
        query="searchtoken",
        mode="keyword",
        include_content=True,
        filters={"mime_type": "text/plain"},
    )
    resp = await async_client.post("/api/search", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("results"), list)
    assert isinstance(data.get("total"), int)
    assert isinstance(data.get("query_time_ms"), (int, float))
    if data["results"]:
        first = data["results"][0]
        for k in [
            "document_id",
            "title",
            "snippet",
            "score",
            "mime_type",
            "size_bytes",
            "match_type",
            "created_at",
            "ingested_at",
            "tags",
            "content",
        ]:
            assert k in first


@pytest.mark.asyncio
async def test_search_post_tool_failure_returns_500(async_client, test_server, monkeypatch):
    async def _fail_execute_tool(name, params):
        if name == "index.search":
            return {"success": False, "error": "search failed"}
        return {"success": True, "result": {}}

    monkeypatch.setattr(test_server, "execute_tool", AsyncMock(side_effect=_fail_execute_tool))
    payload = RequestFactory.create_search_request(query="x")
    resp = await async_client.post("/api/search", json=payload)
    assert resp.status_code == 500
    data = resp.json()
    assert "detail" in data and "search failed" in str(data["detail"]) 


@pytest.mark.asyncio
async def test_search_post_validation_error_missing_query(async_client):
    resp = await async_client.post("/api/search", json={})
    assert resp.status_code == 422