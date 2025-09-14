"""
Tests for the GET /api/search endpoint focusing on endpoint behavior, query param validation, and failure handling.
"""

import pytest
from unittest.mock import AsyncMock

from factories.file.file_factory import FileFactory
from factories.file.temp_file_manager import TempFileManager
from factories.request_factory import RequestFactory


@pytest.mark.asyncio
async def test_search_get_success_with_filters_and_content(async_client, test_server):
    await test_server.llamaindex_service.clear_all_data()
    f1 = FileFactory.create_text_file(content="lorem ipsum searchgettoken alpha")
    f2 = FileFactory.create_text_file(content="unrelated content beta gamma")
    with TempFileManager() as tfm:
        p1 = tfm.create_temp_file(f1)
        p2 = tfm.create_temp_file(f2)
        b1 = RequestFactory.create_ingest_request_from_test_file(f1, temp_path=p1)
        b2 = RequestFactory.create_ingest_request_from_test_file(f2, temp_path=p2)
        r1 = await async_client.post("/api/ingest", json=b1)
        r2 = await async_client.post("/api/ingest", json=b2)
        assert r1.status_code == 200 and r2.status_code == 200
    tag_csv = ",".join(f1.expected_tags[:1]) if f1.expected_tags else ""
    params = RequestFactory.create_search_query_params(
        q="searchgettoken",
        mode="keyword",
        limit=10,
        offset=0,
        include_content=True,
        mime_type="text/plain",
        status="ready",
        tags=tag_csv or None,
    )
    resp = await async_client.get("/api/search", params=params)
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
        ]:
            assert k in first
        assert "content" in first


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params,expected_status",
    [
        (RequestFactory.create_search_query_params(q="x", mode="invalid"), 400),
        (RequestFactory.create_search_query_params(q="x", limit=0), 400),
        (RequestFactory.create_search_query_params(q="x", limit=101), 400),
        (RequestFactory.create_search_query_params(q="x", offset=-1), 400),
    ],
)
async def test_search_get_query_param_validation(async_client, params, expected_status):
    resp = await async_client.get("/api/search", params=params)
    assert resp.status_code == expected_status


@pytest.mark.asyncio
async def test_search_get_tool_failure_returns_500(async_client, test_server, monkeypatch):
    async def _fail_execute_tool(name, params):
        if name == "index.search":
            return {"success": False, "error": "search failed"}
        return {"success": True, "result": {}}

    monkeypatch.setattr(test_server, "execute_tool", AsyncMock(side_effect=_fail_execute_tool))
    params = RequestFactory.create_search_query_params(q="token")
    resp = await async_client.get("/api/search", params=params)
    assert resp.status_code == 500
    data = resp.json()
    assert "detail" in data and "search failed" in str(data["detail"])