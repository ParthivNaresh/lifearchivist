"""
Tests for the /api/ingest endpoint focusing on endpoint behavior and response shape.
"""

import pytest
from unittest.mock import AsyncMock

from factories.file.file_factory import FileFactory
from factories.file.temp_file_manager import TempFileManager
from factories.request_factory import RequestFactory


@pytest.mark.asyncio
async def test_ingest_success(async_client, test_server):
    await test_server.llamaindex_service.clear_all_data()
    test_file = FileFactory.create_text_file()
    with TempFileManager() as tfm:
        temp_path = tfm.create_temp_file(test_file)
        body = RequestFactory.create_ingest_request_from_test_file(
            test_file, temp_path=temp_path
        )
        resp = await async_client.post("/api/ingest", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("file_id"), str) and data["file_id"]
    assert isinstance(data.get("hash"), str) and data["hash"]
    assert isinstance(data.get("size"), int) and data["size"] >= 0
    assert data.get("mime_type") == test_file.mime_type
    assert data.get("status") == "ready"
    assert isinstance(data.get("vault_path"), str) and data["vault_path"]
    assert isinstance(data.get("created_at"), str)
    assert isinstance(data.get("modified_at"), str)
    assert isinstance(data.get("deduped"), bool)


@pytest.mark.asyncio
async def test_ingest_validation_error_missing_path(async_client):
    resp = await async_client.post("/api/ingest", json={"tags": [], "metadata": {}})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_ingest_tool_error_returns_500(async_client, test_server, monkeypatch):
    async def _fail_execute_tool(name, params):
        return {"success": False, "error": "tool failure"}

    monkeypatch.setattr(test_server, "execute_tool", AsyncMock(side_effect=_fail_execute_tool))
    body = RequestFactory.create_ingest_request(path="/tmp/nonexistent.file")
    resp = await async_client.post("/api/ingest", json=body)
    assert resp.status_code == 500
    data = resp.json()
    assert "detail" in data and "tool failure" in str(data["detail"])
