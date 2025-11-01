import pytest
from fastapi.testclient import TestClient


class TestGetSettingsEndpoint:
    def test_get_settings_endpoint_exists(self, client: TestClient):
        response = client.get("/api/settings")
        assert response.status_code == 200

    def test_get_settings_response_structure(self, client: TestClient):
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()

        assert "auto_extract_dates" in data
        assert "generate_text_previews" in data
        assert "max_file_size_mb" in data
        assert "llm_model" in data
        assert "embedding_model" in data
        assert "search_results_limit" in data
        assert "temperature" in data
        assert "max_output_tokens" in data
        assert "response_format" in data
        assert "context_window_size" in data
        assert "response_timeout" in data
        assert "auto_organize_by_date" in data
        assert "duplicate_detection" in data
        assert "default_import_location" in data
        assert "theme" in data
        assert "interface_density" in data
        assert "vault_path" in data
        assert "lifearch_home" in data

    def test_get_settings_data_types(self, client: TestClient):
        response = client.get("/api/settings")
        data = response.json()

        assert isinstance(data["auto_extract_dates"], bool)
        assert isinstance(data["generate_text_previews"], bool)
        assert isinstance(data["max_file_size_mb"], int)
        assert isinstance(data["llm_model"], str)
        assert isinstance(data["embedding_model"], str)
        assert isinstance(data["search_results_limit"], int)
        assert isinstance(data["temperature"], (int, float))
        assert isinstance(data["max_output_tokens"], int)
        assert isinstance(data["response_format"], str)
        assert isinstance(data["context_window_size"], int)
        assert isinstance(data["response_timeout"], int)
        assert isinstance(data["theme"], str)
        assert isinstance(data["vault_path"], str)
        assert isinstance(data["lifearch_home"], str)

    def test_get_settings_default_values(self, client: TestClient):
        response = client.get("/api/settings")
        data = response.json()

        assert data["temperature"] >= 0 and data["temperature"] <= 2
        assert data["max_output_tokens"] >= 1
        assert data["context_window_size"] >= 1
        assert data["response_timeout"] >= 5


class TestUpdateSettingsEndpoint:
    def test_update_settings_endpoint_exists(self, client: TestClient):
        response = client.put("/api/settings", json={})
        assert response.status_code in [200, 400]

    def test_update_settings_empty_request(self, client: TestClient):
        response = client.put("/api/settings", json={})
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data

    def test_update_settings_max_file_size(self, client: TestClient):
        response = client.put("/api/settings", json={"max_file_size_mb": 50})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "max_file_size_mb" in data["updated_fields"]

    def test_update_settings_llm_model(self, client: TestClient):
        response = client.put("/api/settings", json={"llm_model": "llama3.2:3b"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "llm_model" in data["updated_fields"]
        assert data["current_llm_model"] == "llama3.2:3b"

    def test_update_settings_embedding_model(self, client: TestClient):
        response = client.put(
            "/api/settings", json={"embedding_model": "all-mpnet-base-v2"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "embedding_model" in data["updated_fields"]

    def test_update_settings_theme(self, client: TestClient):
        response = client.put("/api/settings", json={"theme": "light"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "theme" in data["updated_fields"]

    @pytest.mark.parametrize(
        "theme",
        ["light", "dark", "system"],
    )
    def test_update_settings_valid_themes(self, client: TestClient, theme: str):
        response = client.put("/api/settings", json={"theme": theme})
        assert response.status_code == 200

    def test_update_settings_invalid_theme(self, client: TestClient):
        response = client.put("/api/settings", json={"theme": "invalid"})
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "temperature,expected_status",
        [
            (0.0, 200),
            (0.5, 200),
            (1.0, 200),
            (2.0, 200),
            (-0.1, 422),
            (2.1, 422),
        ],
    )
    def test_update_settings_temperature_validation(
        self, client: TestClient, temperature: float, expected_status: int
    ):
        response = client.put("/api/settings", json={"temperature": temperature})
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "max_tokens,expected_status",
        [
            (1, 200),
            (1000, 200),
            (100000, 200),
            (1000000, 200),
            (0, 422),
            (1000001, 422),
        ],
    )
    def test_update_settings_max_tokens_validation(
        self, client: TestClient, max_tokens: int, expected_status: int
    ):
        response = client.put("/api/settings", json={"max_output_tokens": max_tokens})
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "response_format",
        ["concise", "verbose"],
    )
    def test_update_settings_valid_response_formats(
        self, client: TestClient, response_format: str
    ):
        response = client.put("/api/settings", json={"response_format": response_format})
        assert response.status_code == 200

    def test_update_settings_invalid_response_format(self, client: TestClient):
        response = client.put("/api/settings", json={"response_format": "invalid"})
        assert response.status_code == 422

    @pytest.mark.parametrize(
        "context_size,expected_status",
        [
            (1, 200),
            (10, 200),
            (50, 200),
            (0, 422),
            (51, 422),
        ],
    )
    def test_update_settings_context_window_validation(
        self, client: TestClient, context_size: int, expected_status: int
    ):
        response = client.put(
            "/api/settings", json={"context_window_size": context_size}
        )
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "timeout,expected_status",
        [
            (5, 200),
            (30, 200),
            (300, 200),
            (4, 422),
            (301, 422),
        ],
    )
    def test_update_settings_timeout_validation(
        self, client: TestClient, timeout: int, expected_status: int
    ):
        response = client.put("/api/settings", json={"response_timeout": timeout})
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "file_size,expected_status",
        [
            (1, 200),
            (50, 200),
            (1000, 200),
            (0, 422),
            (1001, 422),
        ],
    )
    def test_update_settings_file_size_validation(
        self, client: TestClient, file_size: int, expected_status: int
    ):
        response = client.put("/api/settings", json={"max_file_size_mb": file_size})
        assert response.status_code == expected_status

    @pytest.mark.parametrize(
        "density",
        ["compact", "comfortable", "spacious"],
    )
    def test_update_settings_valid_interface_density(
        self, client: TestClient, density: str
    ):
        response = client.put("/api/settings", json={"interface_density": density})
        assert response.status_code == 200

    def test_update_settings_invalid_interface_density(self, client: TestClient):
        response = client.put("/api/settings", json={"interface_density": "invalid"})
        assert response.status_code == 422

    def test_update_settings_multiple_fields(self, client: TestClient):
        response = client.put(
            "/api/settings",
            json={
                "max_file_size_mb": 75,
                "theme": "dark",
                "temperature": 0.8,
                "search_results_limit": 50,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["updated_fields"]) == 4

    def test_update_settings_boolean_fields(self, client: TestClient):
        response = client.put(
            "/api/settings",
            json={
                "auto_extract_dates": False,
                "generate_text_previews": False,
                "duplicate_detection": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestGetAvailableModelsEndpoint:
    def test_get_models_endpoint_exists(self, client: TestClient):
        response = client.get("/api/settings/models")
        assert response.status_code == 200

    def test_get_models_response_structure(self, client: TestClient):
        response = client.get("/api/settings/models")
        assert response.status_code == 200
        data = response.json()

        assert "llm_models" in data
        assert "embedding_models" in data
        assert isinstance(data["llm_models"], list)
        assert isinstance(data["embedding_models"], list)

    def test_get_models_embedding_models_present(self, client: TestClient):
        response = client.get("/api/settings/models")
        data = response.json()

        assert len(data["embedding_models"]) > 0
        for model in data["embedding_models"]:
            assert "id" in model
            assert "name" in model
            assert "description" in model


class TestResetSettingsEndpoint:
    def test_reset_settings_endpoint_exists(self, client: TestClient):
        response = client.post("/api/settings/reset")
        assert response.status_code == 200

    def test_reset_settings_response(self, client: TestClient):
        response = client.post("/api/settings/reset")
        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert data["success"] is True
        assert "message" in data


class TestExportSettingsEndpoint:
    def test_export_settings_endpoint_exists(self, client: TestClient):
        response = client.get("/api/settings/export")
        assert response.status_code == 200

    def test_export_settings_response_structure(self, client: TestClient):
        response = client.get("/api/settings/export")
        assert response.status_code == 200
        data = response.json()

        assert "success" in data
        assert data["success"] is True
        assert "settings" in data
        assert "exported_at" in data
        assert "version" in data
        assert isinstance(data["settings"], dict)

    def test_export_settings_contains_all_fields(self, client: TestClient):
        response = client.get("/api/settings/export")
        data = response.json()
        settings = data["settings"]

        assert "llm_model" in settings
        assert "embedding_model" in settings
        assert "theme" in settings
        assert "temperature" in settings
        assert "max_output_tokens" in settings
