"""
Tests for the /api/bulk-ingest endpoint focusing on endpoint behavior and response aggregation.
"""

import pytest
from unittest.mock import AsyncMock

from factories.file.file_factory import FileFactory
from factories.file.temp_file_manager import TempFileManager
from factories.request_factory import RequestFactory
from factories.response_factory import ResponseFactory


@pytest.mark.asyncio
async def test_bulk_ingest_mixed_success_and_failure(async_client):
    f1 = FileFactory.create_text_file()
    f2 = FileFactory.create_text_file()
    invalid_path = "/tmp/definitely/missing/file.txt"
    with TempFileManager() as tfm:
        p1 = tfm.create_temp_file(f1)
        p2 = tfm.create_temp_file(f2)
        body = RequestFactory.create_bulk_ingest_request(
            file_paths=[str(p1), str(p2), invalid_path], folder_path="/tmp/bulk_folder"
        )
        resp = await async_client.post("/api/bulk-ingest", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert data.get("total_files") == 3
    assert data.get("successful_count") == 2
    assert data.get("failed_count") == 1
    assert data.get("folder_path") == "/tmp/bulk_folder"
    results = data.get("results", [])
    paths = {r.get("file_path") for r in results}
    assert {str(p1), str(p2), invalid_path}.issubset(paths)
    by_path = {r["file_path"]: r for r in results}
    assert by_path[invalid_path]["success"] is False and "error" in by_path[invalid_path]
    assert by_path[str(p1)]["success"] is True and isinstance(by_path[str(p1)].get("file_id"), str)
    assert by_path[str(p2)]["success"] is True and isinstance(by_path[str(p2)].get("file_id"), str)


@pytest.mark.asyncio
async def test_bulk_ingest_tool_failure_path(async_client, test_server, monkeypatch):
    async def _fake_execute_tool(name, params):
        if name == "file.import" and "bad" in params.get("path", ""):
            return {"success": False, "error": "simulated failure"}
        return {"success": True, "result": ResponseFactory.create_upload_response(original_path=params.get("path", "test.txt"))}

    monkeypatch.setattr(test_server, "execute_tool", AsyncMock(side_effect=_fake_execute_tool))
    f1 = FileFactory.create_text_file()
    f2 = FileFactory.create_text_file()
    with TempFileManager() as tfm:
        p1 = tfm.create_temp_file(f1)
        p2 = tfm.create_temp_file(f2)
        body = RequestFactory.create_bulk_ingest_request(
            file_paths=[str(p1), str(p2), "/tmp/bad_path.txt"], folder_path="/tmp/bulk_folder"
        )
        resp = await async_client.post("/api/bulk-ingest", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert data.get("total_files") == 3
    assert data.get("successful_count") == 2
    assert data.get("failed_count") == 1
    results = data.get("results", [])
    bad = next(r for r in results if r["file_path"].endswith("/tmp/bad_path.txt"))
    assert bad["success"] is False and "error" in bad


@pytest.mark.asyncio
async def test_bulk_ingest_no_paths_returns_400(async_client):
    body = RequestFactory.create_bulk_ingest_request(file_paths=[], folder_path="/tmp/bulk_folder")
    resp = await async_client.post("/api/bulk-ingest", json=body)
    assert resp.status_code == 400
    data = resp.json()
    assert "No file paths provided" in str(data.get("detail", ""))