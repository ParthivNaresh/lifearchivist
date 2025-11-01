from fastapi.testclient import TestClient


class TestGetEnrichmentStatusEndpoint:
    def test_status_endpoint_exists(self, client: TestClient):
        response = client.get("/api/enrichment/status")
        assert response.status_code in [200, 500, 503]

    def test_status_success(self, client_with_enrichment: TestClient):
        response = client_with_enrichment.get("/api/enrichment/status")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    def test_status_no_background_tasks(self, client_no_enrichment: TestClient):
        response = client_no_enrichment.get("/api/enrichment/status")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["enabled"] is False
        assert "error" in data


class TestGetQueueStatsEndpoint:
    def test_queue_stats_endpoint_exists(self, client: TestClient):
        response = client.get("/api/enrichment/queue/stats")
        assert response.status_code in [200, 500, 503]

    def test_queue_stats_success(self, client_with_enrichment: TestClient):
        response = client_with_enrichment.get("/api/enrichment/queue/stats")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    def test_queue_stats_no_enrichment_queue(
        self, client_no_enrichment: TestClient
    ):
        response = client_no_enrichment.get("/api/enrichment/queue/stats")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "not_available"
        assert "error" in data
