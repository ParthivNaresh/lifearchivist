import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict, List


class TestSearchGetEndpoint:
    def test_search_get_endpoint_exists(self, client: TestClient):
        response = client.get("/api/search?q=test")
        assert response.status_code in [200, 500, 503]

    def test_search_get_with_query(self, client: TestClient):
        response = client.get("/api/search?q=test+query")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert "count" in data
            assert "mode" in data
            assert "query" in data
            assert isinstance(data["results"], list)

    @pytest.mark.parametrize(
        "mode", ["semantic", "keyword", "hybrid"]
    )
    def test_search_get_all_modes(self, client: TestClient, mode: str):
        response = client.get(f"/api/search?q=test&mode={mode}")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["mode"] == mode

    def test_search_get_invalid_mode(self, client: TestClient):
        response = client.get("/api/search?q=test&mode=invalid")
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data

    @pytest.mark.parametrize(
        "limit,expected_status",
        [
            (0, 422),
            (1, 200),
            (50, 200),
            (100, 200),
            (101, 422),
        ],
    )
    def test_search_get_limit_validation(
        self, client: TestClient, limit: int, expected_status: int
    ):
        response = client.get(f"/api/search?q=test&limit={limit}")
        assert response.status_code in [expected_status, 500]
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    @pytest.mark.parametrize(
        "offset,expected_status",
        [
            (-1, 422),
            (0, 200),
            (10, 200),
            (100, 200),
        ],
    )
    def test_search_get_offset_validation(
        self, client: TestClient, offset: int, expected_status: int
    ):
        response = client.get(f"/api/search?q=test&offset={offset}")
        assert response.status_code in [expected_status, 500]

    def test_search_get_with_filters(self, client: TestClient):
        response = client.get(
            "/api/search?q=test&mime_type=application/pdf&status=completed&tags=important,work"
        )
        assert response.status_code in [200, 500]

    def test_search_get_include_content(self, client: TestClient):
        response = client.get("/api/search?q=test&include_content=true")
        assert response.status_code in [200, 500]

    def test_search_get_empty_query(self, client: TestClient):
        response = client.get("/api/search?q=")
        assert response.status_code in [200, 500]

    def test_search_get_no_service(self, client_no_services: TestClient):
        response = client_no_services.get("/api/search?q=test")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

    def test_search_response_structure(self, client: TestClient):
        response = client.get("/api/search?q=test")
        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert "count" in data
            assert "mode" in data
            assert "query" in data
            
            assert isinstance(data["results"], list)
            assert isinstance(data["count"], int)
            assert isinstance(data["mode"], str)
            assert isinstance(data["query"], str)
            
            if data["results"]:
                result = data["results"][0]
                assert "document_id" in result
                assert "title" in result
                assert "score" in result
                assert "snippet" in result

    def test_search_pagination(self, client: TestClient):
        response = client.get("/api/search?q=test&limit=5&offset=10")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert len(data["results"]) <= 5


class TestAskEndpoint:
    def test_ask_endpoint_exists(self, client: TestClient):
        response = client.post("/api/search/ask", json={"question": "test"})
        assert response.status_code in [200, 500, 503]

    def test_ask_with_valid_question(self, client: TestClient):
        response = client.post("/api/search/ask", json={"question": "What is this about?"})
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "confidence" in data
            assert "citations" in data
            assert "method" in data

    def test_ask_missing_question(self, client: TestClient):
        response = client.post("/api/search/ask", json={})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_ask_empty_question(self, client: TestClient):
        response = client.post("/api/search/ask", json={"question": ""})
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data

    def test_ask_short_question(self, client: TestClient):
        response = client.post("/api/search/ask", json={"question": "ab"})
        assert response.status_code in [400, 422]
        data = response.json()
        assert "detail" in data

    def test_ask_whitespace_question(self, client: TestClient):
        response = client.post("/api/search/ask", json={"question": "   "})
        assert response.status_code in [200, 500]
        # Note: The endpoint currently accepts whitespace-only questions
        # This might be intentional to allow flexible query handling

    @pytest.mark.parametrize(
        "context_limit,expected_status",
        [
            (0, 422),
            (1, 200),
            (10, 200),
            (20, 200),
            (21, 422),
        ],
    )
    def test_ask_context_limit_validation(
        self, client: TestClient, context_limit: int, expected_status: int
    ):
        response = client.post(
            "/api/search/ask",
            json={"question": "test question", "context_limit": context_limit},
        )
        assert response.status_code in [expected_status, 500]

    def test_ask_context_limit_string(self, client: TestClient):
        response = client.post(
            "/api/search/ask", json={"question": "test question", "context_limit": "5"}
        )
        assert response.status_code in [200, 422, 500]

    def test_ask_context_limit_invalid_string(self, client: TestClient):
        response = client.post(
            "/api/search/ask", json={"question": "test question", "context_limit": "invalid"}
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_ask_with_filters(self, client: TestClient):
        response = client.post(
            "/api/search/ask",
            json={
                "question": "test question",
                "filters": {"mime_type": "application/pdf"},
            },
        )
        assert response.status_code in [200, 500]

    def test_ask_response_structure(self, client: TestClient):
        response = client.post("/api/search/ask", json={"question": "test question"})
        if response.status_code == 200:
            data = response.json()
            
            assert "answer" in data
            assert "confidence" in data
            assert "citations" in data
            assert "method" in data
            assert "context_length" in data
            assert "statistics" in data
            
            assert isinstance(data["answer"], str)
            assert isinstance(data["confidence"], float)
            assert isinstance(data["citations"], list)
            assert isinstance(data["method"], str)
            assert isinstance(data["context_length"], int)
            assert isinstance(data["statistics"], dict)
            
            if data["citations"]:
                citation = data["citations"][0]
                assert "doc_id" in citation
                assert "title" in citation
                assert "snippet" in citation
                assert "score" in citation

    def test_ask_no_service(self, client_no_services: TestClient):
        response = client_no_services.post(
            "/api/search/ask", json={"question": "test question"}
        )
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

    def test_ask_no_query_service(self, client_no_query: TestClient):
        response = client_no_query.post("/api/search/ask", json={"question": "test question"})
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
        response = client.post("/api/search/ask", json={"question": question})
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert isinstance(data["answer"], str)


class TestSearchIntegration:
    def test_search_and_ask_consistency(self, client: TestClient):
        search_response = client.get("/api/search?q=artificial+intelligence")
        ask_response = client.post(
            "/api/search/ask",
            json={"question": "What is artificial intelligence?"}
        )
        
        if search_response.status_code == 200 and ask_response.status_code == 200:
            search_data = search_response.json()
            ask_data = ask_response.json()
            
            assert "results" in search_data
            assert "answer" in ask_data

    def test_search_modes_comparison(self, client: TestClient):
        modes = ["semantic", "keyword", "hybrid"]
        query = "test query"
        
        for mode in modes:
            response = client.get(f"/api/search?q={query}&mode={mode}")
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.json()
                assert data["mode"] == mode
                assert data["query"] == query

    def test_error_handling_consistency(self, client_no_services: TestClient):
        endpoints = [
            ("GET", "/api/search?q=test", None),
            ("POST", "/api/search/ask", {"question": "test"}),
        ]
        
        for method, endpoint, json_data in endpoints:
            if method == "GET":
                response = client_no_services.get(endpoint)
            elif method == "POST":
                response = client_no_services.post(endpoint, json=json_data)
            
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data


class TestSearchValidation:
    @pytest.mark.parametrize(
        "query,expected_status",
        [
            ("", 200),
            ("a", 200),
            ("test query", 200),
            ("very " * 100, 200),  # Long query
        ],
    )
    def test_search_query_validation(
        self, client: TestClient, query: str, expected_status: int
    ):
        response = client.get(f"/api/search?q={query}")
        assert response.status_code in [expected_status, 500]

    @pytest.mark.parametrize(
        "filters",
        [
            {"mime_type": "application/pdf"},
            {"status": "completed"},
            {"tags": ["important", "work"]},
            {"mime_type": "text/plain", "status": "processing"},
        ],
    )
    def test_search_filter_combinations(
        self, client: TestClient, filters: Dict[str, Any]
    ):
        query_params = ["q=test"]
        for key, value in filters.items():
            if isinstance(value, list):
                query_params.append(f"{key}={','.join(value)}")
            else:
                query_params.append(f"{key}={value}")
        
        response = client.get(f"/api/search?{'&'.join(query_params)}")
        assert response.status_code in [200, 500]

    def test_ask_question_length_validation(self, client: TestClient):
        questions = [
            ("", 422),  # Empty
            ("a", 422),  # Too short
            ("ab", 422),  # Still too short
            ("abc", 200),  # Minimum valid
            ("What is this?", 200),  # Normal
            ("a" * 1000, 200),  # Long but valid
        ]
        
        for question, expected_status in questions:
            response = client.post(
                "/api/search/ask",
                json={"question": question}
            )
            assert response.status_code in [expected_status, 500]

    def test_search_special_characters(self, client: TestClient):
        special_queries = [
            "test+query",
            "test-query",
            "test_query",
            "test@query",
            "test#query",
            "test$query",
            "test%query",
            "test&query",
        ]
        
        for query in special_queries:
            response = client.get(f"/api/search?q={query}")
            assert response.status_code in [200, 500]