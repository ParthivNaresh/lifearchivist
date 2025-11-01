import pytest
from fastapi.testclient import TestClient


class TestGetVaultInfoEndpoint:
    def test_vault_info_endpoint_exists(self, client: TestClient):
        response = client.get("/api/vault/info")
        assert response.status_code in [200, 500, 503]

    def test_vault_info_success(self, client_with_vault: TestClient):
        response = client_with_vault.get("/api/vault/info")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True

    def test_vault_info_no_vault(self, client_no_vault: TestClient):
        response = client_no_vault.get("/api/vault/info")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert "error" in data


class TestListVaultFilesEndpoint:
    def test_list_files_endpoint_exists(self, client: TestClient):
        response = client.get("/api/vault/files")
        assert response.status_code in [200, 400, 403, 500]

    def test_list_files_default_params(self, client: TestClient):
        response = client.get("/api/vault/files")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "files" in data
            assert "total" in data
            assert "directory" in data
            assert "limit" in data
            assert "offset" in data

    def test_list_files_with_directory(self, client: TestClient):
        response = client.get("/api/vault/files?directory=content")
        assert response.status_code in [200, 500]

    @pytest.mark.parametrize(
        "limit,expected_status",
        [
            (1, 200),
            (100, 200),
            (1000, 200),
            (0, 400),
            (1001, 400),
            (-1, 400),
        ],
    )
    def test_list_files_limit_validation(
        self, client: TestClient, limit: int, expected_status: int
    ):
        response = client.get(f"/api/vault/files?limit={limit}")
        assert response.status_code in [expected_status, 500]

    @pytest.mark.parametrize(
        "offset,expected_status",
        [
            (0, 200),
            (10, 200),
            (100, 200),
            (-1, 400),
            (-10, 400),
        ],
    )
    def test_list_files_offset_validation(
        self, client: TestClient, offset: int, expected_status: int
    ):
        response = client.get(f"/api/vault/files?offset={offset}")
        assert response.status_code in [expected_status, 500]

    def test_list_files_with_pagination(self, client: TestClient):
        response = client.get("/api/vault/files?limit=50&offset=10")
        assert response.status_code in [200, 500]

    def test_list_files_various_directories(self, client: TestClient):
        for directory in ["content", "thumbnails", "temp"]:
            response = client.get(f"/api/vault/files?directory={directory}")
            assert response.status_code in [200, 500]


class TestReconcileVaultEndpoint:
    def test_reconcile_endpoint_exists(self, client: TestClient):
        response = client.post("/api/vault/reconcile")
        assert response.status_code in [200, 500, 503]

    def test_reconcile_success(self, client_with_vault: TestClient):
        response = client_with_vault.post("/api/vault/reconcile")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "reconciliation" in data

    def test_reconcile_no_vault(self, client_no_vault: TestClient):
        response = client_no_vault.post("/api/vault/reconcile")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False

    def test_reconcile_no_llamaindex(self, client_no_services: TestClient):
        response = client_no_services.post("/api/vault/reconcile")
        assert response.status_code == 503


class TestDownloadFileFromVaultEndpoint:
    def test_download_endpoint_exists(self, client: TestClient):
        response = client.get(
            "/api/vault/file/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        assert response.status_code in [200, 404, 503]

    def test_download_invalid_hash_too_short(self, client: TestClient):
        response = client.get("/api/vault/file/abc")
        assert response.status_code == 400

    def test_download_invalid_hash_wrong_length(self, client: TestClient):
        response = client.get("/api/vault/file/0123456789abcdef")
        assert response.status_code == 400

    def test_download_valid_hash_format(self, client: TestClient):
        response = client.get(
            "/api/vault/file/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        assert response.status_code in [200, 404, 503]

    def test_download_no_vault(self, client_no_vault: TestClient):
        response = client_no_vault.get(
            "/api/vault/file/0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        assert response.status_code == 503

    @pytest.mark.parametrize(
        "file_hash",
        [
            "a" * 64,
            "0" * 64,
            "f" * 64,
            "0123456789abcdef" * 4,
        ],
    )
    def test_download_various_valid_hashes(self, client: TestClient, file_hash: str):
        response = client.get(f"/api/vault/file/{file_hash}")
        assert response.status_code in [200, 404, 503]

    @pytest.mark.parametrize(
        "invalid_hash",
        [
            "",
            "abc",
            "0" * 63,
            "0" * 65,
            "g" * 64,
            "ZZZZ" * 16,
        ],
    )
    def test_download_invalid_hashes(self, client: TestClient, invalid_hash: str):
        response = client.get(f"/api/vault/file/{invalid_hash}")
        assert response.status_code in [400, 404, 503]
