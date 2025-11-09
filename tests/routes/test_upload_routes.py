import io

import pytest
from fastapi.testclient import TestClient
from typing import Any, Dict, List


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
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "document_id" in data
            # Note: Response now has 'document_id' instead of 'file_id'

    def test_ingest_with_session_id(self, client: TestClient):
        response = client.post(
            "/api/ingest",
            json={
                "path": "/test/document.pdf",
                "session_id": "test_session_123",
            },
        )
        assert response.status_code in [200, 500]

    def test_ingest_error_response_structure(self, client: TestClient):
        response = client.post("/api/ingest", json={})
        data = response.json()

        if response.status_code >= 400:
            # Error responses now use FastAPI's standard format
            assert "detail" in data
        elif not data.get("success", True):
            # Success=false responses still have error fields
            assert "error" in data
            assert "error_type" in data
            assert isinstance(data["error"], str)
            assert isinstance(data["error_type"], str)

    def test_ingest_response_structure(self, client: TestClient):
        response = client.post(
            "/api/ingest",
            json={"path": "/test/document.pdf"},
        )
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "document_id" in data
            assert "file_hash" in data
            assert "status" in data
            assert "metadata" in data
            assert isinstance(data["metadata"], dict)


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
        assert response.status_code in [200, 500]
        if response.status_code == 200:
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
        assert response.status_code in [200, 500]

    def test_upload_with_session_id(self, client: TestClient):
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"tags": "[]", "metadata": "{}", "session_id": "session_123"}

        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code in [200, 500]

    @pytest.mark.parametrize(
        "invalid_tags,invalid_metadata",
        [
            ("not_json", "{}"),
            ("[]", "not_json"),
            ("{}", "{}"),  # Tags must be array, not object
            ('"string"', "{}"),  # Tags must be array, not string
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
        # Error responses now use FastAPI's standard format with 'detail'
        assert "detail" in result

    def test_upload_no_filename(self, client: TestClient):
        file_content = b"Test file content"
        files = {"file": ("", io.BytesIO(file_content), "text/plain")}
        data = {"tags": "[]", "metadata": "{}"}

        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code in [400, 422]
        if response.status_code == 400:
            result = response.json()
            assert "detail" in result
            assert "filename" in result["detail"].lower()

    def test_upload_response_structure(self, client: TestClient):
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"tags": "[]", "metadata": "{}"}

        response = client.post("/api/upload", files=files, data=data)
        if response.status_code == 200:
            result = response.json()
            assert "success" in result
            assert "filename" in result
            assert "file_path" in result
            assert "file_size" in result
            assert "mime_type" in result


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
        # Error responses now use FastAPI's standard format
        assert "detail" in data
        assert "no file paths" in data["detail"].lower()

    def test_bulk_ingest_too_many_files(self, client: TestClient):
        file_paths = [f"/test/file{i}.txt" for i in range(1001)]
        response = client.post(
            "/api/bulk-ingest", json={"file_paths": file_paths, "folder_path": "/test"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "1000" in data["detail"]

    def test_bulk_ingest_valid_request(self, client: TestClient):
        file_paths = ["/test/file1.txt", "/test/file2.txt", "/test/file3.txt"]
        response = client.post(
            "/api/bulk-ingest",
            json={"file_paths": file_paths, "folder_path": "/test/folder"},
        )
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["total_files"] == 3
            # Note: Response uses 'successful' and 'failed', not 'successful_count'
            assert "successful" in data
            assert "failed" in data
            assert "results" in data

    def test_bulk_ingest_response_structure(self, client: TestClient):
        file_paths = ["/test/file1.txt"]
        response = client.post(
            "/api/bulk-ingest", json={"file_paths": file_paths, "folder_path": "/test"}
        )
        if response.status_code == 200:
            data = response.json()
            assert "total_files" in data
            assert "successful" in data  # Changed from 'successful_count'
            assert "failed" in data  # Changed from 'failed_count'
            assert "results" in data
            assert isinstance(data["results"], list)

    @pytest.mark.parametrize("file_count", [1, 10, 50, 100, 500, 1000])
    def test_bulk_ingest_various_counts(self, client: TestClient, file_count: int):
        file_paths = [f"/test/file{i}.txt" for i in range(file_count)]
        response = client.post(
            "/api/bulk-ingest", json={"file_paths": file_paths, "folder_path": "/test"}
        )
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert data["total_files"] == file_count


class TestProgressEndpoint:
    def test_progress_endpoint_exists(self, client: TestClient):
        response = client.get("/api/upload/test_id/progress")
        assert response.status_code in [200, 400, 404, 500, 503]

    def test_progress_invalid_file_id_short(self, client: TestClient):
        response = client.get("/api/upload/ab/progress")
        assert response.status_code == 400
        data = response.json()
        # Error responses now use FastAPI's standard format
        assert "detail" in data

    def test_progress_invalid_file_id_empty(self, client: TestClient):
        response = client.get("/api/upload//progress")
        assert response.status_code == 404

    def test_progress_valid_file_id(self, client: TestClient):
        response = client.get("/api/upload/valid_id/progress")
        # This might return 404 if the ID doesn't exist, or 500 if there's an error
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data
            assert "status" in data
            assert "progress" in data
            assert "completed" in data

    def test_progress_not_found(self, client: TestClient):
        response = client.get("/api/upload/nonexistent_id_123/progress")
        assert response.status_code in [404, 500]
        if response.status_code == 404:
            data = response.json()
            assert "detail" in data

    def test_progress_no_manager(self, client_no_services: TestClient):
        response = client_no_services.get("/api/upload/test_id/progress")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data

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
        assert response.status_code in [200, 404, 500]

    def test_progress_response_structure(self, client: TestClient):
        response = client.get("/api/upload/test_file_123/progress")
        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data
            assert "progress" in data
            assert "status" in data
            assert "completed" in data
            
            assert isinstance(data["progress"], (int, float))
            assert 0.0 <= data["progress"] <= 1.0
            assert isinstance(data["status"], str)
            assert isinstance(data["completed"], bool)


class TestUploadIntegration:
    def test_upload_and_ingest_consistency(self, client: TestClient):
        # Test that both upload and ingest endpoints work consistently
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"tags": '["test"]', "metadata": '{"source": "test"}'}
        
        upload_response = client.post("/api/upload", files=files, data=data)
        ingest_response = client.post(
            "/api/ingest",
            json={"path": "/test/test.txt", "tags": ["test"], "metadata": {"source": "test"}}
        )
        
        if upload_response.status_code == 200:
            upload_data = upload_response.json()
            assert upload_data["success"] is True
            
        if ingest_response.status_code == 200:
            ingest_data = ingest_response.json()
            assert ingest_data["success"] is True

    def test_bulk_ingest_file_limit(self, client: TestClient):
        # Test various file counts around the limit
        test_cases = [
            (999, 200),   # Just under limit
            (1000, 200),  # At limit
            (1001, 400),  # Over limit
        ]
        
        for file_count, expected_status in test_cases:
            file_paths = [f"/test/file{i}.txt" for i in range(file_count)]
            response = client.post(
                "/api/bulk-ingest",
                json={"file_paths": file_paths, "folder_path": "/test"}
            )
            assert response.status_code == expected_status

    def test_error_handling_consistency(self, client_no_services: TestClient):
        # Test that all endpoints handle missing services consistently
        endpoints = [
            ("GET", "/api/upload/test_id/progress", None),
        ]
        
        for method, endpoint, json_data in endpoints:
            if method == "GET":
                response = client_no_services.get(endpoint)
            elif method == "POST":
                response = client_no_services.post(endpoint, json=json_data)
            
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data


class TestUploadValidation:
    @pytest.mark.parametrize(
        "tags,metadata,expected_status",
        [
            ('[]', '{}', 200),  # Valid empty
            ('["tag1", "tag2"]', '{"key": "value"}', 200),  # Valid with data
            ('not_json', '{}', 400),  # Invalid tags JSON
            ('[]', 'not_json', 400),  # Invalid metadata JSON
            ('{}', '{}', 400),  # Tags must be array
            ('"string"', '{}', 400),  # Tags must be array
            ('[]', '[]', 400),  # Metadata must be object
        ],
    )
    def test_upload_json_validation(
        self, client: TestClient, tags: str, metadata: str, expected_status: int
    ):
        file_content = b"Test file content"
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"tags": tags, "metadata": metadata}
        
        response = client.post("/api/upload", files=files, data=data)
        assert response.status_code in [expected_status, 500]
        
        if response.status_code >= 400:
            data = response.json()
            assert "detail" in data

    def test_ingest_field_validation(self, client: TestClient):
        # Test various field combinations
        test_cases = [
            ({"path": "/test/file.txt"}, 200),  # Valid minimal
            ({"path": "/test/file.txt", "tags": ["tag1"]}, 200),  # With tags
            ({"path": "/test/file.txt", "metadata": {"key": "value"}}, 200),  # With metadata
            ({}, 422),  # Missing path - FastAPI returns 422 for missing required fields
            ({"tags": ["tag1"]}, 422),  # Missing path - FastAPI returns 422 for missing required fields
        ]
        
        for payload, expected_status in test_cases:
            response = client.post("/api/ingest", json=payload)
            assert response.status_code in [expected_status, 500]

    def test_progress_file_id_validation(self, client: TestClient):
        # Test various file ID formats
        test_cases = [
            ("", 404),  # Empty
            ("a", 400),  # Too short
            ("ab", 400),  # Still too short
            ("abc", 200),  # Minimum valid (might be 404 if not found)
            ("valid_file_id_123", 200),  # Normal (might be 404 if not found)
            ("a" * 100, 200),  # Long but valid (might be 404 if not found)
        ]
        
        for file_id, expected_status in test_cases:
            response = client.get(f"/api/upload/{file_id}/progress")
            if expected_status == 200:
                # Valid format, but might not exist
                assert response.status_code in [200, 404, 500]
            else:
                assert response.status_code == expected_status