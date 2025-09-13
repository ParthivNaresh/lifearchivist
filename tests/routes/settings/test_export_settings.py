"""
Route tests for GET /api/settings/export
"""

import pytest


@pytest.mark.asyncio
async def test_export_settings_success(async_client, test_settings):
    resp = await async_client.get("/api/settings/export")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert isinstance(data.get("settings"), dict)
    settings = data["settings"]
    assert settings.get("llm_model") == test_settings.llm_model
    assert settings.get("embedding_model") == test_settings.embedding_model
    assert settings.get("max_file_size_mb") == test_settings.max_file_size_mb
    assert settings.get("theme") == test_settings.theme
    assert isinstance(data.get("exported_at"), str)
    assert isinstance(data.get("version"), str)
