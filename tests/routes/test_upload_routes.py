import io

import pytest
from fastapi.testclient import TestClient


class TestIngestEndpoint:
    def test_ingest_endpoint_exists(self, client: TestClient):
        response = client.post("/api/ingest", json={"path": "/test/path.pdf"})
        assert response.status_code in [200, 400, 422, 500]

    def test_ingest_with_valid_path(self, client: TestClient):
        response = client.post(
            "/api/ingest",
            json={
                "path": "/test/document.pdf",
                "tags": ["test"],
                "metadata": {"source": "test"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "file_id" in data

    def test_ingest_with_session_id(self, client: TestClient):
        response = client.post(
            "/api/ingest",
            json={
                "path": "/test/document.pdf",
                "session_id": "test_session_123",
            },
        )
        assert response.status_code == 200

    def test_ingest_error_response_structure(self, client: TestClient):
        response = client.post("/api/ingest", json={})
        data = response.json()

        if not data.get("success", True):
            assert "error" in data
            assert "error_type" in data
            assert isinstance(data["error"], str)
            assert isinstance(data["error_type"], str)


class TestUploadEndpoint:
    def test_upload_endpoint_exists(self, client: TestClient):
        response = client.post("/api/upload")
        assert response.status_code in [400, 422]

    def test_upload_missing_file(self, client: TestClient):
        response = client.post("/api/upload", data={"tags": "[]", "metadata": "{}"})
        assert response.status_code == 422

    def test_upload_with_file(self, client: TestClient):
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"tags": "[]", "metadata": "{}"}

        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code == 200
        result = response.json()
        assert result["success"] is True

    def test_upload_with_tags_and_metadata(self, client: TestClient):
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {
            "tags": '["important", "work"]',
            "metadata": '{"project": "test_project"}',
        }

        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code == 200

    def test_upload_with_session_id(self, client: TestClient):
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"tags": "[]", "metadata": "{}", "session_id": "session_123"}

        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        "invalid_tags,invalid_metadata",
        [
            ("not_json", "{}"),
            ("[]", "not_json"),
            ("{}", "{}"),
            ('"string"', "{}"),
        ],
    )
    def test_upload_invalid_json(
        self, client: TestClient, invalid_tags: str, invalid_metadata: str
    ):
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"tags": invalid_tags, "metadata": invalid_metadata}

        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code == 400
        result = response.json()
        assert result["success"] is False
        assert result["error_type"] == "ValidationError"

    def test_upload_no_filename(self, client: TestClient):
        file_content = b"Test file content"
        files = {"file": ("", io.BytesIO(file_content), "text/plain")}
        data = {"tags": "[]", "metadata": "{}"}

        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code in [400, 422]
        if response.status_code == 400:
            result = response.json()
            assert result["error_type"] == "ValidationError"
            assert "filename" in result["error"].lower()


class TestBulkIngestEndpoint:
    def test_bulk_ingest_endpoint_exists(self, client: TestClient):
        response = client.post("/api/bulk-ingest", json={"file_paths": []})
        assert response.status_code in [200, 400]

    def test_bulk_ingest_empty_list(self, client: TestClient):
        response = client.post(
            "/api/bulk-ingest", json={"file_paths": [], "folder_path": "/test"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "ValidationError"
        assert "no file paths" in data["error"].lower()

    def test_bulk_ingest_too_many_files(self, client: TestClient):
        file_paths = [f"/test/file{i}.txt" for i in range(1001)]
        response = client.post(
            "/api/bulk-ingest", json={"file_paths": file_paths, "folder_path": "/test"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "1000" in data["error"]

    def test_bulk_ingest_valid_request(self, client: TestClient):
        file_paths = ["/test/file1.txt", "/test/file2.txt", "/test/file3.txt"]
        response = client.post(
            "/api/bulk-ingest",
            json={"file_paths": file_paths, "folder_path": "/test/folder"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_files"] == 3
        assert "successful_count" in data
        assert "failed_count" in data
        assert "success_rate" in data
        assert "results" in data

    def test_bulk_ingest_response_structure(self, client: TestClient):
        file_paths = ["/test/file1.txt"]
        response = client.post(
            "/api/bulk-ingest", json={"file_paths": file_paths, "folder_path": "/test"}
        )
        data = response.json()

        assert "total_files" in data
        assert "successful_count" in data
        assert "failed_count" in data
        assert "success_rate" in data
        assert "folder_path" in data
        assert "results" in data
        assert isinstance(data["results"], list)

    @pytest.mark.parametrize("file_count", [1, 10, 50, 100, 500, 1000])
    def test_bulk_ingest_various_counts(self, client: TestClient, file_count: int):
        file_paths = [f"/test/file{i}.txt" for i in range(file_count)]
        response = client.post(
            "/api/bulk-ingest", json={"file_paths": file_paths, "folder_path": "/test"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == file_count


class TestProgressEndpoint:
    def test_progress_endpoint_exists(self, client: TestClient):
        response = client.get("/api/upload/test_id/progress")
        assert response.status_code in [200, 400, 404, 503]

    def test_progress_invalid_file_id_short(self, client: TestClient):
        response = client.get("/api/upload/ab/progress")
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "ValidationError"

    def test_progress_invalid_file_id_empty(self, client: TestClient):
        response = client.get("/api/upload//progress")
        assert response.status_code == 404

    def test_progress_valid_file_id(self, client: TestClient):
        response = client.get("/api/upload/valid_id/progress")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data
        assert "progress" in data

    def test_progress_not_found(self, client: TestClient):
        response = client.get("/api/upload/nonexistent_id_123/progress")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "NotFoundError"

    def test_progress_no_manager(self, client_no_services: TestClient):
        response = client_no_services.get("/api/upload/test_id/progress")
        assert response.status_code == 503
        data = response.json()
        assert data["success"] is False
        assert data["error_type"] == "ServiceUnavailable"

    @pytest.mark.parametrize(
        "file_id",
        [
            "abc123",
            "file_id_with_underscores",
            "file-id-with-dashes",
            "FileIdWithCaps",
            "123456789",
        ],
    )
    def test_progress_various_file_id_formats(self, client: TestClient, file_id: str):
        response = client.get(f"/api/upload/{file_id}/progress")
        assert response.status_code in [200, 404]
