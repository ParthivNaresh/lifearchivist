"""
Route tests for GET /api/settings
"""

import pytest


@pytest.mark.asyncio
async def test_get_settings_success(async_client, test_settings):
    resp = await async_client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {
        "auto_extract_dates",
        "generate_text_previews",
        "max_file_size_mb",
        "llm_model",
        "embedding_model",
        "search_results_limit",
        "auto_organize_by_date",
        "duplicate_detection",
        "default_import_location",
        "theme",
        "interface_density",
        "vault_path",
        "lifearch_home",
    }
    assert expected_keys.issubset(set(data.keys()))
    assert data["llm_model"] == test_settings.llm_model
    assert data["embedding_model"] == test_settings.embedding_model
    assert data["theme"] == test_settings.theme
    assert data["max_file_size_mb"] == test_settings.max_file_size_mb
    assert data["auto_extract_dates"] is True
    assert data["generate_text_previews"] is True
    assert data["search_results_limit"] == 25
    assert data["auto_organize_by_date"] is False
    assert data["duplicate_detection"] is True
    assert data["default_import_location"] == "~/Documents"
    assert data["interface_density"] == "comfortable"
    assert data["vault_path"] == str(test_settings.vault_path)
    assert data["lifearch_home"] == str(test_settings.lifearch_home)
