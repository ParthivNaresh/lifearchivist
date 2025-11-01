from fastapi.testclient import TestClient


class TestHealthEndpoint:
    def test_health_endpoint_exists(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_correct_structure(self, client: TestClient):
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "version" in data
        assert "mode" in data
        assert "vault" in data
        assert "llamaindex" in data
        assert "agents_enabled" in data
        assert "websockets_enabled" in data
        assert "ui_enabled" in data

    def test_health_status_is_healthy(self, client: TestClient):
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    def test_health_services_availability(self, client: TestClient):
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["vault"], bool)
        assert isinstance(data["llamaindex"], bool)
        assert isinstance(data["agents_enabled"], bool)
        assert isinstance(data["websockets_enabled"], bool)
        assert isinstance(data["ui_enabled"], bool)

    def test_health_with_no_services(self, client_no_services: TestClient):
        response = client_no_services.get("/health")
        data = response.json()

        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert data["llamaindex"] is False
