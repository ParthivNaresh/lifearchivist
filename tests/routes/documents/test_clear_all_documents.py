"""
Tests for DELETE /api/documents focusing on aggregated metrics, vault uninitialized error, and handling of missing LlamaIndex service.
"""

import pytest

from factories.file.file_factory import FileFactory
from factories.file.temp_file_manager import TempFileManager
from factories.request_factory import RequestFactory


@pytest.mark.asyncio
async def test_clear_all_documents_success_aggregates_metrics(async_client, test_server):
    await test_server.vault.clear_all_files([])
    await test_server.llamaindex_service.clear_all_data()
    f1 = FileFactory.create_text_file(content="clear one 111")
    f2 = FileFactory.create_text_file(content="clear two 222")
    with TempFileManager() as tfm:
        for tf in [f1, f2]:
            p = tfm.create_temp_file(tf)
            body = RequestFactory.create_ingest_request_from_test_file(tf, temp_path=p)
            r = await async_client.post("/api/ingest", json=body)
            assert r.status_code == 200
    resp = await async_client.delete("/api/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    vault = data.get("vault_metrics", {})
    llama = data.get("llamaindex_metrics", {})
    summary = data.get("summary", {})
    vault_files_deleted = vault.get("files_deleted", 0) + vault.get("orphaned_files_deleted", 0)
    total_files_deleted = vault_files_deleted + llama.get("storage_files_deleted", 0)
    assert summary.get("total_files_deleted") == total_files_deleted
    vault_bytes_reclaimed = vault.get("bytes_reclaimed", 0) + vault.get("orphaned_bytes_reclaimed", 0)
    total_bytes_reclaimed = vault_bytes_reclaimed + llama.get("storage_bytes_reclaimed", 0)
    assert summary.get("total_bytes_reclaimed") == total_bytes_reclaimed
    vinfo = await async_client.get("/api/vault/info")
    assert vinfo.status_code == 200
    assert vinfo.json().get("total_files") == 0


@pytest.mark.asyncio
async def test_clear_all_documents_vault_uninitialized_returns_500(async_client, test_server, monkeypatch):
    monkeypatch.setattr(test_server, "vault", None)
    resp = await async_client.delete("/api/documents")
    assert resp.status_code == 500
    data = resp.json()
    assert "Vault not initialized" in str(data.get("detail", ""))


@pytest.mark.asyncio
async def test_clear_all_documents_llamaindex_missing_still_succeeds(async_client, test_server, monkeypatch):
    await test_server.vault.clear_all_files([])
    await test_server.llamaindex_service.clear_all_data()
    f1 = FileFactory.create_text_file(content="orphan vault 999")
    with TempFileManager() as tfm:
        p = tfm.create_temp_file(f1)
        body = RequestFactory.create_ingest_request_from_test_file(f1, temp_path=p)
        r = await async_client.post("/api/ingest", json=body)
        assert r.status_code == 200
    monkeypatch.setattr(test_server, "llamaindex_service", None)
    resp = await async_client.delete("/api/documents")
    assert resp.status_code == 200
    data = resp.json()
    llama = data.get("llamaindex_metrics", {})
    assert llama.get("skipped") is True
    vinfo = await async_client.get("/api/vault/info")
    assert vinfo.status_code == 200
    assert vinfo.json().get("total_files") == 0