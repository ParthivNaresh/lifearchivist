import pytest
from fastapi.testclient import TestClient


class TestSearchPostEndpoint:
    def test_search_post_endpoint_exists(self, client: TestClient):
        response = client.post("/api/search", json={"query": "test"})
        assert response.status_code in [200, 503]

    def test_search_post_with_query(self, client: TestClient):
        response = client.post("/api/search", json={"query": "test query"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "results" in data
        assert "count" in data
        assert "mode" in data

    @pytest.mark.parametrize(
        "mode", ["semantic", "keyword", "hybrid"]
    )
    def test_search_post_all_modes(self, client: TestClient, mode: str):
        response = client.post("/api/search", json={"query": "test", "mode": mode})
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == mode

    def test_search_post_invalid_mode(self, client: TestClient):
        response = client.post("/api/search", json={"query": "test", "mode": "invalid"})
        assert response.status_code in [400, 422]
        data = response.json()
        if response.status_code == 400:
            assert data["success"] is False
            assert data["error_type"] == "ValidationError"

    def test_search_post_with_filters(self, client: TestClient):
        response = client.post(
            "/api/search",
            json={
                "query": "test",
                "filters": {"mime_type": "application/pdf", "tags": ["important"]},
            },
        )
        assert response.status_code == 200

    def test_search_post_with_limit(self, client: TestClient):
        response = client.post("/api/search", json={"query": "test", "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 10

    def test_search_post_no_service(self, client_no_services: TestClient):
        response = client_no_services.post("/api/search", json={"query": "test"})
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "ServiceUnavailable"

    def test_search_post_no_search_service(self, client_no_search: TestClient):
        response = client_no_search.post("/api/search", json={"query": "test"})
        assert response.status_code == 503


class TestSearchGetEndpoint:
    def test_search_get_endpoint_exists(self, client: TestClient):
        response = client.get("/api/search?q=test")
        assert response.status_code in [200, 503]

    def test_search_get_with_query(self, client: TestClient):
        response = client.get("/api/search?q=test+query")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "results" in data
        assert "count" in data
        assert "mode" in data
        assert "query" in data

    @pytest.mark.parametrize(
        "mode", ["semantic", "keyword", "hybrid"]
    )
    def test_search_get_all_modes(self, client: TestClient, mode: str):
        response = client.get(f"/api/search?q=test&mode={mode}")
        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == mode

    def test_search_get_invalid_mode(self, client: TestClient):
        response = client.get("/api/search?q=test&mode=invalid")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "ValidationError"

    @pytest.mark.parametrize(
        "limit,expected_status",
        [
            (0, 400),
            (1, 200),
            (50, 200),
            (100, 200),
            (101, 400),
        ],
    )
    def test_search_get_limit_validation(
        self, client: TestClient, limit: int, expected_status: int
    ):
        response = client.get(f"/api/search?q=test&limit={limit}")
        assert response.status_code == expected_status
        if expected_status == 400:
            data = response.json()
            assert data["error_type"] == "ValidationError"

    @pytest.mark.parametrize(
        "offset,expected_status",
        [
            (-1, 400),
            (0, 200),
            (10, 200),
            (100, 200),
        ],
    )
    def test_search_get_offset_validation(
        self, client: TestClient, offset: int, expected_status: int
    ):
        response = client.get(f"/api/search?q=test&offset={offset}")
        assert response.status_code == expected_status

    def test_search_get_with_filters(self, client: TestClient):
        response = client.get(
            "/api/search?q=test&mime_type=application/pdf&status=completed&tags=important,work"
        )
        assert response.status_code == 200

    def test_search_get_include_content(self, client: TestClient):
        response = client.get("/api/search?q=test&include_content=true")
        assert response.status_code == 200

    def test_search_get_empty_query(self, client: TestClient):
        response = client.get("/api/search?q=")
        assert response.status_code == 200

    def test_search_get_no_service(self, client_no_services: TestClient):
        response = client_no_services.get("/api/search?q=test")
        assert response.status_code == 503


class TestAskEndpoint:
    def test_ask_endpoint_exists(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "test"})
        assert response.status_code in [200, 503]

    def test_ask_with_valid_question(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "What is this about?"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "answer" in data
        assert "confidence" in data
        assert "citations" in data
        assert "method" in data

    def test_ask_missing_question(self, client: TestClient):
        response = client.post("/api/ask", json={})
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "ValidationError"

    def test_ask_empty_question(self, client: TestClient):
        response = client.post("/api/ask", json={"question": ""})
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "ValidationError"

    def test_ask_short_question(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "ab"})
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "ValidationError"
        assert "3 characters" in data["error"]

    def test_ask_whitespace_question(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "   "})
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "context_limit,expected_status",
        [
            (0, 400),
            (1, 200),
            (10, 200),
            (20, 200),
            (21, 400),
        ],
    )
    def test_ask_context_limit_validation(
        self, client: TestClient, context_limit: int, expected_status: int
    ):
        response = client.post(
            "/api/ask",
            json={"question": "test question", "context_limit": context_limit},
        )
        assert response.status_code == expected_status

    def test_ask_context_limit_string(self, client: TestClient):
        response = client.post(
            "/api/ask", json={"question": "test question", "context_limit": "5"}
        )
        assert response.status_code == 200

    def test_ask_context_limit_invalid_string(self, client: TestClient):
        response = client.post(
            "/api/ask", json={"question": "test question", "context_limit": "invalid"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["error_type"] == "ValidationError"

    def test_ask_with_filters(self, client: TestClient):
        response = client.post(
            "/api/ask",
            json={
                "question": "test question",
                "filters": {"mime_type": "application/pdf"},
            },
        )
        assert response.status_code == 200

    def test_ask_response_structure(self, client: TestClient):
        response = client.post("/api/ask", json={"question": "test question"})
        data = response.json()

        assert "success" in data
        assert "answer" in data
        assert "confidence" in data
        assert "citations" in data
        assert "method" in data
        assert "context_length" in data
        assert "statistics" in data

        assert isinstance(data["citations"], list)
        if data["citations"]:
            citation = data["citations"][0]
            assert "doc_id" in citation
            assert "title" in citation
            assert "snippet" in citation
            assert "score" in citation

    def test_ask_no_service(self, client_no_services: TestClient):
        response = client_no_services.post(
            "/api/ask", json={"question": "test question"}
        )
        assert response.status_code == 503
        data = response.json()
        assert data["error_type"] == "ServiceUnavailable"

    def test_ask_no_query_service(self, client_no_query: TestClient):
        response = client_no_query.post("/api/ask", json={"question": "test question"})
        assert response.status_code == 503

    @pytest.mark.parametrize(
        "question",
        [
            "What is the meaning of life?",
            "How does this work?",
            "Can you explain the process?",
            "What are the key points?",
            "Why is this important?",
        ],
    )
    def test_ask_various_questions(self, client: TestClient, question: str):
        response = client.post("/api/ask", json={"question": question})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
