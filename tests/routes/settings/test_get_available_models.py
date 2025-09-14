"""
Route tests for GET /api/settings/models
"""

import pytest


@pytest.mark.asyncio
async def test_get_available_models_success(async_client):
    resp = await async_client.get("/api/settings/models")
    assert resp.status_code == 200
    data = resp.json()
    assert "llm_models" in data and isinstance(data["llm_models"], list) and data["llm_models"]
    assert "embedding_models" in data and isinstance(data["embedding_models"], list) and data["embedding_models"]
    llm_ids = {m.get("id") for m in data["llm_models"]}
    emb_ids = {m.get("id") for m in data["embedding_models"]}
    assert "llama3.2:1b" in llm_ids
    assert "all-MiniLM-L6-v2" in emb_ids
