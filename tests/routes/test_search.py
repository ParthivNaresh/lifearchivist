"""
Tests for search routes (/api/search, /api/ask).

This module demonstrates the testing patterns for search-related routes
using the testing framework and base classes.
"""

import pytest
from httpx import AsyncClient

from .. import BaseSearchTest
from ..base import ParameterizedRouteTest, IntegrationRouteTest
from ..factories.request_factory import RequestFactory
from ..utils.assertions import assert_error_response


class TestSearchRoutes(BaseSearchTest):
    """Test search routes with mocked services."""
    
    @pytest.mark.asyncio
    async def test_search_post_basic(self, async_client: AsyncClient):
        """Test basic POST search functionality."""
        response_data = await self.perform_search_post(
            async_client,
            query="test document",
            mode="keyword",
            limit=10
        )
        
        # Validate search response structure
        assert "results" in response_data
        assert "total" in response_data
        assert "query_time_ms" in response_data
        
        # Query time should be reasonable
        assert response_data["query_time_ms"] >= 0
        assert response_data["query_time_ms"] <= 5000  # Should be under 5 seconds
    
    @pytest.mark.asyncio
    async def test_search_get_basic(self, async_client: AsyncClient):
        """Test basic GET search functionality."""
        response_data = await self.perform_search_get(
            async_client,
            q="test document",
            mode="semantic",
            limit=5
        )
        
        # Validate search response
        assert isinstance(response_data["results"], list)
        assert len(response_data["results"]) <= 5  # Respects limit
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, async_client: AsyncClient):
        """Test search with metadata filters."""
        response_data = await self.perform_search_post(
            async_client,
            query="medical report",
            mode="hybrid",
            filters={
                "mime_type": "application/pdf",
                "status": "processed"
            }
        )
        
        # Search should execute successfully with filters
        assert "results" in response_data
    
    @pytest.mark.asyncio
    async def test_search_with_tags_filter(self, async_client: AsyncClient):
        """Test search with tags filter."""
        response_data = await self.perform_search_get(
            async_client,
            q="financial data",
            tags="financial,report"  # Comma-separated tags
        )
        
        # Should handle tag filtering
        assert "results" in response_data
    
    @pytest.mark.asyncio
    async def test_search_pagination(self, async_client: AsyncClient):
        """Test search pagination parameters."""
        # Test first page
        page1_data = await self.perform_search_get(
            async_client,
            q="test",
            limit=2,
            offset=0
        )
        
        # Test second page
        page2_data = await self.perform_search_get(
            async_client,
            q="test",
            limit=2,
            offset=2
        )
        
        # Both pages should return valid results
        assert len(page1_data["results"]) <= 2
        assert len(page2_data["results"]) <= 2
    
    @pytest.mark.asyncio
    async def test_search_include_content(self, async_client: AsyncClient):
        """Test search with content inclusion."""
        response_data = await self.perform_search_get(
            async_client,
            q="test document",
            include_content=True
        )
        
        # Should include content in results
        assert "results" in response_data
    
    @pytest.mark.asyncio
    async def test_search_with_direct_request_factory(self, async_client: AsyncClient):
        """Test search using RequestFactory directly (demonstrates factory usage)."""
        # Create search request payload using factory
        search_payload = RequestFactory.create_search_request(
            query="factory generated query",
            mode="hybrid",
            limit=15,
            filters={"mime_type": "application/pdf"}
        )
        
        # Send request with factory-generated payload
        response = await async_client.post("/api/search", json=search_payload)
        
        # Validate response
        data = await self.assert_successful_response(response)
        assert "results" in data
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self, async_client: AsyncClient):
        """Test search with empty query should return error."""
        response = await async_client.get("/api/search?q=&mode=keyword")
        
        # Empty query should return successful response with error field
        data = await self.assert_successful_response(response)
        assert "error" in data
        assert "query" in data["error"].lower()
    
    @pytest.mark.asyncio
    async def test_search_invalid_mode(self, async_client: AsyncClient):
        """Test search with invalid mode should return error."""
        response = await async_client.get("/api/search?q=test&mode=invalid_mode")
        
        # Invalid mode should return error
        assert_error_response(
            response,
            expected_status=400,
            expected_detail_contains="Invalid mode"
        )


class TestQARoutes(BaseSearchTest):
    """Test Q&A routes."""
    
    @pytest.mark.asyncio
    async def test_ask_basic_question(self, async_client: AsyncClient):
        """Test basic Q&A functionality."""
        response_data = await self.perform_qa_query(
            async_client,
            question="What is the main topic of the documents?",
            context_limit=5
        )
        
        # Validate Q&A response structure
        assert "answer" in response_data
        assert "confidence" in response_data
        assert "citations" in response_data
        assert "method" in response_data
        
        # Validate response values
        assert isinstance(response_data["answer"], str)
        assert len(response_data["answer"]) > 0
        assert 0 <= response_data["confidence"] <= 1
        assert isinstance(response_data["citations"], list)
    
    @pytest.mark.asyncio
    async def test_ask_with_context_limit(self, async_client: AsyncClient):
        """Test Q&A with different context limits."""
        # Test with small context limit
        small_context_data = await self.perform_qa_query(
            async_client,
            question="Summarize the key findings?",
            context_limit=3
        )
        
        # Test with larger context limit
        large_context_data = await self.perform_qa_query(
            async_client,
            question="Summarize the key findings?",
            context_limit=10
        )
        
        # Both should return valid responses
        assert "answer" in small_context_data
        assert "answer" in large_context_data
    
    @pytest.mark.asyncio
    async def test_ask_domain_specific_question(self, async_client: AsyncClient):
        """Test Q&A with domain-specific questions."""
        medical_data = await self.perform_qa_query(
            async_client,
            question="What are the patient's blood pressure readings?",
            context_limit=5
        )
        
        financial_data = await self.perform_qa_query(
            async_client,
            question="What were the quarterly earnings results?",
            context_limit=5
        )
        
        # Both domain questions should get responses
        assert "answer" in medical_data
        assert "answer" in financial_data
    
    @pytest.mark.asyncio
    async def test_ask_empty_question(self, async_client: AsyncClient):
        """Test Q&A with empty question should return error."""
        response = await async_client.post(
            "/api/ask",
            json={"question": "", "context_limit": 5}
        )
        
        # Empty question should return error
        assert_error_response(
            response,
            expected_status=400,
            expected_detail_contains="Question is required"
        )
    
    @pytest.mark.asyncio
    async def test_ask_short_question(self, async_client: AsyncClient):
        """Test Q&A with very short question should return error."""
        response = await async_client.post(
            "/api/ask",
            json={"question": "Hi", "context_limit": 5}
        )
        
        # Short question should return error
        assert_error_response(
            response,
            expected_status=400,
            expected_detail_contains="at least 3 characters"
        )
    
    @pytest.mark.asyncio
    async def test_ask_invalid_context_limit(self, async_client: AsyncClient):
        """Test Q&A with invalid context limit should return error."""
        # Use RequestFactory to create invalid requests
        invalid_request = RequestFactory.create_ask_request(
            question="Test question?", 
            context_limit=-1
        )
        
        response = await async_client.post("/api/ask", json=invalid_request)
        
        assert_error_response(
            response,
            expected_status=400,
            expected_detail_contains="context_limit must be between 1 and 20"
        )
        
        # Test excessive context limit using factory
        excessive_request = RequestFactory.create_ask_request(
            question="Test question?", 
            context_limit=50
        )
        
        response = await async_client.post("/api/ask", json=excessive_request)
        
        assert_error_response(
            response,
            expected_status=400,
            expected_detail_contains="context_limit must be between 1 and 20"
        )


class TestSearchParameterized(ParameterizedRouteTest):
    """Parameterized tests for search routes."""
    
    @pytest.mark.parametrize("mode", ["keyword", "semantic", "hybrid"])
    @pytest.mark.asyncio
    async def test_search_all_modes(self, async_client: AsyncClient, mode: str):
        """Test all search modes."""
        response = await async_client.get(
            f"/api/search?q=test+document&mode={mode}&limit=5"
        )
        
        data = await self.assert_successful_response(response)
        assert "results" in data
    
    @pytest.mark.parametrize("limit", [1, 5, 20, 100])
    @pytest.mark.asyncio
    async def test_search_various_limits(self, async_client: AsyncClient, limit: int):
        """Test search with various limit values."""
        response = await async_client.get(
            f"/api/search?q=test&mode=keyword&limit={limit}"
        )
        
        data = await self.assert_successful_response(response)
        assert len(data["results"]) <= limit
    
    @pytest.mark.parametrize("context_limit", [1, 5, 10, 20])
    @pytest.mark.asyncio
    async def test_qa_various_context_limits(self, async_client: AsyncClient, context_limit: int):
        """Test Q&A with various context limits."""
        response = await async_client.post(
            "/api/ask",
            json={
                "question": "What information is available?",
                "context_limit": context_limit
            }
        )
        
        data = await self.assert_successful_response(response)
        assert "answer" in data
        assert "citations" in data


class TestSearchIntegration(IntegrationRouteTest):
    """Integration tests for search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_after_upload(self, async_client: AsyncClient):
        """Test that uploaded documents can be searched."""
        # Upload a test document
        file_id = await self.create_test_document(
            async_client,
            content="This document contains information about mortgage rates and home loans.",
            filename="mortgage_info.txt"
        )
        
        # Search for the uploaded content
        search_data = await self.perform_search_get(
            async_client,
            q="mortgage rates"
        )
        
        # Should find results (even with mocked service)
        assert "results" in search_data
    
    @pytest.mark.asyncio
    async def test_qa_after_upload(self, async_client: AsyncClient):
        """Test that Q&A works after uploading documents."""
        # Upload test documents
        await self.create_multiple_test_documents(async_client, count=3)
        
        # Ask a question about the documents
        qa_data = await self.perform_qa_query(
            async_client,
            question="What topics are covered in the uploaded documents?"
        )
        
        # Should get an answer
        assert "answer" in qa_data
        assert len(qa_data["answer"]) > 0
        assert "citations" in qa_data
    
    @pytest.mark.asyncio
    async def test_search_and_qa_consistency(self, async_client: AsyncClient):
        """Test that search and Q&A return consistent information."""
        # Upload a document with specific content
        await self.create_test_document(
            async_client,
            content="The quarterly report shows significant growth in the technology sector.",
            filename="quarterly_report.txt"
        )
        
        # Search for the content
        search_data = await self.perform_search_get(
            async_client,
            q="quarterly report technology"
        )
        
        # Ask a related question
        qa_data = await self.perform_qa_query(
            async_client,
            question="What does the quarterly report say about technology?"
        )
        
        # Both should return relevant results
        assert "results" in search_data
        assert "answer" in qa_data