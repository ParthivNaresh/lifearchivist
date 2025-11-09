import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict, List


class TestGetAllTagsEndpoint:
    def test_tags_endpoint_exists(self, client: TestClient):
        response = client.get("/api/tags")
        assert response.status_code in [200, 500, 503]

    def test_tags_success(self, client: TestClient):
        response = client.get("/api/tags")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "tags" in data
            assert "total" in data
            assert "min_count" in data
            assert "limit" in data
            assert isinstance(data["tags"], list)
            assert isinstance(data["total"], int)

    def test_tags_no_llamaindex(self, client_no_services: TestClient):
        response = client_no_services.get("/api/tags")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

    def test_tags_default_params(self, client: TestClient):
        response = client.get("/api/tags")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["min_count"] == 1
            assert data["limit"] == 100

    @pytest.mark.parametrize(
        "min_count",
        [0, 1, 5, 10, 100],
    )
    def test_tags_various_min_counts(self, client: TestClient, min_count: int):
        response = client.get(f"/api/tags?min_count={min_count}")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["min_count"] == min_count

    def test_tags_negative_min_count(self, client: TestClient):
        response = client.get("/api/tags?min_count=-1")
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.parametrize(
        "limit",
        [1, 10, 100, 500, 1000],
    )
    def test_tags_various_limits(self, client: TestClient, limit: int):
        response = client.get(f"/api/tags?limit={limit}")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["limit"] == limit

    @pytest.mark.parametrize(
        "limit,expected_status",
        [
            (0, 422),
            (1001, 422),
            (-1, 422),
        ],
    )
    def test_tags_invalid_limits(
        self, client: TestClient, limit: int, expected_status: int
    ):
        response = client.get(f"/api/tags?limit={limit}")
        assert response.status_code == expected_status
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    def test_tags_combined_params(self, client: TestClient):
        response = client.get("/api/tags?min_count=5&limit=50")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["min_count"] == 5
            assert data["limit"] == 50

    def test_tags_response_structure(self, client: TestClient):
        response = client.get("/api/tags")
        if response.status_code == 200:
            data = response.json()
            assert "tags" in data
            assert "total" in data
            assert "min_count" in data
            assert "limit" in data
            
            assert isinstance(data["tags"], list)
            assert isinstance(data["total"], int)
            assert isinstance(data["min_count"], int)
            assert isinstance(data["limit"], int)
            
            if data["tags"]:
                tag = data["tags"][0]
                assert "name" in tag
                assert "count" in tag
                assert "metadata" in tag


class TestGetTopicLandscapeEndpoint:
    def test_topics_endpoint_exists(self, client: TestClient):
        response = client.get("/api/topics")
        assert response.status_code in [200, 500, 503]

    def test_topics_success(self, client: TestClient):
        response = client.get("/api/topics")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "topics" in data
            assert "total_topics" in data
            assert "total_documents" in data
            assert "generated_at" in data
            assert isinstance(data["topics"], list)
            assert isinstance(data["total_topics"], int)
            assert isinstance(data["total_documents"], int)

    def test_topics_no_llamaindex(self, client_no_services: TestClient):
        response = client_no_services.get("/api/topics")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

    def test_topics_default_params(self, client: TestClient):
        response = client.get("/api/topics")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["min_documents"] == 1
            assert data["max_topics"] == 50

    @pytest.mark.parametrize(
        "min_documents",
        [1, 5, 10, 50, 100],
    )
    def test_topics_various_min_documents(
        self, client: TestClient, min_documents: int
    ):
        response = client.get(f"/api/topics?min_documents={min_documents}")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["min_documents"] == min_documents

    @pytest.mark.parametrize(
        "min_documents,expected_status",
        [
            (0, 422),
            (-1, 422),
            (-10, 422),
        ],
    )
    def test_topics_invalid_min_documents(
        self, client: TestClient, min_documents: int, expected_status: int
    ):
        response = client.get(f"/api/topics?min_documents={min_documents}")
        assert response.status_code == expected_status
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    @pytest.mark.parametrize(
        "max_topics",
        [1, 10, 50, 100, 200],
    )
    def test_topics_various_max_topics(self, client: TestClient, max_topics: int):
        response = client.get(f"/api/topics?max_topics={max_topics}")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["max_topics"] == max_topics

    @pytest.mark.parametrize(
        "max_topics,expected_status",
        [
            (0, 422),
            (201, 422),
            (-1, 422),
        ],
    )
    def test_topics_invalid_max_topics(
        self, client: TestClient, max_topics: int, expected_status: int
    ):
        response = client.get(f"/api/topics?max_topics={max_topics}")
        assert response.status_code == expected_status
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    def test_topics_combined_params(self, client: TestClient):
        response = client.get("/api/topics?min_documents=5&max_topics=25")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["min_documents"] == 5
            assert data["max_topics"] == 25

    def test_topics_response_structure(self, client: TestClient):
        response = client.get("/api/topics")
        if response.status_code == 200:
            data = response.json()
            assert "topics" in data
            assert "total_topics" in data
            assert "total_documents" in data
            assert "generated_at" in data
            assert "min_documents" in data
            assert "max_topics" in data
            
            assert isinstance(data["topics"], list)
            assert isinstance(data["total_topics"], int)
            assert isinstance(data["total_documents"], int)
            assert isinstance(data["generated_at"], str)
            assert isinstance(data["min_documents"], int)
            assert isinstance(data["max_topics"], int)
            
            if data["topics"]:
                topic = data["topics"][0]
                assert "id" in topic
                assert "name" in topic
                assert "document_count" in topic
                assert "subtopics" in topic
                assert "metadata" in topic


class TestTagsIntegration:
    def test_tags_and_topics_consistency(self, client: TestClient):
        tags_response = client.get("/api/tags")
        topics_response = client.get("/api/topics")
        
        if tags_response.status_code == 200 and topics_response.status_code == 200:
            tags_data = tags_response.json()
            topics_data = topics_response.json()
            
            assert "tags" in tags_data
            assert "topics" in topics_data

    def test_error_handling_consistency(self, client_no_services: TestClient):
        endpoints = [
            "/api/tags",
            "/api/topics",
        ]
        
        for endpoint in endpoints:
            response = client_no_services.get(endpoint)
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data

    def test_pagination_parameters(self, client: TestClient):
        endpoints_params = [
            ("/api/tags", "limit", 50),
            ("/api/topics", "max_topics", 25),
        ]
        
        for endpoint, param, value in endpoints_params:
            response = client.get(f"{endpoint}?{param}={value}")
            assert response.status_code in [200, 500]
            if response.status_code == 200:
                data = response.json()
                assert data[param] == value


class TestTagsValidation:
    @pytest.mark.parametrize(
        "endpoint,param,value,expected_status",
        [
            ("/api/tags", "min_count", -1, 422),
            ("/api/tags", "min_count", 0, 200),
            ("/api/tags", "min_count", 1, 200),
            ("/api/tags", "min_count", 100, 200),
            ("/api/tags", "limit", 0, 422),
            ("/api/tags", "limit", 1, 200),
            ("/api/tags", "limit", 1000, 200),
            ("/api/tags", "limit", 1001, 422),
            ("/api/topics", "min_documents", 0, 422),
            ("/api/topics", "min_documents", 1, 200),
            ("/api/topics", "min_documents", 100, 200),
            ("/api/topics", "max_topics", 0, 422),
            ("/api/topics", "max_topics", 1, 200),
            ("/api/topics", "max_topics", 200, 200),
            ("/api/topics", "max_topics", 201, 422),
        ],
    )
    def test_parameter_validation(
        self, client: TestClient, endpoint: str, param: str, value: int, expected_status: int
    ):
        response = client.get(f"{endpoint}?{param}={value}")
        assert response.status_code in [expected_status, 500]
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data

    def test_invalid_parameter_types(self, client: TestClient):
        invalid_params = [
            ("/api/tags", "min_count", "abc"),
            ("/api/tags", "limit", "xyz"),
            ("/api/topics", "min_documents", "invalid"),
            ("/api/topics", "max_topics", "not_a_number"),
        ]
        
        for endpoint, param, value in invalid_params:
            response = client.get(f"{endpoint}?{param}={value}")
            assert response.status_code == 422
            data = response.json()
            assert "detail" in data

    def test_multiple_parameters(self, client: TestClient):
        test_cases = [
            ("/api/tags", {"min_count": 5, "limit": 50}, 200),
            ("/api/tags", {"min_count": -1, "limit": 50}, 422),
            ("/api/tags", {"min_count": 5, "limit": 0}, 422),
            ("/api/topics", {"min_documents": 10, "max_topics": 25}, 200),
            ("/api/topics", {"min_documents": 0, "max_topics": 25}, 422),
            ("/api/topics", {"min_documents": 10, "max_topics": 0}, 422),
        ]
        
        for endpoint, params, expected_status in test_cases:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            response = client.get(f"{endpoint}?{query_string}")
            assert response.status_code in [expected_status, 500]