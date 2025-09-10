"""
Tests for the /api/vault/files endpoint focusing on structure, invalid directory, and populated listing with pagination and database record linkage.
"""

import pytest

from factories.file.file_factory import FileFactory
from factories.file.temp_file_manager import TempFileManager
from factories.request_factory import RequestFactory


@pytest.mark.asyncio
async def test_list_vault_files_empty_and_invalid_directory(async_client, test_server):
    await test_server.vault.clear_all_files([])
    resp = await async_client.get("/api/vault/files")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("directory") == "content"
    assert data.get("total") == 0
    assert data.get("files") == []
    resp2 = await async_client.get("/api/vault/files", params={"directory": "does_not_exist"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2.get("directory") == "does_not_exist"
    assert data2.get("total") == 0
    assert data2.get("files") == []


@pytest.mark.asyncio
async def test_list_vault_files_populated_pagination_and_records(async_client, test_server):
    await test_server.vault.clear_all_files([])
    f1 = FileFactory.create_text_file(content="alpha content 111")
    f2 = FileFactory.create_text_file(content="beta content 222")
    f3 = FileFactory.create_text_file(content="gamma content 333")
    created = [f1, f2, f3]
    hash_to_file_id = {}
    with TempFileManager() as tfm:
        for tf in created:
            pth = tfm.create_temp_file(tf)
            body = RequestFactory.create_ingest_request_from_test_file(tf, temp_path=pth)
            r = await async_client.post("/api/ingest", json=body)
            assert r.status_code == 200
            hash_to_file_id[tf.hash] = r.json()["file_id"]
    page1 = await async_client.get("/api/vault/files", params={"directory": "content", "limit": 2, "offset": 0})
    assert page1.status_code == 200
    d1 = page1.json()
    assert d1.get("directory") == "content"
    assert d1.get("total", 0) >= 3
    files1 = d1.get("files", [])
    assert len(files1) == 2
    for entry in files1:
        assert isinstance(entry.get("path"), str)
        assert isinstance(entry.get("full_path"), str)
        assert isinstance(entry.get("hash"), str)
        assert isinstance(entry.get("extension"), str)
        assert isinstance(entry.get("size_bytes"), int)
        assert isinstance(entry.get("created_at"), (int, float))
        assert isinstance(entry.get("modified_at"), (int, float))
        h = entry.get("hash")
        if h in hash_to_file_id:
            record = entry.get("database_record")
            assert record and record.get("id") == hash_to_file_id[h]
    page2 = await async_client.get("/api/vault/files", params={"directory": "content", "limit": 2, "offset": 2})
    assert page2.status_code == 200
    d2 = page2.json()
    files2 = d2.get("files", [])
    paths1 = {e["full_path"] for e in files1}
    paths2 = {e["full_path"] for e in files2}
    assert paths1.isdisjoint(paths2)
    union_count = len(paths1.union(paths2))
    assert union_count >= 3


@pytest.mark.asyncio
async def test_list_vault_files_vault_path_unconfigured_returns_500(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server.settings, "vault_path", None)
    resp = await async_client.get("/api/vault/files")
    assert resp.status_code == 500
    data = resp.json()
    assert "Vault path not configured" in str(data.get("detail", ""))