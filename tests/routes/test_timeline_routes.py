import pytest
from fastapi.testclient import TestClient


class TestGetTimelineDataEndpoint:
    def test_timeline_data_endpoint_exists(self, client: TestClient):
        response = client.get("/api/timeline/data")
        assert response.status_code in [200, 500, 503]

    def test_timeline_data_success(self, client: TestClient):
        response = client.get("/api/timeline/data")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "date_range" in data
        assert "by_year" in data
        assert "documents_without_dates" in data
        assert isinstance(data["total_documents"], int)
        assert isinstance(data["by_year"], dict)

    def test_timeline_data_no_llamaindex(self, client_no_services: TestClient):
        response = client_no_services.get("/api/timeline/data")
        assert response.status_code == 503

    def test_timeline_data_with_start_date(self, client: TestClient):
        response = client.get("/api/timeline/data?start_date=2024-01-01")
        assert response.status_code == 200

    def test_timeline_data_with_end_date(self, client: TestClient):
        response = client.get("/api/timeline/data?end_date=2024-12-31")
        assert response.status_code == 200

    def test_timeline_data_with_date_range(self, client: TestClient):
        response = client.get(
            "/api/timeline/data?start_date=2024-01-01&end_date=2024-12-31"
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "start_date",
        [
            "2020-01-01",
            "2023-06-15",
            "2024-12-31",
        ],
    )
    def test_timeline_data_various_start_dates(
        self, client: TestClient, start_date: str
    ):
        response = client.get(f"/api/timeline/data?start_date={start_date}")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "end_date",
        [
            "2024-01-01",
            "2024-06-30",
            "2025-12-31",
        ],
    )
    def test_timeline_data_various_end_dates(self, client: TestClient, end_date: str):
        response = client.get(f"/api/timeline/data?end_date={end_date}")
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "invalid_date",
        [
            "invalid",
            "2024-13-01",
            "2024-01-32",
            "2024/01/01",
        ],
    )
    def test_timeline_data_invalid_start_date(
        self, client: TestClient, invalid_date: str
    ):
        response = client.get(f"/api/timeline/data?start_date={invalid_date}")
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "invalid_date",
        [
            "invalid",
            "2024-13-01",
            "2024-01-32",
            "2024/01/01",
        ],
    )
    def test_timeline_data_invalid_end_date(
        self, client: TestClient, invalid_date: str
    ):
        response = client.get(f"/api/timeline/data?end_date={invalid_date}")
        assert response.status_code == 400

    def test_timeline_data_response_structure(self, client: TestClient):
        response = client.get("/api/timeline/data")
        assert response.status_code == 200
        data = response.json()
        assert "date_range" in data
        assert "earliest" in data["date_range"]
        assert "latest" in data["date_range"]


class TestGetTimelineSummaryEndpoint:
    def test_timeline_summary_endpoint_exists(self, client: TestClient):
        response = client.get("/api/timeline/summary")
        assert response.status_code in [200, 500, 503]

    def test_timeline_summary_success(self, client: TestClient):
        response = client.get("/api/timeline/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "date_range" in data
        assert "by_year" in data
        assert "data_quality" in data
        assert isinstance(data["total_documents"], int)
        assert isinstance(data["by_year"], dict)
        assert isinstance(data["data_quality"], dict)

    def test_timeline_summary_no_llamaindex(self, client_no_services: TestClient):
        response = client_no_services.get("/api/timeline/summary")
        assert response.status_code == 503

    def test_timeline_summary_response_structure(self, client: TestClient):
        response = client.get("/api/timeline/summary")
        assert response.status_code == 200
        data = response.json()
        assert "date_range" in data
        assert "earliest" in data["date_range"]
        assert "latest" in data["date_range"]
        assert "data_quality" in data
        assert "with_document_created_at" in data["data_quality"]
        assert "with_platform_dates" in data["data_quality"]
        assert "fallback_to_disk" in data["data_quality"]
        assert "no_dates" in data["data_quality"]

    def test_timeline_summary_data_quality_types(self, client: TestClient):
        response = client.get("/api/timeline/summary")
        assert response.status_code == 200
        data = response.json()
        quality = data["data_quality"]
        assert isinstance(quality["with_document_created_at"], int)
        assert isinstance(quality["with_platform_dates"], int)
        assert isinstance(quality["fallback_to_disk"], int)
        assert isinstance(quality["no_dates"], int)
