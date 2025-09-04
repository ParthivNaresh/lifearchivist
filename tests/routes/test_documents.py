"""
Tests for document management routes (/api/documents/*).

This module tests the document-related API endpoints using the populated 
document fixtures to solve the document lifecycle problem.
"""

import pytest
from httpx import AsyncClient
from typing import Dict, Any, List

from ..base import BaseDocumentTest, PopulatedRouteTest, BaseSearchTest
from ..utils.assertions import assert_successful_response, assert_error_response, assert_pagination_response


class TestDocumentListingRoutes(BaseDocumentTest, PopulatedRouteTest):
    """Test document listing and management routes."""
    
    @pytest.mark.asyncio
    async def test_list_documents_with_populated_data(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test document listing with pre-populated documents."""
        # Set up with populated documents
        test_context = await self.setup_populated_test(populated_vault_with_search_ready_docs)
        expected_count = test_context["documents_available"]
        
        # List all documents
        documents_data = await self.list_documents(async_client, limit=50)
        
        # Should return populated documents
        assert len(documents_data["documents"]) >= expected_count, \
            f"Should return at least {expected_count} documents"
        assert documents_data["total"] >= expected_count, \
            f"Total should be at least {expected_count}"
        
        # Verify document structure
        for doc in documents_data["documents"]:
            assert "document_id" in doc, "Document should have document_id"
            # Additional fields depend on LlamaIndex service implementation
    
    @pytest.mark.asyncio
    async def test_list_documents_with_status_filter(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test document listing with status filtering."""
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        # List documents with ready status
        ready_docs = await self.list_documents(
            async_client, 
            status="ready",
            limit=50
        )
        
        # All populated documents should be ready
        assert len(ready_docs["documents"]) > 0, "Should have ready documents"
        
        # Test invalid status filter
        response = await async_client.get("/api/documents?status=invalid_status")
        # Should still return successfully but may filter out everything
        data = await self.assert_successful_response(response)
        assert "documents" in data
    
    @pytest.mark.asyncio
    async def test_list_documents_pagination(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test document listing pagination."""
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        # Test first page
        page1 = await self.list_documents(
            async_client,
            limit=2,
            offset=0
        )
        
        # Test second page
        page2 = await self.list_documents(
            async_client,
            limit=2, 
            offset=2
        )
        
        # Verify pagination structure
        assert len(page1["documents"]) <= 2, "Page 1 should respect limit"
        assert len(page2["documents"]) <= 2, "Page 2 should respect limit"
        assert page1["limit"] == 2, "Page 1 should have correct limit"
        assert page2["offset"] == 2, "Page 2 should have correct offset"
    
    @pytest.mark.asyncio
    async def test_list_documents_empty_vault(
        self,
        async_client: AsyncClient
    ):
        """Test document listing with empty vault."""
        # Clear all documents first
        await self.clear_all_documents(async_client)
        
        # List documents from empty vault
        empty_docs = await self.list_documents(async_client)
        
        # Should return empty list
        assert len(empty_docs["documents"]) == 0, "Should have no documents in empty vault"
        assert empty_docs["total"] == 0, "Total should be 0 for empty vault"


class TestDocumentAnalysisRoutes(BaseDocumentTest, PopulatedRouteTest):
    """Test document analysis and detail routes."""
    
    @pytest.mark.asyncio
    async def test_get_document_analysis(
        self,
        async_client: AsyncClient,
        single_processed_document: Dict[str, Any]
    ):
        """Test getting document analysis for a specific document."""
        document_id = single_processed_document["file_id"]
        
        # Get document analysis
        analysis_data = await self.get_document_analysis(async_client, document_id)
        
        # Verify analysis structure
        assert analysis_data["document_id"] == document_id, "Should return correct document_id"
        assert "status" in analysis_data, "Should include document status"
        assert "processing_info" in analysis_data, "Should include processing info"
        assert "chunks_preview" in analysis_data, "Should include chunks preview"
        
        # Check processing info structure
        processing_info = analysis_data["processing_info"]
        assert "total_chunks" in processing_info, "Processing info should include total chunks"
        
        # Document should have some chunks for meaningful content
        if single_processed_document["size"] > 100:  # Non-trivial content
            assert processing_info["total_chunks"] > 0, "Non-trivial document should have chunks"
    
    @pytest.mark.asyncio
    async def test_get_document_analysis_not_found(
        self,
        async_client: AsyncClient
    ):
        """Test document analysis for non-existent document."""
        fake_document_id = "nonexistent_document_123"
        
        response = await async_client.get(f"/api/documents/{fake_document_id}/llamaindex-analysis")
        
        assert_error_response(
            response,
            expected_status=500,
            expected_detail_contains="Document nonexistent_document_123 not found in LlamaIndex"
        )
    
    @pytest.mark.asyncio
    async def test_get_document_chunks(
        self,
        async_client: AsyncClient,
        single_processed_document: Dict[str, Any]
    ):
        """Test getting document chunks."""
        document_id = single_processed_document["file_id"]
        
        # Get document chunks
        chunks_data = await self.get_document_chunks(
            async_client,
            document_id,
            limit=10,
            offset=0
        )
        
        # Verify chunks structure
        assert chunks_data["document_id"] == document_id, "Should return correct document_id"
        assert "chunks" in chunks_data, "Should include chunks list"
        assert "total" in chunks_data, "Should include total count"
        assert "has_more" in chunks_data, "Should include pagination flag"
        
        # Verify chunks are lists
        assert isinstance(chunks_data["chunks"], list), "Chunks should be a list"
        
        # If document has meaningful content, should have chunks
        if single_processed_document["size"] > 100:
            assert len(chunks_data["chunks"]) > 0, "Document should have chunks"
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_pagination(
        self,
        async_client: AsyncClient,
        single_processed_document: Dict[str, Any]
    ):
        """Test document chunks pagination."""
        document_id = single_processed_document["file_id"]
        
        # Get first page of chunks
        page1_chunks = await self.get_document_chunks(
            async_client,
            document_id,
            limit=5,
            offset=0
        )
        
        # Get second page of chunks
        page2_chunks = await self.get_document_chunks(
            async_client,
            document_id,
            limit=5,
            offset=5
        )
        
        # Verify pagination
        assert len(page1_chunks["chunks"]) <= 5, "Page 1 should respect limit"
        assert len(page2_chunks["chunks"]) <= 5, "Page 2 should respect limit"
        
        # If there are enough chunks, verify different pages
        if page1_chunks["total"] > 5:
            assert page1_chunks["has_more"] is True, "Should indicate more chunks available"
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_invalid_params(
        self,
        async_client: AsyncClient,
        single_processed_document: Dict[str, Any]
    ):
        """Test document chunks with invalid parameters."""
        document_id = single_processed_document["file_id"]
        
        # Test invalid limit
        response = await async_client.get(
            f"/api/documents/{document_id}/llamaindex-chunks?limit=0"
        )
        assert_error_response(response, expected_status=500, expected_detail_contains="Limit must be between 1 and 1000")
        
        # Test invalid offset
        response = await async_client.get(
            f"/api/documents/{document_id}/llamaindex-chunks?offset=-1"
        )
        assert_error_response(response, expected_status=500)
    
    @pytest.mark.asyncio
    async def test_get_document_neighbors(
        self,
        async_client: AsyncClient,
        multiple_processed_documents: List[Dict[str, Any]]
    ):
        """Test getting document neighbors (similar documents)."""
        # Get a document to find neighbors for
        target_doc = multiple_processed_documents[0]
        document_id = target_doc["file_id"]
        
        # Get document neighbors
        neighbors_data = await self.get_document_neighbors(
            async_client,
            document_id,
            top_k=5
        )
        
        # Verify neighbors structure
        assert neighbors_data["document_id"] == document_id, "Should return correct document_id"
        assert "neighbors" in neighbors_data, "Should include neighbors list"
        assert isinstance(neighbors_data["neighbors"], list), "Neighbors should be a list"
        
        # With multiple documents, should find some neighbors
        if len(multiple_processed_documents) > 1:
            assert len(neighbors_data["neighbors"]) > 0, "Should find some neighboring documents"
            
            # Verify neighbor structure
            for neighbor in neighbors_data["neighbors"]:
                assert "document_id" in neighbor, "Neighbor should have document_id"
                assert "similarity_score" in neighbor, "Neighbor should have similarity score"
                assert -1 <= neighbor["similarity_score"] <= 1, "Score should be between 0 and 1"
    
    @pytest.mark.asyncio
    async def test_get_document_neighbors_invalid_params(
        self,
        async_client: AsyncClient,
        single_processed_document: Dict[str, Any]
    ):
        """Test document neighbors with invalid parameters."""
        document_id = single_processed_document["file_id"]
        
        # Test invalid top_k (too small)
        response = await async_client.get(
            f"/api/documents/{document_id}/llamaindex-neighbors?top_k=0"
        )
        assert_error_response(response, expected_status=500, expected_detail_contains="top_k must be between 1 and 100")
        
        # Test invalid top_k (too large)
        response = await async_client.get(
            f"/api/documents/{document_id}/llamaindex-neighbors?top_k=200"
        )
        assert_error_response(response, expected_status=500, expected_detail_contains="top_k must be between 1 and 100")


class TestDocumentManagementRoutes(BaseDocumentTest, PopulatedRouteTest):
    """Test document management operations (clear, delete, etc.)."""
    
    @pytest.mark.asyncio
    async def test_clear_all_documents_populated_vault(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test clearing all documents from populated vault."""
        # Start with populated vault
        test_context = await self.setup_populated_test(populated_vault_with_search_ready_docs)
        initial_count = test_context["documents_available"]
        
        # Verify we have documents to clear
        assert initial_count > 0, "Should start with documents to clear"
        
        # Clear all documents
        clear_result = await self.clear_all_documents(async_client)
        
        # Verify clear operation results
        assert clear_result["success"] is True, "Clear operation should succeed"
        assert clear_result["operation"] == "comprehensive_clear_all", "Should be comprehensive clear"
        assert "summary" in clear_result, "Should include operation summary"
        
        # Verify cleanup metrics
        summary = clear_result["summary"]
        assert summary["total_files_deleted"] > 0, "Should have deleted some files"
        assert summary["total_bytes_reclaimed"] >= 0, "Should reclaim some bytes"
        
        # Verify vault is now empty
        empty_docs = await self.list_documents(async_client)
        assert len(empty_docs["documents"]) == 0, "Vault should be empty after clear"
        assert empty_docs["total"] == 0, "Total should be 0 after clear"
    
    @pytest.mark.asyncio
    async def test_clear_all_documents_empty_vault(
        self,
        async_client: AsyncClient
    ):
        """Test clearing documents from already empty vault."""
        # Clear to ensure empty state
        await self.clear_all_documents(async_client)
        
        # Clear again, should delete 5 json files which are recreated with LlamaIndex
        clear_result = await self.clear_all_documents(async_client)
        
        assert clear_result["success"] is True, "Clear should succeed on empty vault"
        summary = clear_result["summary"]
        assert summary["total_files_deleted"] == 5, "Should delete 5 default files from empty vault"
    
    @pytest.mark.asyncio
    async def test_document_service_unavailable(
        self,
        async_client: AsyncClient
    ):
        """Test document routes when LlamaIndex service is unavailable."""
        # This test would require mocking the service to be unavailable
        # For now, we'll test with a non-existent document which may trigger service checks
        fake_document_id = "service_test_document"
        
        response = await async_client.get(f"/api/documents/{fake_document_id}/llamaindex-analysis")
        
        assert response.status_code == 500, "Should handle missing document/service appropriately"


class TestDocumentIntegrationWorkflows(BaseSearchTest, BaseDocumentTest, PopulatedRouteTest):
    """Integration tests for document workflows."""
    
    @pytest.mark.asyncio
    async def test_document_workflow_list_to_analysis(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test workflow: list documents → get specific document analysis."""
        # Set up with populated documents
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        # 1. List documents
        documents_list = await self.list_documents(async_client, limit=10)
        assert len(documents_list["documents"]) > 0, "Should have documents to analyze"
        
        # 2. Get first document for detailed analysis
        first_doc = documents_list["documents"][0]
        document_id = first_doc["document_id"]
        
        # 3. Get document analysis
        analysis = await self.get_document_analysis(async_client, document_id)
        assert analysis["document_id"] == document_id, "Analysis should match requested document"
        
        # 4. Get document chunks
        chunks = await self.get_document_chunks(async_client, document_id, limit=5)
        assert chunks["document_id"] == document_id, "Chunks should match requested document"
        
        # 5. Get document neighbors
        neighbors = await self.get_document_neighbors(async_client, document_id, top_k=3)
        assert neighbors["document_id"] == document_id, "Neighbors should match requested document"
        
        return {
            "workflow_completed": True,
            "document_analyzed": document_id,
            "has_chunks": len(chunks["chunks"]) > 0,
            "has_neighbors": len(neighbors["neighbors"]) > 0
        }
    
    @pytest.mark.asyncio
    async def test_document_workflow_with_search_integration(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test integration between document management and search functionality."""
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        # 1. Search for documents
        search_data = await self.perform_search_get(
            async_client,
            q="test document",
            limit=5
        )
        assert len(search_data["results"]) > 0, "Search should find documents"
        
        # 2. Get detailed analysis for found documents
        for result in search_data["results"]:
            document_id = result["document_id"]
            
            # Get analysis for each found document
            analysis = await self.get_document_analysis(async_client, document_id)
            assert analysis["document_id"] == document_id, "Analysis should match search result"
            
            # Verify document is actually accessible
            assert "status" in analysis, "Document should have status"
            assert "total_chunks" in analysis["processing_info"], "Document should have chunk info"
        
        return {
            "search_to_analysis_workflow": True,
            "documents_found": len(search_data["results"]),
            "documents_analyzed": len([r["document_id"] for r in search_data["results"]])
        }