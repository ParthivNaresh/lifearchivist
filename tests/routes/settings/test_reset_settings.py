"""
Route tests for POST /api/settings/reset
"""

import pytest


@pytest.mark.asyncio
async def test_reset_settings_success(async_client):
    resp = await async_client.post("/api/settings/reset")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("success") is True
    assert "message" in data
    assert "note" in data
