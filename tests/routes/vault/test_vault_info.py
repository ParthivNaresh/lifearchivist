"""
Tests for the /api/vault/info endpoint focusing on structure and counts.
"""

import pytest

from factories.file.file_factory import FileFactory
from factories.file.temp_file_manager import TempFileManager
from factories.request_factory import RequestFactory


@pytest.mark.asyncio
async def test_vault_info_empty_structure(async_client, test_server):
    await test_server.vault.clear_all_files([])
    resp = await async_client.get("/api/vault/info")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data.get("vault_path"), str) and data["vault_path"]
    directories = data.get("directories", {})
    assert set(directories.keys()) == {"content", "thumbnails", "temp", "exports"}
    for key in ["content", "thumbnails", "temp", "exports"]:
        d = directories[key]
        assert set(d.keys()) == {"file_count", "total_size_bytes", "total_size_mb"}
        assert isinstance(d["file_count"], int)
        assert isinstance(d["total_size_bytes"], int)
        assert isinstance(d["total_size_mb"], (int, float))
    assert isinstance(data.get("total_files"), int)
    assert isinstance(data.get("total_size_bytes"), int)
    assert isinstance(data.get("total_size_mb"), (int, float))


@pytest.mark.asyncio
async def test_vault_info_populated_updates_counts(async_client, test_server):
    await test_server.vault.clear_all_files([])
    f1 = FileFactory.create_text_file(content="document one content 12345")
    f2 = FileFactory.create_text_file(content="document two content 67890")
    with TempFileManager() as tfm:
        p1 = tfm.create_temp_file(f1)
        p2 = tfm.create_temp_file(f2)
        b1 = RequestFactory.create_ingest_request_from_test_file(f1, temp_path=p1)
        b2 = RequestFactory.create_ingest_request_from_test_file(f2, temp_path=p2)
        r1 = await async_client.post("/api/ingest", json=b1)
        r2 = await async_client.post("/api/ingest", json=b2)
        assert r1.status_code == 200 and r2.status_code == 200
    resp = await async_client.get("/api/vault/info")
    assert resp.status_code == 200
    data = resp.json()
    directories = data.get("directories", {})
    content = directories.get("content", {})
    assert content.get("file_count", 0) >= 2
    assert data.get("total_files", 0) >= 2


@pytest.mark.asyncio
async def test_vault_info_uninitialized_returns_500(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server, "vault", None)
    resp = await async_client.get("/api/vault/info")
    assert resp.status_code == 500
    data = resp.json()
    assert "Vault not initialized" in str(data.get("detail", ""))