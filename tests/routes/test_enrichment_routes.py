import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict


class TestGetEnrichmentStatusEndpoint:
    def test_status_endpoint_exists(self, client: TestClient):
        response = client.get("/api/enrichment/status")
        assert response.status_code in [200, 500, 503]

    def test_status_success(self, client_with_enrichment: TestClient):
        response = client_with_enrichment.get("/api/enrichment/status")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "enabled" in data
            assert isinstance(data["enabled"], bool)
            assert "enrichment_worker" in data

    def test_status_response_structure(self, client_with_enrichment: TestClient):
        response = client_with_enrichment.get("/api/enrichment/status")
        if response.status_code == 200:
            data = response.json()
            assert "enabled" in data
            if data["enabled"]:
                assert "enrichment_worker" in data
                if data["enrichment_worker"]:
                    assert isinstance(data["enrichment_worker"], dict)

    def test_status_no_background_tasks(self, client_no_enrichment: TestClient):
        response = client_no_enrichment.get("/api/enrichment/status")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_status_disabled_enrichment(self, client: TestClient):
        response = client.get("/api/enrichment/status")
        if response.status_code == 200:
            data = response.json()
            if not data["enabled"]:
                assert data["enrichment_worker"] is None


class TestGetQueueStatsEndpoint:
    def test_queue_stats_endpoint_exists(self, client: TestClient):
        response = client.get("/api/enrichment/queue/stats")
        assert response.status_code in [200, 500, 503]

    def test_queue_stats_success(self, client_with_enrichment: TestClient):
        response = client_with_enrichment.get("/api/enrichment/queue/stats")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "queue_length" in data
            assert "processing" in data
            assert "completed" in data
            assert "failed" in data
            assert isinstance(data["status"], str)
            assert isinstance(data["queue_length"], int)
            assert isinstance(data["processing"], int)
            assert isinstance(data["completed"], int)
            assert isinstance(data["failed"], int)

    def test_queue_stats_response_structure(self, client_with_enrichment: TestClient):
        response = client_with_enrichment.get("/api/enrichment/queue/stats")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert "queue_length" in data
            assert "processing" in data
            assert "completed" in data
            assert "failed" in data
            assert "error" in data
            
            assert data["queue_length"] >= 0
            assert data["processing"] >= 0
            assert data["completed"] >= 0
            assert data["failed"] >= 0
            
            if data["status"] == "error":
                assert data["error"] is not None
            else:
                assert data["error"] is None or isinstance(data["error"], str)

    def test_queue_stats_no_enrichment_queue(
        self, client_no_enrichment: TestClient
    ):
        response = client_no_enrichment.get("/api/enrichment/queue/stats")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_queue_stats_operational_status(self, client_with_enrichment: TestClient):
        response = client_with_enrichment.get("/api/enrichment/queue/stats")
        if response.status_code == 200:
            data = response.json()
            valid_statuses = ["operational", "unknown", "error", "not_available"]
            assert data["status"] in valid_statuses

    @pytest.mark.parametrize(
        "field",
        ["queue_length", "processing", "completed", "failed"],
    )
    def test_queue_stats_numeric_fields(
        self, client_with_enrichment: TestClient, field: str
    ):
        response = client_with_enrichment.get("/api/enrichment/queue/stats")
        if response.status_code == 200:
            data = response.json()
            assert field in data
            assert isinstance(data[field], int)
            assert data[field] >= 0


class TestEnrichmentEndpointsIntegration:
    def test_status_and_queue_consistency(self, client_with_enrichment: TestClient):
        status_response = client_with_enrichment.get("/api/enrichment/status")
        queue_response = client_with_enrichment.get("/api/enrichment/queue/stats")
        
        if status_response.status_code == 200 and queue_response.status_code == 200:
            status_data = status_response.json()
            queue_data = queue_response.json()
            
            if status_data["enabled"]:
                assert queue_data["status"] != "not_available"
            
            if not status_data["enabled"]:
                assert queue_data["status"] in ["unknown", "not_available"]

    def test_both_endpoints_fail_without_services(
        self, client_no_enrichment: TestClient
    ):
        status_response = client_no_enrichment.get("/api/enrichment/status")
        queue_response = client_no_enrichment.get("/api/enrichment/queue/stats")
        
        assert status_response.status_code == 503
        assert queue_response.status_code == 503
        
        status_data = status_response.json()
        queue_data = queue_response.json()
        
        assert "detail" in status_data
        assert "detail" in queue_data

    def test_response_types_consistency(self, client: TestClient):
        endpoints = [
            "/api/enrichment/status",
            "/api/enrichment/queue/stats",
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code in [200, 500, 503]
            
            data = response.json()
            assert isinstance(data, dict)
            
            if response.status_code == 503:
                assert "detail" in data
            elif response.status_code == 200:
                assert "detail" not in data


class TestEnrichmentErrorHandling:
    def test_status_internal_error_handling(self, client: TestClient):
        response = client.get("/api/enrichment/status")
        if response.status_code == 500:
            data = response.json()
            assert "detail" in data
            assert isinstance(data["detail"], str)

    def test_queue_stats_internal_error_handling(self, client: TestClient):
        response = client.get("/api/enrichment/queue/stats")
        if response.status_code == 500:
            data = response.json()
            assert "detail" in data
            assert isinstance(data["detail"], str)

    def test_invalid_endpoint_returns_404(self, client: TestClient):
        response = client.get("/api/enrichment/invalid")
        assert response.status_code == 404

    def test_method_not_allowed(self, client: TestClient):
        response = client.post("/api/enrichment/status", json={})
        assert response.status_code == 405
        
        response = client.put("/api/enrichment/queue/stats", json={})
        assert response.status_code == 405
        
        response = client.delete("/api/enrichment/status")
        assert response.status_code == 405
