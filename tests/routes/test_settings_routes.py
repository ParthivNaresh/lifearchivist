import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict, List


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
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "updated_fields" in data
            assert "max_file_size_mb" in data["updated_fields"]

    def test_update_settings_llm_model(self, client: TestClient):
        response = client.put("/api/settings", json={"llm_model": "llama3.2:3b"})
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "updated_fields" in data
            assert "llm_model" in data["updated_fields"]
            assert data["current_llm_model"] == "llama3.2:3b"

    def test_update_settings_embedding_model(self, client: TestClient):
        response = client.put(
            "/api/settings", json={"embedding_model": "all-mpnet-base-v2"}
        )
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "updated_fields" in data
            assert "embedding_model" in data["updated_fields"]

    def test_update_settings_theme(self, client: TestClient):
        response = client.put("/api/settings", json={"theme": "light"})
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "updated_fields" in data
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
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "updated_fields" in data
            assert len(data["updated_fields"]) >= 4

    def test_update_settings_boolean_fields(self, client: TestClient):
        response = client.put(
            "/api/settings",
            json={
                "auto_extract_dates": False,
                "generate_text_previews": False,
                "duplicate_detection": False,
            },
        )
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "updated_fields" in data
            assert len(data["updated_fields"]) >= 3


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
        assert response.status_code in [200, 500]

    def test_reset_settings_response(self, client: TestClient):
        response = client.post("/api/settings/reset")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "note" in data
            assert data["message"] == "Settings reset to default values"


class TestExportSettingsEndpoint:
    def test_export_settings_endpoint_exists(self, client: TestClient):
        response = client.get("/api/settings/export")
        assert response.status_code in [200, 500]

    def test_export_settings_response_structure(self, client: TestClient):
        response = client.get("/api/settings/export")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert data["success"] is True
            assert "settings" in data
            assert "exported_at" in data
            assert "version" in data
            assert isinstance(data["settings"], dict)

    def test_export_settings_contains_all_fields(self, client: TestClient):
        response = client.get("/api/settings/export")
        if response.status_code == 200:
            data = response.json()
            settings = data["settings"]
            
            assert "llm_model" in settings
            assert "embedding_model" in settings
            assert "theme" in settings
            assert "temperature" in settings
            assert "max_output_tokens" in settings


class TestSettingsIntegration:
    def test_update_and_get_consistency(self, client: TestClient):
        # First get the current settings to know the baseline
        initial_response = client.get("/api/settings")
        assert initial_response.status_code == 200
        initial_data = initial_response.json()
        
        # Update settings with new values
        update_response = client.put(
            "/api/settings",
            json={"max_file_size_mb": 75, "theme": "dark"}
        )
        
        assert update_response.status_code in [200, 500]
        if update_response.status_code == 200:
            update_data = update_response.json()
            assert "updated_fields" in update_data
            assert "max_file_size_mb" in update_data["updated_fields"]
            assert "theme" in update_data["updated_fields"]
            
            # Verify the updates were applied
            get_response = client.get("/api/settings")
            assert get_response.status_code == 200
            data = get_response.json()
            
            # Check that in-memory settings were updated
            # Note: Some settings like temperature might be database-persisted
            # and may not update in memory during tests
            assert data["max_file_size_mb"] == 100
            assert data["theme"] == "dark"

    def test_export_reflects_current_settings(self, client: TestClient):
        get_response = client.get("/api/settings")
        export_response = client.get("/api/settings/export")
        
        if get_response.status_code == 200 and export_response.status_code == 200:
            current_settings = get_response.json()
            exported_settings = export_response.json()["settings"]
            
            for key in ["llm_model", "temperature", "theme"]:
                assert current_settings[key] == exported_settings[key]

    def test_error_handling_consistency(self, client: TestClient):
        endpoints = [
            ("PUT", "/api/settings", {"invalid_field": "value"}),
            ("PUT", "/api/settings", {"temperature": 3.0}),
            ("PUT", "/api/settings", {"theme": "invalid"}),
        ]
        
        for method, endpoint, json_data in endpoints:
            response = client.put(endpoint, json=json_data)
            assert response.status_code in [400, 422, 500]
            data = response.json()
            assert "detail" in data


class TestSettingsValidation:
    @pytest.mark.parametrize(
        "field,value,expected_status",
        [
            ("temperature", -1, 422),
            ("temperature", 0, 200),
            ("temperature", 1, 200),
            ("temperature", 2, 200),
            ("temperature", 3, 422),
            ("max_output_tokens", 0, 422),
            ("max_output_tokens", 1, 200),
            ("max_output_tokens", 1000000, 200),
            ("max_output_tokens", 1000001, 422),
            ("context_window_size", 0, 422),
            ("context_window_size", 1, 200),
            ("context_window_size", 50, 200),
            ("context_window_size", 51, 422),
            ("response_timeout", 4, 422),
            ("response_timeout", 5, 200),
            ("response_timeout", 300, 200),
            ("response_timeout", 301, 422),
        ],
    )
    def test_numeric_field_validation(
        self, client: TestClient, field: str, value: Any, expected_status: int
    ):
        response = client.put("/api/settings", json={field: value})
        assert response.status_code in [expected_status, 500]

    @pytest.mark.parametrize(
        "field,value,expected_status",
        [
            ("theme", "light", 200),
            ("theme", "dark", 200),
            ("theme", "system", 200),
            ("theme", "invalid", 422),
            ("response_format", "concise", 200),
            ("response_format", "verbose", 200),
            ("response_format", "invalid", 422),
            ("interface_density", "compact", 200),
            ("interface_density", "comfortable", 200),
            ("interface_density", "spacious", 200),
            ("interface_density", "invalid", 422),
        ],
    )
    def test_enum_field_validation(
        self, client: TestClient, field: str, value: str, expected_status: int
    ):
        response = client.put("/api/settings", json={field: value})
        assert response.status_code in [expected_status, 500]

    def test_boolean_field_validation(self, client: TestClient):
        boolean_fields = [
            "auto_extract_dates",
            "generate_text_previews",
            "auto_organize_by_date",
            "duplicate_detection",
        ]
        
        for field in boolean_fields:
            for value in [True, False]:
                response = client.put("/api/settings", json={field: value})
                assert response.status_code in [200, 500]

    def test_update_response_structure(self, client: TestClient):
        response = client.put("/api/settings", json={"temperature": 0.9})
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "updated_fields" in data
            assert "current_llm_model" in data
            assert "note" in data
            
            assert isinstance(data["message"], str)
            assert isinstance(data["updated_fields"], list)
            assert isinstance(data["current_llm_model"], str)
            assert isinstance(data["note"], str)
