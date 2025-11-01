import pytest
from fastapi.testclient import TestClient


class TestListDocumentsEndpoint:
    def test_list_documents_endpoint_exists(self, client: TestClient):
        response = client.get("/api/documents")
        assert response.status_code in [200, 503]

    def test_list_documents_success(self, client: TestClient):
        response = client.get("/api/documents")
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "documents" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["documents"], list)

    @pytest.mark.parametrize(
        "limit,expected_limit",
        [
            (10, 10),
            (50, 50),
            (100, 100),
            (500, 500),
            (501, 500),
            (1000, 500),
            (0, 50),
            (-1, 50),
        ],
    )
    def test_list_documents_limit_validation(
        self, client: TestClient, limit: int, expected_limit: int
    ):
        response = client.get(f"/api/documents?limit={limit}")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == expected_limit

    @pytest.mark.parametrize(
        "offset,expected_offset",
        [
            (0, 0),
            (10, 10),
            (100, 100),
            (-1, 0),
            (-10, 0),
        ],
    )
    def test_list_documents_offset_validation(
        self, client: TestClient, offset: int, expected_offset: int
    ):
        response = client.get(f"/api/documents?offset={offset}")
        assert response.status_code == 200
        data = response.json()
        assert data["offset"] == expected_offset

    def test_list_documents_with_status_filter(self, client: TestClient):
        response = client.get("/api/documents?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data

    def test_list_documents_count_only(self, client: TestClient):
        response = client.get("/api/documents?count_only=true")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "filters" in data
        assert isinstance(data["total"], int)

    def test_list_documents_no_service(self, client_no_services: TestClient):
        response = client_no_services.get("/api/documents")
        assert response.status_code == 503


class TestDeleteDocumentEndpoint:
    def test_delete_document_endpoint_exists(self, client: TestClient):
        response = client.delete("/api/documents/test_doc_id")
        assert response.status_code in [200, 404, 503]

    def test_delete_document_not_found(self, client: TestClient):
        response = client.delete("/api/documents/nonexistent_doc_123")
        assert response.status_code == 404

    def test_delete_document_no_service(self, client_no_services: TestClient):
        response = client_no_services.delete("/api/documents/test_doc_id")
        assert response.status_code == 503

    @pytest.mark.parametrize(
        "document_id",
        [
            "doc123",
            "document-with-dashes",
            "document_with_underscores",
            "DocumentWithCaps",
            "123456789",
        ],
    )
    def test_delete_document_various_id_formats(
        self, client: TestClient, document_id: str
    ):
        response = client.delete(f"/api/documents/{document_id}")
        assert response.status_code in [200, 404, 503]


class TestUpdateDocumentSubthemeEndpoint:
    def test_update_subtheme_endpoint_exists(self, client: TestClient):
        response = client.patch(
            "/api/documents/test_doc_id/subtheme", json={"theme": "test"}
        )
        assert response.status_code in [200, 404, 503]

    def test_update_subtheme_with_valid_data(self, client: TestClient):
        response = client.patch(
            "/api/documents/test_doc_id/subtheme",
            json={
                "theme": "work",
                "subtheme": "meetings",
                "confidence": 0.95,
            },
        )
        assert response.status_code in [200, 404, 503]

    def test_update_subtheme_empty_data(self, client: TestClient):
        response = client.patch("/api/documents/test_doc_id/subtheme", json={})
        assert response.status_code in [200, 404, 503]

    def test_update_subtheme_no_service(self, client_no_services: TestClient):
        response = client_no_services.patch(
            "/api/documents/test_doc_id/subtheme", json={"theme": "test"}
        )
        assert response.status_code == 503


class TestClearAllDocumentsEndpoint:
    def test_clear_all_endpoint_exists(self, client: TestClient):
        response = client.delete("/api/documents")
        assert response.status_code in [200, 500, 503]

    def test_clear_all_response_structure(self, client: TestClient):
        response = client.delete("/api/documents")
        if response.status_code == 200:
            data = response.json()
            assert "success" in data
            assert "operation" in data
            assert "summary" in data
            assert "vault_metrics" in data
            assert "llamaindex_metrics" in data
            assert "progress_metrics" in data
            assert "errors" in data

            summary = data["summary"]
            assert "total_files_deleted" in summary
            assert "total_bytes_reclaimed" in summary
            assert "total_mb_reclaimed" in summary


class TestDocumentAnalysisEndpoint:
    def test_analysis_endpoint_exists(self, client: TestClient):
        response = client.get("/api/documents/test_doc_id/llamaindex-analysis")
        assert response.status_code in [200, 404, 503]

    def test_analysis_no_service(self, client_no_services: TestClient):
        response = client_no_services.get(
            "/api/documents/test_doc_id/llamaindex-analysis"
        )
        assert response.status_code == 503

    @pytest.mark.parametrize(
        "document_id",
        [
            "doc123",
            "document-with-dashes",
            "document_with_underscores",
        ],
    )
    def test_analysis_various_id_formats(self, client: TestClient, document_id: str):
        response = client.get(f"/api/documents/{document_id}/llamaindex-analysis")
        assert response.status_code in [200, 404, 503]


class TestDocumentChunksEndpoint:
    def test_chunks_endpoint_exists(self, client: TestClient):
        response = client.get("/api/documents/test_doc_id/llamaindex-chunks")
        assert response.status_code in [200, 404, 503]

    @pytest.mark.parametrize(
        "limit,expected_status",
        [
            (1, 200),
            (50, 200),
            (100, 200),
            (1000, 200),
            (0, 400),
            (1001, 400),
            (-1, 400),
        ],
    )
    def test_chunks_limit_validation(
        self, client: TestClient, limit: int, expected_status: int
    ):
        response = client.get(
            f"/api/documents/test_doc_id/llamaindex-chunks?limit={limit}"
        )
        assert response.status_code in [expected_status, 404, 503]

    @pytest.mark.parametrize(
        "offset,expected_status",
        [
            (0, 200),
            (10, 200),
            (100, 200),
            (-1, 400),
        ],
    )
    def test_chunks_offset_validation(
        self, client: TestClient, offset: int, expected_status: int
    ):
        response = client.get(
            f"/api/documents/test_doc_id/llamaindex-chunks?offset={offset}"
        )
        assert response.status_code in [expected_status, 404, 503]

    def test_chunks_with_pagination(self, client: TestClient):
        response = client.get(
            "/api/documents/test_doc_id/llamaindex-chunks?limit=10&offset=5"
        )
        assert response.status_code in [200, 404, 503]

    def test_chunks_no_service(self, client_no_services: TestClient):
        response = client_no_services.get(
            "/api/documents/test_doc_id/llamaindex-chunks"
        )
        assert response.status_code == 503


class TestDocumentNeighborsEndpoint:
    def test_neighbors_endpoint_exists(self, client: TestClient):
        response = client.get("/api/documents/test_doc_id/llamaindex-neighbors")
        assert response.status_code in [200, 404, 503]

    @pytest.mark.parametrize(
        "top_k,expected_status",
        [
            (1, 200),
            (10, 200),
            (50, 200),
            (100, 200),
            (0, 400),
            (101, 400),
            (-1, 400),
        ],
    )
    def test_neighbors_top_k_validation(
        self, client: TestClient, top_k: int, expected_status: int
    ):
        response = client.get(
            f"/api/documents/test_doc_id/llamaindex-neighbors?top_k={top_k}"
        )
        assert response.status_code in [expected_status, 404, 503]

    def test_neighbors_default_top_k(self, client: TestClient):
        response = client.get("/api/documents/test_doc_id/llamaindex-neighbors")
        assert response.status_code in [200, 404, 503]

    def test_neighbors_no_service(self, client_no_services: TestClient):
        response = client_no_services.get(
            "/api/documents/test_doc_id/llamaindex-neighbors"
        )
        assert response.status_code == 503

    @pytest.mark.parametrize(
        "document_id",
        [
            "doc123",
            "document-with-dashes",
            "document_with_underscores",
        ],
    )
    def test_neighbors_various_id_formats(self, client: TestClient, document_id: str):
        response = client.get(f"/api/documents/{document_id}/llamaindex-neighbors")
        assert response.status_code in [200, 404, 503]
