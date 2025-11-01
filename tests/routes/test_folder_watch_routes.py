from fastapi.testclient import TestClient


class TestAddFolderEndpoint:
    def test_add_folder_endpoint_exists(self, client: TestClient):
        response = client.post(
            "/api/folder-watch/folders",
            json={"folder_path": "/test/path"},
        )
        assert response.status_code in [201, 400, 503]

    def test_add_folder_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.post(
            "/api/folder-watch/folders",
            json={"folder_path": "/test/path"},
        )
        assert response.status_code == 503

    def test_add_folder_missing_path(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.post(
            "/api/folder-watch/folders",
            json={},
        )
        assert response.status_code == 422


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
        assert response.status_code in [200, 404, 503]

    def test_get_folder_not_found(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders/nonexistent-id"
        )
        assert response.status_code == 404

    def test_get_folder_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.get(
            "/api/folder-watch/folders/test-id"
        )
        assert response.status_code == 503


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
        assert response.status_code in [200, 404, 503]

    def test_update_folder_enable(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.patch(
            "/api/folder-watch/folders/test-folder-id",
            json={"enabled": True},
        )
        assert response.status_code in [200, 404]

    def test_update_folder_disable(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.patch(
            "/api/folder-watch/folders/test-folder-id",
            json={"enabled": False},
        )
        assert response.status_code in [200, 404]

    def test_update_folder_not_found(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.patch(
            "/api/folder-watch/folders/nonexistent-id",
            json={"enabled": True},
        )
        assert response.status_code == 404

    def test_update_folder_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.patch(
            "/api/folder-watch/folders/test-id",
            json={"enabled": True},
        )
        assert response.status_code == 503


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
        assert response.status_code in [200, 404, 503]

    def test_folder_status_not_found(self, client_with_folder_watcher: TestClient):
        response = client_with_folder_watcher.get(
            "/api/folder-watch/folders/nonexistent-id/status"
        )
        assert response.status_code == 404

    def test_folder_status_no_watcher(self, client_no_folder_watcher: TestClient):
        response = client_no_folder_watcher.get(
            "/api/folder-watch/folders/test-id/status"
        )
        assert response.status_code == 503
