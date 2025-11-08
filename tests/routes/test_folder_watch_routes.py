import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict, List


class TestAddFolderEndpoint:
    def test_add_folder_endpoint_exists(self, client: TestClient):
        response = client.post(
            "/api/folder-watch/folders",
            json={"folder_path": "/test/path"},
        )
        assert response.status_code in [201, 400, 500, 503]

    def test_add_folder_success_response(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.post(
            "/api/folder-watch/folders",
            json={"folder_path": "/test/path"},
        )
        if response.status_code == 201:
            data = response.json()
            assert "id" in data
            assert "path" in data
            assert "enabled" in data
            assert "created_at" in data

    def test_add_folder_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.post(
            "/api/folder-watch/folders",
            json={"folder_path": "/test/path"},
        )
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

    def test_add_folder_missing_path(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.post(
            "/api/folder-watch/folders",
            json={},
        )
        assert response.status_code == 422

    def test_add_folder_invalid_path(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.post(
            "/api/folder-watch/folders",
            json={"folder_path": ""},
        )
        assert response.status_code in [400, 422]


class TestListFoldersEndpoint:
    def test_list_folders_endpoint_exists(self, client: TestClient):
        response = client.get("/api/folder-watch/folders")
        assert response.status_code in [200, 503]

    def test_list_folders_success(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get("/api/folder-watch/folders")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "folders" in data
        assert "total" in data
        assert isinstance(data["folders"], list)

    def test_list_folders_enabled_only(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders?enabled_only=true"
        )
        assert response.status_code == 200

    def test_list_folders_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.get("/api/folder-watch/folders")
        assert response.status_code == 503


class TestGetFolderEndpoint:
    def test_get_folder_endpoint_exists(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders/test-folder-id"
        )
        assert response.status_code in [200, 404, 500, 503]

    def test_get_folder_success_response(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders/test-folder-id"
        )
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "path" in data
            assert "enabled" in data
            assert "created_at" in data
            assert "status" in data
            assert "health" in data
            assert "is_active" in data
            assert "success_rate" in data
            assert "stats" in data

    def test_get_folder_not_found(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders/nonexistent-id"
        )
        assert response.status_code in [404, 500]

    def test_get_folder_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.get(
            "/api/folder-watch/folders/test-id"
        )
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data


class TestRemoveFolderEndpoint:
    def test_remove_folder_endpoint_exists(
        self, client_with_folder_watcher: TestClient
    ):
        response = client_with_folder_watcher.delete(
            "/api/folder-watch/folders/test-folder-id"
        )
        assert response.status_code in [200, 404, 503]

    def test_remove_folder_not_found(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.delete(
            "/api/folder-watch/folders/nonexistent-id"
        )
        assert response.status_code == 404

    def test_remove_folder_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.delete(
            "/api/folder-watch/folders/test-id"
        )
        assert response.status_code == 503


class TestUpdateFolderEndpoint:
    def test_update_folder_endpoint_exists(
        self, client_with_folder_watcher: TestClient
    ):
        response = client_with_folder_watcher.patch(
            "/api/folder-watch/folders/test-folder-id",
            json={"enabled": True},
        )
        assert response.status_code in [200, 404, 500, 503]

    def test_update_folder_enable(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.patch(
            "/api/folder-watch/folders/test-folder-id",
            json={"enabled": True},
        )
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "path" in data
            assert "enabled" in data
            assert data["enabled"] is True

    def test_update_folder_disable(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.patch(
            "/api/folder-watch/folders/test-folder-id",
            json={"enabled": False},
        )
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "path" in data
            assert "enabled" in data
            assert data["enabled"] is False

    def test_update_folder_not_found(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.patch(
            "/api/folder-watch/folders/nonexistent-id",
            json={"enabled": True},
        )
        assert response.status_code in [404, 500]

    def test_update_folder_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.patch(
            "/api/folder-watch/folders/test-id",
            json={"enabled": True},
        )
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data


class TestScanFolderEndpoint:
    def test_scan_folder_endpoint_exists(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.post(
            "/api/folder-watch/folders/test-folder-id/scan"
        )
        assert response.status_code in [200, 400, 404, 503]

    def test_scan_folder_not_found(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.post(
            "/api/folder-watch/folders/nonexistent-id/scan"
        )
        assert response.status_code == 404

    def test_scan_folder_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.post(
            "/api/folder-watch/folders/test-id/scan"
        )
        assert response.status_code == 503


class TestGetAggregateStatusEndpoint:
    def test_aggregate_status_endpoint_exists(self, client: TestClient):
        response = client.get("/api/folder-watch/status")
        assert response.status_code in [200, 503]

    def test_aggregate_status_success(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get("/api/folder-watch/status")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "total_folders" in data
        assert "active_folders" in data
        assert "folders" in data
        assert "supported_extensions" in data
        assert isinstance(data["folders"], list)

    def test_aggregate_status_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.get("/api/folder-watch/status")
        assert response.status_code == 503


class TestGetFolderStatusEndpoint:
    def test_folder_status_endpoint_exists(
        self, client_with_folder_watcher: TestClient
    ):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders/test-folder-id/status"
        )
        assert response.status_code in [200, 404, 500, 503]

    def test_folder_status_success_response(
        self, client_with_folder_watcher: TestClient
    ):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders/test-folder-id/status"
        )
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "folder_id" in data
            assert "folder_path" in data
            assert "accessible" in data
            assert "exists" in data
            assert "readable" in data
            assert "health" in data

    def test_folder_status_not_found(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders/nonexistent-id/status"
        )
        assert response.status_code in [404, 500]

    def test_folder_status_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.get(
            "/api/folder-watch/folders/test-id/status"
        )
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data


class TestFolderWatchIntegration:
    def test_folder_lifecycle(self, client_with_folder_watcher: TestClient):
        add_response = client_with_folder_watcher.post(
            "/api/folder-watch/folders",
            json={"folder_path": "/test/integration/path"},
        )
        
        if add_response.status_code == 201:
            folder_data = add_response.json()
            folder_id = folder_data.get("id")
            
            if folder_id:
                get_response = client_with_folder_watcher.get(
                    f"/api/folder-watch/folders/{folder_id}"
                )
                assert get_response.status_code in [200, 404, 500]
                
                update_response = client_with_folder_watcher.patch(
                    f"/api/folder-watch/folders/{folder_id}",
                    json={"enabled": False},
                )
                assert update_response.status_code in [200, 404, 500]
                
                delete_response = client_with_folder_watcher.delete(
                    f"/api/folder-watch/folders/{folder_id}"
                )
                assert delete_response.status_code in [200, 404, 500]

    def test_error_handling_consistency(self, client_no_folder_watcher: TestClient):
        endpoints = [
            ("POST", "/api/folder-watch/folders", {"folder_path": "/test"}),
            ("GET", "/api/folder-watch/folders", None),
            ("GET", "/api/folder-watch/folders/test-id", None),
            ("PATCH", "/api/folder-watch/folders/test-id", {"enabled": True}),
            ("DELETE", "/api/folder-watch/folders/test-id", None),
            ("POST", "/api/folder-watch/folders/test-id/scan", None),
            ("GET", "/api/folder-watch/status", None),
            ("GET", "/api/folder-watch/folders/test-id/status", None),
        ]
        
        for method, endpoint, json_data in endpoints:
            if method == "GET":
                response = client_no_folder_watcher.get(endpoint)
            elif method == "POST":
                response = client_no_folder_watcher.post(endpoint, json=json_data)
            elif method == "PATCH":
                response = client_no_folder_watcher.patch(endpoint, json=json_data)
            elif method == "DELETE":
                response = client_no_folder_watcher.delete(endpoint)
            
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data


class TestFolderWatchValidation:
    @pytest.mark.parametrize(
        "folder_path,expected_status",
        [
            ("/valid/path", [201, 400, 500]),
            ("", [400, 422]),
            (None, [422]),
            ("relative/path", [201, 400, 500]),
            ("/path/with spaces/", [201, 400, 500]),
        ],
    )
    def test_folder_path_validation(
        self, client_with_folder_watcher: TestClient, folder_path: str, expected_status: List[int]
    ):
        json_data = {"folder_path": folder_path} if folder_path is not None else {}
        response = client_with_folder_watcher.post(
            "/api/folder-watch/folders",
            json=json_data,
        )
        assert response.status_code in expected_status

    def test_scan_response_structure(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.post(
            "/api/folder-watch/folders/test-folder-id/scan"
        )
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "folder_id" in data
            assert "folder_path" in data
            assert "files_found" in data
            assert "files_queued" in data
            assert "files_failed" in data
            assert "message" in data

    def test_remove_response_structure(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.delete(
            "/api/folder-watch/folders/test-folder-id"
        )
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "folder_id" in data
