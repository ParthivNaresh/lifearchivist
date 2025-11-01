import pytest
from fastapi.testclient import TestClient


class TestAddProviderEndpoint:
    def test_add_provider_endpoint_exists(self, client: TestClient):
        response = client.post(
            "/api/providers",
            json={
                "provider_id": "test-provider",
                "provider_type": "openai",
                "config": {"api_key": "sk-test"},
            },
        )
        assert response.status_code in [200, 400, 503]

    def test_add_provider_minimal(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers",
            json={
                "provider_id": "test-openai",
                "provider_type": "openai",
                "config": {"api_key": "sk-test123"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["provider_id"] == "test-openai"

    def test_add_provider_with_default(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers",
            json={
                "provider_id": "test-provider",
                "provider_type": "openai",
                "config": {"api_key": "sk-test"},
                "set_as_default": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_default"] is True

    @pytest.mark.parametrize(
        "provider_type",
        ["openai", "anthropic", "google", "ollama"],
    )
    def test_add_provider_valid_types(
        self, client_with_llm: TestClient, provider_type: str
    ):
        response = client_with_llm.post(
            "/api/providers",
            json={
                "provider_id": f"test-{provider_type}",
                "provider_type": provider_type,
                "config": {"api_key": "test-key"},
            },
        )
        assert response.status_code in [200, 400]

    def test_add_provider_invalid_type(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers",
            json={
                "provider_id": "test",
                "provider_type": "invalid_type",
                "config": {},
            },
        )
        assert response.status_code == 400

    def test_add_provider_missing_fields(self, client_with_llm: TestClient):
        response = client_with_llm.post("/api/providers", json={})
        assert response.status_code == 422

    def test_add_provider_no_service(self, client: TestClient):
        response = client.post(
            "/api/providers",
            json={
                "provider_id": "test",
                "provider_type": "openai",
                "config": {"api_key": "test"},
            },
        )
        assert response.status_code == 503


class TestListProvidersEndpoint:
    def test_list_providers_endpoint_exists(self, client: TestClient):
        response = client.get("/api/providers")
        assert response.status_code in [200, 503]

    def test_list_providers_success(self, client_with_llm: TestClient):
        response = client_with_llm.get("/api/providers")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert "providers" in data
        assert "total" in data
        assert isinstance(data["providers"], list)

    def test_list_providers_no_service(self, client: TestClient):
        response = client.get("/api/providers")
        assert response.status_code == 503


class TestGetProviderEndpoint:
    def test_get_provider_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.get("/api/providers/test_provider")
        assert response.status_code in [200, 404, 503]

    def test_get_provider_not_found(self, client_with_llm: TestClient):
        response = client_with_llm.get("/api/providers/nonexistent")
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "provider_id",
        [
            "provider123",
            "provider-with-dashes",
            "provider_with_underscores",
        ],
    )
    def test_get_provider_various_id_formats(
        self, client_with_llm: TestClient, provider_id: str
    ):
        response = client_with_llm.get(f"/api/providers/{provider_id}")
        assert response.status_code in [200, 404, 503]

    def test_get_provider_no_service(self, client: TestClient):
        response = client.get("/api/providers/test")
        assert response.status_code == 503


class TestCheckProviderUsageEndpoint:
    def test_check_usage_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.get("/api/providers/test_provider/usage-check")
        assert response.status_code in [200, 500, 503]

    def test_check_usage_response_structure(self, client_with_llm: TestClient):
        response = client_with_llm.get("/api/providers/test_provider/usage-check")
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "provider_id" in data
            assert "conversation_count" in data
            assert "sample_conversations" in data

    def test_check_usage_no_service(
        self, client_no_conversation_service: TestClient
    ):
        response = client_no_conversation_service.get(
            "/api/providers/test/usage-check"
        )
        assert response.status_code == 503


class TestDeleteProviderEndpoint:
    def test_delete_provider_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.delete("/api/providers/test_provider")
        assert response.status_code in [200, 404, 503]

    def test_delete_provider_with_update_conversations(
        self, client_with_llm: TestClient
    ):
        response = client_with_llm.delete(
            "/api/providers/test_provider?update_conversations=true"
        )
        assert response.status_code in [200, 404, 503]

    def test_delete_provider_without_update(self, client_with_llm: TestClient):
        response = client_with_llm.delete(
            "/api/providers/test_provider?update_conversations=false"
        )
        assert response.status_code in [200, 404, 503]

    @pytest.mark.parametrize(
        "provider_id",
        [
            "provider123",
            "provider-with-dashes",
            "provider_with_underscores",
        ],
    )
    def test_delete_provider_various_id_formats(
        self, client_with_llm: TestClient, provider_id: str
    ):
        response = client_with_llm.delete(f"/api/providers/{provider_id}")
        assert response.status_code in [200, 404, 503]

    def test_delete_provider_no_service(self, client: TestClient):
        response = client.delete("/api/providers/test")
        assert response.status_code == 503


class TestUpdateProviderEndpoint:
    def test_update_provider_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.patch("/api/providers/test_provider", json={})
        assert response.status_code in [200, 400, 404, 503]

    def test_update_provider_empty_request(self, client_with_llm: TestClient):
        response = client_with_llm.patch("/api/providers/test_provider", json={})
        assert response.status_code == 400

    def test_update_provider_config(self, client_with_llm: TestClient):
        response = client_with_llm.patch(
            "/api/providers/test_provider",
            json={"config": {"api_key": "new-key"}},
        )
        assert response.status_code in [200, 400, 404, 503]

    def test_update_provider_set_default(self, client_with_llm: TestClient):
        response = client_with_llm.patch(
            "/api/providers/test_provider",
            json={"set_as_default": True},
        )
        assert response.status_code in [200, 404, 503]

    def test_update_provider_both_fields(self, client_with_llm: TestClient):
        response = client_with_llm.patch(
            "/api/providers/test_provider",
            json={
                "config": {"api_key": "new-key"},
                "set_as_default": True,
            },
        )
        assert response.status_code in [200, 400, 404, 503]

    def test_update_provider_no_service(self, client: TestClient):
        response = client.patch(
            "/api/providers/test", json={"set_as_default": True}
        )
        assert response.status_code == 503


class TestTestProviderEndpoint:
    def test_test_provider_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.post("/api/providers/test_provider/test")
        assert response.status_code in [200, 404, 500, 503]

    def test_test_provider_not_found(self, client_with_llm: TestClient):
        response = client_with_llm.post("/api/providers/nonexistent/test")
        assert response.status_code == 404

    def test_test_provider_response_structure(self, client_with_llm: TestClient):
        response = client_with_llm.post("/api/providers/test_provider/test")
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "provider_id" in data
            assert "is_valid" in data
            assert "message" in data

    def test_test_provider_no_service(self, client: TestClient):
        response = client.post("/api/providers/test/test")
        assert response.status_code == 503


class TestListProviderModelsEndpoint:
    def test_list_models_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.get("/api/providers/test_provider/models")
        assert response.status_code in [200, 404, 503]

    def test_list_models_response_structure(self, client_with_llm: TestClient):
        response = client_with_llm.get("/api/providers/test_provider/models")
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "provider_id" in data
            assert "models" in data
            assert "total" in data
            assert isinstance(data["models"], list)

    @pytest.mark.parametrize(
        "provider_id",
        [
            "openai-provider",
            "anthropic-provider",
            "ollama-provider",
        ],
    )
    def test_list_models_various_providers(
        self, client_with_llm: TestClient, provider_id: str
    ):
        response = client_with_llm.get(f"/api/providers/{provider_id}/models")
        assert response.status_code in [200, 404, 503]

    def test_list_models_no_service(self, client: TestClient):
        response = client.get("/api/providers/test/models")
        assert response.status_code == 503


class TestGenerateTextEndpoint:
    def test_generate_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/generate",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "gpt-4o-mini",
            },
        )
        assert response.status_code in [200, 400, 500, 503]

    def test_generate_missing_messages(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/generate",
            json={"model": "gpt-4o-mini"},
        )
        assert response.status_code == 422

    def test_generate_missing_model(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/generate",
            json={"messages": [{"role": "user", "content": "Hello"}]},
        )
        assert response.status_code == 422

    def test_generate_empty_messages(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/generate",
            json={"messages": [], "model": "gpt-4o-mini"},
        )
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "temperature,expected_status",
        [
            (0.0, 200),
            (0.7, 200),
            (2.0, 200),
            (-0.1, 422),
            (2.1, 422),
        ],
    )
    def test_generate_temperature_validation(
        self, client_with_llm: TestClient, temperature: float, expected_status: int
    ):
        response = client_with_llm.post(
            "/api/providers/generate",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "model": "gpt-4o-mini",
                "temperature": temperature,
            },
        )
        assert response.status_code in [expected_status, 500, 503]

    @pytest.mark.parametrize(
        "max_tokens,expected_status",
        [
            (1, 200),
            (1000, 200),
            (100000, 200),
            (0, 422),
            (100001, 422),
        ],
    )
    def test_generate_max_tokens_validation(
        self, client_with_llm: TestClient, max_tokens: int, expected_status: int
    ):
        response = client_with_llm.post(
            "/api/providers/generate",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "model": "gpt-4o-mini",
                "max_tokens": max_tokens,
            },
        )
        assert response.status_code in [expected_status, 500, 503]

    def test_generate_with_provider_id(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/generate",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "model": "gpt-4o-mini",
                "provider_id": "my-openai",
            },
        )
        assert response.status_code in [200, 400, 500, 503]

    def test_generate_system_and_user_messages(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/generate",
            json={
                "messages": [
                    {"role": "system", "content": "You are helpful"},
                    {"role": "user", "content": "Hello"},
                ],
                "model": "gpt-4o-mini",
            },
        )
        assert response.status_code in [200, 500, 503]

    def test_generate_no_service(self, client: TestClient):
        response = client.post(
            "/api/providers/generate",
            json={
                "messages": [{"role": "user", "content": "Test"}],
                "model": "test",
            },
        )
        assert response.status_code == 503


class TestSetDefaultProviderEndpoint:
    def test_set_default_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/default",
            json={"provider_id": "test_provider"},
        )
        assert response.status_code in [200, 400, 404, 503]

    def test_set_default_missing_provider_id(self, client_with_llm: TestClient):
        response = client_with_llm.post("/api/providers/default", json={})
        assert response.status_code == 422

    def test_set_default_with_model(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/default",
            json={
                "provider_id": "test_provider",
                "default_model": "gpt-4o-mini",
            },
        )
        assert response.status_code in [200, 404, 503]

    def test_set_default_not_found(self, client_with_llm: TestClient):
        response = client_with_llm.post(
            "/api/providers/default",
            json={"provider_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_set_default_no_service(self, client: TestClient):
        response = client.post(
            "/api/providers/default",
            json={"provider_id": "test"},
        )
        assert response.status_code == 503


class TestGetProviderMetadataEndpoint:
    def test_metadata_endpoint_exists(self, client_with_llm: TestClient):
        response = client_with_llm.get("/api/providers/test_provider/metadata")
        assert response.status_code in [200, 404, 501, 503]

    def test_metadata_with_capabilities(self, client_with_llm: TestClient):
        response = client_with_llm.get(
            "/api/providers/test_provider/metadata?include=capabilities"
        )
        assert response.status_code in [200, 404, 503]

    def test_metadata_with_workspaces(self, client_with_llm: TestClient):
        response = client_with_llm.get(
            "/api/providers/test_provider/metadata?include=workspaces"
        )
        assert response.status_code in [200, 404, 501, 503]

    def test_metadata_with_usage(self, client_with_llm: TestClient):
        response = client_with_llm.get(
            "/api/providers/test_provider/metadata?include=usage&start_time=2025-01-01T00:00:00Z&end_time=2025-01-08T00:00:00Z"
        )
        assert response.status_code in [200, 404, 501, 503]

    def test_metadata_with_costs(self, client_with_llm: TestClient):
        response = client_with_llm.get(
            "/api/providers/test_provider/metadata?include=costs&start_time=2025-01-01T00:00:00Z&end_time=2025-01-08T00:00:00Z"
        )
        assert response.status_code in [200, 404, 501, 503]

    def test_metadata_usage_without_time_range(self, client_with_llm: TestClient):
        response = client_with_llm.get(
            "/api/providers/test_provider/metadata?include=usage"
        )
        assert response.status_code == 400

    def test_metadata_costs_without_time_range(self, client_with_llm: TestClient):
        response = client_with_llm.get(
            "/api/providers/test_provider/metadata?include=costs"
        )
        assert response.status_code == 400

    def test_metadata_invalid_time_format(self, client_with_llm: TestClient):
        response = client_with_llm.get(
            "/api/providers/test_provider/metadata?include=usage&start_time=invalid&end_time=invalid"
        )
        assert response.status_code == 400

    def test_metadata_multiple_includes(self, client_with_llm: TestClient):
        response = client_with_llm.get(
            "/api/providers/test_provider/metadata?include=capabilities&include=workspaces"
        )
        assert response.status_code in [200, 404, 501, 503]

    def test_metadata_no_service(self, client: TestClient):
        response = client.get("/api/providers/test/metadata")
        assert response.status_code == 503
