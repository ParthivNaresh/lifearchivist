"""
Tests for the POST /api/ask endpoint focusing on endpoint behavior, input validation, and transformation of tool results.
"""

import pytest
from unittest.mock import AsyncMock

from factories.request_factory import RequestFactory


@pytest.mark.asyncio
async def test_ask_success_transforms_sources_to_citations(async_client, test_server, monkeypatch):
    async def _success_execute_tool(name, params):
        assert name == "llamaindex.query"
        assert params["question"] == "What is alpha?"
        assert params["similarity_top_k"] == 5
        return {
            "success": True,
            "result": {
                "answer": "Alpha is a test.",
                "confidence": 0.82,
                "sources": [
                    {
                        "document_id": "doc_1",
                        "title": "Doc One",
                        "text": "A" * 500,
                        "score": 0.91,
                    },
                    {
                        "document_id": "doc_2",
                        "metadata": {"title": "Doc Two"},
                        "text": "Short snippet",
                        "score": 0.72,
                    },
                ],
                "method": "llamaindex_rag",
                "metadata": {"nodes_used": 2},
            },
        }

    monkeypatch.setattr(test_server, "execute_tool", AsyncMock(side_effect=_success_execute_tool))
    body = RequestFactory.create_ask_request(question="What is alpha?", context_limit=5)
    resp = await async_client.post("/api/ask", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("answer") == "Alpha is a test."
    assert isinstance(data.get("confidence"), float)
    assert data.get("method") == "llamaindex_rag"
    assert data.get("context_length") == 2
    citations = data.get("citations", [])
    assert len(citations) == 2
    first = citations[0]
    assert set(["doc_id", "title", "snippet", "score"]).issubset(first.keys())
    assert len(first.get("snippet", "")) <= 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {},
        {"question": ""},
        {"question": "hi"},
        {"question": "valid", "context_limit": "abc"},
        {"question": "valid", "context_limit": 0},
        {"question": "valid", "context_limit": 21},
    ],
)
async def test_ask_validation_errors(async_client, body):
    resp = await async_client.post("/api/ask", json=body)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_ask_accepts_string_context_limit(async_client, test_server, monkeypatch):
    async def _assert_params(name, params):
        assert name == "llamaindex.query"
        assert params["question"] == "Define beta"
        assert params["similarity_top_k"] == 7
        return {
            "success": True,
            "result": {
                "answer": "Beta defined.",
                "confidence": 0.5,
                "sources": [],
                "method": "llamaindex_rag",
                "metadata": {"nodes_used": 0},
            },
        }

    monkeypatch.setattr(test_server, "execute_tool", AsyncMock(side_effect=_assert_params))
    body = RequestFactory.create_ask_request(question="Define beta", context_limit="7")
    resp = await async_client.post("/api/ask", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("answer") == "Beta defined."
    assert data.get("context_length") == 0


@pytest.mark.asyncio
async def test_ask_tool_failure_returns_500(async_client, test_server, monkeypatch):
    async def _fail(name, params):
        return {"success": False, "error": "qa failed"}

    monkeypatch.setattr(test_server, "execute_tool", AsyncMock(side_effect=_fail))
    body = RequestFactory.create_ask_request(question="What is gamma?", context_limit=5)
    resp = await async_client.post("/api/ask", json=body)
    assert resp.status_code == 500
    data = resp.json()
    assert "detail" in data and "qa failed" in str(data["detail"])