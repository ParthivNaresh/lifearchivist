"""
Base test classes with common patterns for Life Archivist testing.

This module provides base test classes that encapsulate common testing
patterns and provide reusable functionality for route testing.
"""

import pytest
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from httpx import AsyncClient
from fastapi.testclient import TestClient

from .utils.assertions import (
    assert_successful_response,
    assert_error_response,
    assert_pagination_response,
    assert_search_response,
    assert_upload_response,
    assert_qa_response,
)
from .utils.helpers import (
    extract_file_id,
    extract_document_ids,
    ResponseValidator,
    create_pagination_test_cases,
    create_error_test_cases,
)
from .factories.request_factory import RequestFactory
from .factories.response_factory import ResponseFactory


class BaseRouteTest:
    """
    Base class for route testing with common utilities.
    
    This class provides common functionality that can be used across
    different route test classes to reduce code duplication.
    """
    
    def setup_method(self):
        """Set up method called before each test method."""
        pass
    
    def teardown_method(self):
        """Tear down method called after each test method."""
        pass
    
    async def assert_successful_response(
        self,
        response,
        expected_status: int = 200,
        required_fields: Optional[List[str]] = None,
        forbidden_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Assert successful response with common validations."""
        return assert_successful_response(
            response, expected_status, required_fields, forbidden_fields
        )
    
    async def assert_error_response(
        self,
        response,
        expected_status: int,
        expected_detail_contains: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Assert error response with common validations."""
        return assert_error_response(
            response, expected_status, expected_detail_contains
        )
    
    def create_request_payload(self, request_type: str, **kwargs) -> Dict[str, Any]:
        """Create request payload using factory."""
        factory_method = getattr(RequestFactory, f"create_{request_type}_request")
        return factory_method(**kwargs)
    
    def create_expected_response(self, response_type: str, **kwargs) -> Dict[str, Any]:
        """Create expected response using factory."""
        factory_method = getattr(ResponseFactory, f"create_{response_type}_response")
        return factory_method(**kwargs)


class BaseUploadTest(BaseRouteTest):
    """Base class for upload-related route testing."""
    
    async def perform_upload(
        self,
        client: Union[AsyncClient, TestClient],
        file_content: bytes = b"test content",
        filename: str = "test.txt",
        content_type: str = "text/plain",
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform a file upload and return the response data."""
        import json
        
        # Create the form data in the format FastAPI expects
        files = {"file": (filename, file_content, content_type)}
        data = {
            "tags": json.dumps(tags or []),
            "metadata": json.dumps(metadata or {}),
        }
        if session_id:
            data["session_id"] = session_id
        
        if isinstance(client, AsyncClient):
            response = await client.post("/api/upload", files=files, data=data)
        else:
            response = client.post("/api/upload", files=files, data=data)
        
        return assert_upload_response(response)
    
    async def perform_ingest(
        self,
        client: Union[AsyncClient, TestClient],
        file_path: str = "/tmp/test.txt",
        **kwargs
    ) -> Dict[str, Any]:
        """Perform a file ingest and return the response data."""
        payload = RequestFactory.create_ingest_request(path=file_path, **kwargs)
        
        if isinstance(client, AsyncClient):
            response = await client.post("/api/ingest", json=payload)
        else:
            response = client.post("/api/ingest", json=payload)
        
        return assert_successful_response(
            response, required_fields=["file_id", "status"]
        )
    
    async def perform_bulk_ingest(
        self,
        client: Union[AsyncClient, TestClient],
        file_paths: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Perform bulk ingest and return the response data."""
        payload = RequestFactory.create_bulk_ingest_request(
            file_paths=file_paths, **kwargs
        )
        
        if isinstance(client, AsyncClient):
            response = await client.post("/api/bulk-ingest", json=payload)
        else:
            response = client.post("/api/bulk-ingest", json=payload)
        
        return assert_successful_response(
            response,
            required_fields=["success", "total_files", "successful_count", "results"]
        )


class BaseDocumentTest(BaseRouteTest):
    """Base class for document-related route testing."""
    
    async def list_documents(
        self,
        client: Union[AsyncClient, TestClient],
        **kwargs
    ) -> Dict[str, Any]:
        """List documents and return the response data."""
        params = RequestFactory.create_documents_query_params(**kwargs)
        
        if isinstance(client, AsyncClient):
            response = await client.get("/api/documents", params=params)
        else:
            response = client.get("/api/documents", params=params)
        
        return assert_pagination_response(response, items_field="documents")
    
    async def clear_all_documents(
        self,
        client: Union[AsyncClient, TestClient]
    ) -> Dict[str, Any]:
        """Clear all documents and return the response data."""
        if isinstance(client, AsyncClient):
            response = await client.delete("/api/documents")
        else:
            response = client.delete("/api/documents")
        
        return assert_successful_response(
            response,
            required_fields=["success", "operation", "summary"]
        )
    
    async def get_document_analysis(
        self,
        client: Union[AsyncClient, TestClient],
        document_id: str
    ) -> Dict[str, Any]:
        """Get document analysis and return the response data."""
        if isinstance(client, AsyncClient):
            response = await client.get(f"/api/documents/{document_id}/llamaindex-analysis")
        else:
            response = client.get(f"/api/documents/{document_id}/llamaindex-analysis")
        
        return assert_successful_response(
            response,
            required_fields=["document_id", "status", "processing_info", "chunks_preview"]
        )
    
    async def get_document_chunks(
        self,
        client: Union[AsyncClient, TestClient],
        document_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Get document chunks and return the response data."""
        params = RequestFactory.create_document_chunks_query_params(**kwargs)
        
        if isinstance(client, AsyncClient):
            response = await client.get(f"/api/documents/{document_id}/llamaindex-chunks", params=params)
        else:
            response = client.get(f"/api/documents/{document_id}/llamaindex-chunks", params=params)
        
        return assert_successful_response(
            response,
            required_fields=["document_id", "chunks", "total", "has_more"]
        )
    
    async def get_document_neighbors(
        self,
        client: Union[AsyncClient, TestClient],
        document_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Get document neighbors and return the response data."""
        params = RequestFactory.create_document_neighbors_query_params(**kwargs)
        
        if isinstance(client, AsyncClient):
            response = await client.get(f"/api/documents/{document_id}/llamaindex-neighbors", params=params)
        else:
            response = client.get(f"/api/documents/{document_id}/llamaindex-neighbors", params=params)
        
        return assert_successful_response(
            response,
            required_fields=["document_id", "neighbors"]
        )


class BaseSearchTest(BaseRouteTest):
    """Base class for search-related route testing."""
    
    async def perform_search_post(
        self,
        client: Union[AsyncClient, TestClient],
        **kwargs
    ) -> Dict[str, Any]:
        """Perform POST search and return the response data."""
        payload = RequestFactory.create_search_request(**kwargs)
        
        if isinstance(client, AsyncClient):
            response = await client.post("/api/search", json=payload)
        else:
            response = client.post("/api/search", json=payload)
        
        return assert_search_response(response)
    
    async def perform_search_get(
        self,
        client: Union[AsyncClient, TestClient],
        **kwargs
    ) -> Dict[str, Any]:
        """Perform GET search and return the response data."""
        params = RequestFactory.create_search_query_params(**kwargs)
        
        if isinstance(client, AsyncClient):
            response = await client.get("/api/search", params=params)
        else:
            response = client.get("/api/search", params=params)
        
        return assert_search_response(response)
    
    async def perform_qa_query(
        self,
        client: Union[AsyncClient, TestClient],
        **kwargs
    ) -> Dict[str, Any]:
        """Perform Q&A query and return the response data."""
        payload = RequestFactory.create_ask_request(**kwargs)
        
        if isinstance(client, AsyncClient):
            response = await client.post("/api/ask", json=payload)
        else:
            response = client.post("/api/ask", json=payload)
        
        return assert_qa_response(response)


class BaseVaultTest(BaseRouteTest):
    """Base class for vault-related route testing."""
    
    async def get_vault_info(
        self,
        client: Union[AsyncClient, TestClient]
    ) -> Dict[str, Any]:
        """Get vault info and return the response data."""
        if isinstance(client, AsyncClient):
            response = await client.get("/api/vault/info")
        else:
            response = client.get("/api/vault/info")
        
        return assert_successful_response(
            response,
            required_fields=["vault_path", "total_files", "total_size_bytes"]
        )
    
    async def list_vault_files(
        self,
        client: Union[AsyncClient, TestClient],
        **kwargs
    ) -> Dict[str, Any]:
        """List vault files and return the response data."""
        params = RequestFactory.create_vault_files_query_params(**kwargs)
        
        if isinstance(client, AsyncClient):
            response = await client.get("/api/vault/files", params=params)
        else:
            response = client.get("/api/vault/files", params=params)
        
        return assert_pagination_response(response, items_field="files")


class BaseProgressTest(BaseRouteTest):
    """Base class for progress-related route testing."""
    
    async def get_upload_progress(
        self,
        client: Union[AsyncClient, TestClient],
        file_id: str
    ) -> Dict[str, Any]:
        """Get upload progress and return the response data."""
        if isinstance(client, AsyncClient):
            response = await client.get(f"/api/upload/{file_id}/progress")
        else:
            response = client.get(f"/api/upload/{file_id}/progress")
        
        return assert_successful_response(
            response,
            required_fields=["file_id", "stage", "percentage"]
        )


class ParameterizedRouteTest(BaseRouteTest):
    """Base class for parameterized route testing."""
    
    # Note: These are template methods that subclasses can implement
    # They are not active test methods in this base class
    
    def create_pagination_test_cases(self):
        """Helper method to create pagination test cases."""
        return create_pagination_test_cases()
    
    def create_error_test_cases(self):
        """Helper method to create error test cases."""
        return create_error_test_cases()


class IntegrationRouteTest(BaseUploadTest, BaseSearchTest, BaseDocumentTest):
    """
    Base class for integration route testing.
    
    This class provides patterns for testing workflows that span
    multiple routes (e.g., upload -> search -> query).
    """
    
    async def create_test_document(
        self,
        client: Union[AsyncClient, TestClient],
        content: str = "Test document content",
        filename: str = "test.txt"
    ) -> str:
        """Create a test document and return its file ID."""
        upload_data = await self.perform_upload(
            client,
            file_content=content.encode(),
            filename=filename
        )
        return extract_file_id(upload_data)
    
    async def create_multiple_test_documents(
        self,
        client: Union[AsyncClient, TestClient],
        count: int = 3
    ) -> List[str]:
        """Create multiple test documents and return their file IDs."""
        file_ids = []
        for i in range(count):
            file_id = await self.create_test_document(
                client,
                content=f"Test document {i+1} content for testing search and query functionality.",
                filename=f"test_doc_{i+1}.txt"
            )
            file_ids.append(file_id)
        return file_ids
    
    async def run_complete_workflow(
        self,
        client: Union[AsyncClient, TestClient]
    ) -> Dict[str, Any]:
        """Helper method for complete workflow - to be used by subclasses."""
        # 1. Upload documents
        file_ids = await self.create_multiple_test_documents(client)
        
        # 2. Verify documents are stored
        documents_data = await self.list_documents(client)
        
        # 3. Search for documents
        search_data = await self.perform_search_get(client, q="test document")
        
        # 4. Query about documents
        qa_data = await self.perform_qa_query(client, question="What is in these documents?")
        
        return {
            "uploaded_files": file_ids,
            "stored_documents": documents_data,
            "search_results": search_data,
            "qa_results": qa_data,
        }


class PopulatedRouteTest(BaseRouteTest):
    """
    Enhanced base class for testing routes with pre-populated documents.
    
    This class solves the document lifecycle problem by providing access to
    processed documents that are ready for search, query, and analysis operations.
    
    Use this class when testing routes that require existing content.
    """
    
    async def setup_populated_test(
        self, 
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Set up test with populated vault and documents.
        
        Args:
            populated_vault_with_search_ready_docs: Fixture with ready documents
            
        Returns:
            Test context with document information
        """
        self.vault_info = populated_vault_with_search_ready_docs
        self.available_documents = self.vault_info["documents"]
        self.document_count = self.vault_info["document_count"]
        
        return {
            "documents_available": self.document_count,
            "vault_ready": self.vault_info["ready_for_testing"],
            "searchable": self.vault_info["searchable"]
        }
    
    def get_test_document_by_category(self, category: str) -> Optional[Dict[str, Any]]:
        """Get a document by category for targeted testing."""
        for doc in self.available_documents:
            if doc.get("category") == category:
                return doc
        return None
    
    def get_all_document_ids(self) -> List[str]:
        """Get all available document IDs for testing."""
        return [doc["file_id"] for doc in self.available_documents]
    
    def get_sample_search_content(self) -> str:
        """Get sample content that should return search results."""
        if self.available_documents:
            # Return part of the content from first document
            content = self.available_documents[0]["content"]
            words = content.split()[:5]  # First 5 words
            return " ".join(words)
        return "test document"
    
    async def verify_documents_searchable(
        self, 
        client: Union[AsyncClient, TestClient],
        expected_min_results: int = 1
    ) -> Dict[str, Any]:
        """Verify that populated documents are searchable."""
        search_query = self.get_sample_search_content()
        
        search_data = await self.perform_search_get(
            client,
            q=search_query,
            limit=10
        )
        
        assert len(search_data["results"]) >= expected_min_results, \
            f"Expected at least {expected_min_results} search results"
        
        return search_data
    
    async def verify_documents_queryable(
        self,
        client: Union[AsyncClient, TestClient],
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify that populated documents support Q&A queries."""
        if not question:
            question = "What information is available in these documents?"
            
        qa_data = await self.perform_qa_query(
            client,
            question=question,
            context_limit=5
        )
        
        assert len(qa_data["answer"]) > 0, "Should get non-empty answer"
        assert len(qa_data["citations"]) > 0, "Should get citations from documents"
        
        return qa_data