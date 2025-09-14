"""
Route tests for PUT /api/settings
"""

import pytest


@pytest.mark.asyncio
async def test_update_settings_partial_success(async_client):
    payload = {
        "auto_extract_dates": False,
        "generate_text_previews": True,
        "max_file_size_mb": 256,
        "llm_model": "llama3.2:3b",
        "embedding_model": "all-mpnet-base-v2",
        "search_results_limit": 50,
        "auto_organize_by_date": True,
        "duplicate_detection": False,
        "default_import_location": "/tmp",
        "theme": "dark",
        "interface_density": "compact",
    }
    resp = await async_client.put("/api/settings", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert data.get("message")
    updated = set(data.get("updated_fields", []))
    expected = set(payload.keys())
    assert expected.issubset(updated)
    assert "note" in data


@pytest.mark.asyncio
async def test_update_settings_validation(async_client):
    bad_payloads = [
        {"max_file_size_mb": 0},
        {"max_file_size_mb": 1001},
        {"search_results_limit": 0},
        {"search_results_limit": 1001},
        {"theme": "invalid"},
        {"interface_density": "invalid"},
    ]
    for body in bad_payloads:
        resp = await async_client.put("/api/settings", json=body)
        assert resp.status_code == 422
