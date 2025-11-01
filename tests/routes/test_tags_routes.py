import pytest
from fastapi.testclient import TestClient


class TestGetAllTagsEndpoint:
    def test_tags_endpoint_exists(self, client: TestClient):
        response = client.get("/api/tags")
        assert response.status_code in [200, 500, 503]

    def test_tags_success(self, client: TestClient):
        response = client.get("/api/tags")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "tags" in data
        assert "total" in data
        assert isinstance(data["tags"], list)
        assert isinstance(data["total"], int)

    def test_tags_no_llamaindex(self, client_no_services: TestClient):
        response = client_no_services.get("/api/tags")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False

    def test_tags_default_params(self, client: TestClient):
        response = client.get("/api/tags")
        assert response.status_code == 200
        data = response.json()
        assert data["min_count"] == 1
        assert data["limit"] == 100

    @pytest.mark.parametrize(
        "min_count",
        [0, 1, 5, 10, 100],
    )
    def test_tags_various_min_counts(self, client: TestClient, min_count: int):
        response = client.get(f"/api/tags?min_count={min_count}")
        assert response.status_code == 200
        data = response.json()
        assert data["min_count"] == min_count

    def test_tags_negative_min_count(self, client: TestClient):
        response = client.get("/api/tags?min_count=-1")
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "limit",
        [1, 10, 100, 500, 1000],
    )
    def test_tags_various_limits(self, client: TestClient, limit: int):
        response = client.get(f"/api/tags?limit={limit}")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == limit

    @pytest.mark.parametrize(
        "limit,expected_status",
        [
            (0, 400),
            (1001, 400),
            (-1, 400),
        ],
    )
    def test_tags_invalid_limits(
        self, client: TestClient, limit: int, expected_status: int
    ):
        response = client.get(f"/api/tags?limit={limit}")
        assert response.status_code == expected_status

    def test_tags_combined_params(self, client: TestClient):
        response = client.get("/api/tags?min_count=5&limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["min_count"] == 5
        assert data["limit"] == 50


class TestGetTopicLandscapeEndpoint:
    def test_topics_endpoint_exists(self, client: TestClient):
        response = client.get("/api/topics")
        assert response.status_code in [200, 500, 503]

    def test_topics_success(self, client: TestClient):
        response = client.get("/api/topics")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True
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
        assert data["success"] is False

    def test_topics_default_params(self, client: TestClient):
        response = client.get("/api/topics")
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert data["min_documents"] == min_documents

    @pytest.mark.parametrize(
        "min_documents,expected_status",
        [
            (0, 400),
            (-1, 400),
            (-10, 400),
        ],
    )
    def test_topics_invalid_min_documents(
        self, client: TestClient, min_documents: int, expected_status: int
    ):
        response = client.get(f"/api/topics?min_documents={min_documents}")
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "max_topics",
        [1, 10, 50, 100, 200],
    )
    def test_topics_various_max_topics(self, client: TestClient, max_topics: int):
        response = client.get(f"/api/topics?max_topics={max_topics}")
        assert response.status_code == 200
        data = response.json()
        assert data["max_topics"] == max_topics

    @pytest.mark.parametrize(
        "max_topics,expected_status",
        [
            (0, 400),
            (201, 400),
            (-1, 400),
        ],
    )
    def test_topics_invalid_max_topics(
        self, client: TestClient, max_topics: int, expected_status: int
    ):
        response = client.get(f"/api/topics?max_topics={max_topics}")
        assert response.status_code == expected_status

    def test_topics_combined_params(self, client: TestClient):
        response = client.get("/api/topics?min_documents=5&max_topics=25")
        assert response.status_code == 200
        data = response.json()
        assert data["min_documents"] == 5
        assert data["max_topics"] == 25
