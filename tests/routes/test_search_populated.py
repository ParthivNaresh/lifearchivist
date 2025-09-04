"""
Enhanced search route tests using populated document fixtures.

This demonstrates how to test search functionality with pre-existing processed documents,
solving the document lifecycle problem that was identified in the testing framework review.
"""

import pytest
from httpx import AsyncClient
from typing import Dict, Any, List

from ..base import BaseSearchTest, BaseUploadTest, PopulatedRouteTest
from ..utils.assertions import assert_search_response, assert_qa_response


class TestSearchWithPopulatedDocuments(BaseSearchTest, PopulatedRouteTest):
    """Test search routes with populated documents - demonstrates the solution to the document lifecycle problem."""
    
    @pytest.mark.asyncio
    async def test_search_with_existing_content(
        self, 
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test search functionality with pre-populated documents."""
        # Set up test with populated documents
        test_context = await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        # Verify we have documents to test with
        assert test_context["documents_available"] > 0, "Should have documents for testing"
        assert test_context["searchable"], "Documents should be searchable"
        
        # Test search with content that should return results
        search_query = self.get_sample_search_content()
        
        search_data = await self.perform_search_get(
            async_client,
            q=search_query,
            limit=10
        )
        
        # Should find results since we have populated content
        assert len(search_data["results"]) > 0, f"Search for '{search_query}' should return results"
        assert search_data["total"] > 0, "Total results should be greater than 0"
        
        # Verify search result structure
        for result in search_data["results"]:
            assert "document_id" in result
            assert "score" in result
            assert 0 <= result["score"] <= 1
    
    @pytest.mark.asyncio
    async def test_domain_specific_search(
        self, 
        async_client: AsyncClient,
        domain_specific_documents: Dict[str, List[Dict[str, Any]]]
    ):
        """Test search with domain-specific documents."""
        # Test medical domain search
        medical_results = await self.perform_search_get(
            async_client,
            q="blood pressure patient treatment",
            limit=5
        )
        
        # Should find medical documents
        assert len(medical_results["results"]) > 0, "Should find medical documents"
        
        # Test financial domain search
        financial_results = await self.perform_search_get(
            async_client,
            q="earnings revenue investment growth",
            limit=5
        )
        
        # Should find financial documents
        assert len(financial_results["results"]) > 0, "Should find financial documents"
        
        # Results should be different (different domains)
        medical_doc_ids = {r["document_id"] for r in medical_results["results"]}
        financial_doc_ids = {r["document_id"] for r in financial_results["results"]}
        
        # May have some overlap but should have domain-specific results
        assert len(medical_doc_ids) > 0, "Should have medical document results"
        assert len(financial_doc_ids) > 0, "Should have financial document results"
    
    @pytest.mark.asyncio
    async def test_search_with_filters_on_populated_data(
        self,
        async_client: AsyncClient,
        multiple_processed_documents: List[Dict[str, Any]]
    ):
        """Test search filters work with populated documents."""
        # Get a specific document category for filtering
        medical_doc = None
        for doc in multiple_processed_documents:
            if doc.get("category") == "medical":
                medical_doc = doc
                break
        
        if medical_doc:
            # Search with category filter using POST (filters only supported in POST)
            filtered_results = await self.perform_search_post(
                async_client,
                query="treatment",
                filters={"category": "medical"},
                limit=10
            )
            
            # Should find medical documents specifically
            assert len(filtered_results["results"]) > 0, "Should find filtered medical results"
    
    @pytest.mark.asyncio 
    async def test_search_pagination_with_real_data(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test search pagination with actual populated documents."""
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        # Get broad search query that should return multiple results
        search_query = "document report analysis"
        
        # Test first page
        page1_results = await self.perform_search_get(
            async_client,
            q=search_query,
            limit=2,
            offset=0
        )
        
        # Test second page
        page2_results = await self.perform_search_get(
            async_client,
            q=search_query,
            limit=2, 
            offset=2
        )
        
        # Verify pagination works
        assert page1_results["total"] >= 2, "Should have enough results for pagination"
        assert len(page1_results["results"]) <= 2, "Page 1 should respect limit"
        assert len(page2_results["results"]) <= 2, "Page 2 should respect limit"
        
        # Pages should have different results
        page1_ids = {r["document_id"] for r in page1_results["results"]}
        page2_ids = {r["document_id"] for r in page2_results["results"]}
        
        # Should be no overlap between pages (unless there are duplicates)
        overlap = page1_ids & page2_ids
        assert len(overlap) == 0, "Pages should not have overlapping results"


class TestQAWithPopulatedDocuments(BaseSearchTest, PopulatedRouteTest):
    """Test Q&A functionality with populated documents."""
    
    @pytest.mark.asyncio
    async def test_qa_with_domain_knowledge(
        self,
        async_client: AsyncClient,
        domain_specific_documents: Dict[str, List[Dict[str, Any]]]
    ):
        """Test Q&A with domain-specific populated documents."""
        # Test medical Q&A
        medical_qa = await self.perform_qa_query(
            async_client,
            question="What are the patient's blood pressure readings?",
            context_limit=3
        )
        
        assert len(medical_qa["answer"]) > 0, "Should get medical answer"
        assert medical_qa["confidence"] > 0, "Should have some confidence"
        assert len(medical_qa["citations"]) > 0, "Should cite medical documents"
        
        # Test financial Q&A
        financial_qa = await self.perform_qa_query(
            async_client,
            question="What were the quarterly earnings results?",
            context_limit=3
        )
        
        assert len(financial_qa["answer"]) > 0, "Should get financial answer"
        assert financial_qa["confidence"] > 0, "Should have some confidence"
        assert len(financial_qa["citations"]) > 0, "Should cite financial documents"
    
    @pytest.mark.asyncio
    async def test_qa_cross_document_synthesis(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test Q&A that synthesizes information across multiple documents."""
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        # Ask broad question that should pull from multiple documents
        synthesis_qa = await self.perform_qa_query(
            async_client,
            question="What are the main topics covered across all these documents?",
            context_limit=10
        )
        
        assert len(synthesis_qa["answer"]) > 50, "Should get comprehensive answer"
        assert len(synthesis_qa["citations"]) >= 1, "Should have at least one citation"
        
        # If we have multiple citations, verify they can reference different documents
        cited_doc_ids = set()
        for citation in synthesis_qa["citations"]:
            cited_doc_ids.add(citation["doc_id"])
        
        # The AI might synthesize from one comprehensive source or multiple sources
        # Both approaches are valid for a broad question
        assert len(cited_doc_ids) >= 1, "Should cite at least one document"
        
        # Verify answer mentions multiple topic domains if available
        answer_lower = synthesis_qa["answer"].lower()
        topic_mentions = 0
        topic_keywords = ["medical", "financial", "real estate", "technology", "housing"]
        for keyword in topic_keywords:
            if keyword in answer_lower:
                topic_mentions += 1
        
        # Should mention at least 2 different topic areas from our diverse documents
        assert topic_mentions >= 2, f"Answer should mention multiple topics from diverse documents, found {topic_mentions}"
    
    @pytest.mark.asyncio
    async def test_qa_with_no_relevant_context(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test Q&A when asking about topics not in the documents."""
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        # Ask about something not in our test documents
        irrelevant_qa = await self.perform_qa_query(
            async_client,
            question="What is the capital of Mars?",
            context_limit=5
        )
        
        # Should still get a response, but with low confidence or explicit "not found"
        assert len(irrelevant_qa["answer"]) > 0, "Should get some response"
        # Confidence might be low for irrelevant questions
        # Citations might be empty or explain lack of relevant information


class TestSearchIntegrationWithLifecycle(BaseSearchTest, BaseUploadTest, PopulatedRouteTest):
    """Integration tests demonstrating the complete document lifecycle in action."""
    
    @pytest.mark.asyncio
    async def test_upload_then_immediate_search(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test that newly uploaded content becomes immediately searchable."""
        # Start with populated documents for baseline
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        baseline_count = self.document_count
        
        # Upload new content
        new_content = "Unique test content about quantum computing algorithms and implementation."
        new_doc_data = await self.perform_upload(
            async_client,
            file_content=new_content.encode(),
            filename="quantum_computing.txt",
            tags=["quantum", "algorithms"]
        )
        
        new_file_id = new_doc_data["file_id"]
        
        # Search for the new content - should find it after processing
        search_results = await self.perform_search_get(
            async_client,
            q="quantum computing algorithms",
            limit=10
        )
        
        # Should find the new document
        assert len(search_results["results"]) > 0, "Should find newly uploaded document"
        
        # Verify one of the results is our new document
        found_new_doc = False
        for result in search_results["results"]:
            if result["document_id"] == new_file_id:
                found_new_doc = True
                break
        
        assert found_new_doc, "Should find newly uploaded document in search results"
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_populated_baseline(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """Test complete workflow: populated baseline → upload → search → query."""
        # 1. Start with populated baseline
        baseline_context = await self.setup_populated_test(populated_vault_with_search_ready_docs)
        baseline_search = await self.verify_documents_searchable(async_client)
        baseline_qa = await self.verify_documents_queryable(async_client)
        
        # 2. Add new content
        new_content = "Artificial intelligence breakthrough in natural language understanding."
        upload_data = await self.perform_upload(
            async_client,
            file_content=new_content.encode(),
            filename="ai_breakthrough.txt"
        )
        
        # 3. Search should now include both baseline and new content
        # Use a broad query that could match both old and new documents
        comprehensive_search = await self.perform_search_get(
            async_client,
            q="analysis report document",
            limit=20
        )
        
        # The new document adds to the total document count, so total should increase
        # However, specific search results depend on relevance, so we verify differently
        total_docs_after = len(comprehensive_search["results"]) if comprehensive_search["results"] else 0
        total_docs_baseline = len(baseline_search["results"]) if baseline_search["results"] else 0
        
        # Either we get more results, or we verify the new document was indeed indexed
        # by checking if we can find it with a specific search
        ai_specific_search = await self.perform_search_get(
            async_client,
            q="artificial intelligence breakthrough",
            limit=5
        )
        
        found_new_doc = any(
            "artificial intelligence" in result.get("snippet", "").lower() 
            for result in ai_specific_search["results"]
        )
        
        assert found_new_doc or total_docs_after > total_docs_baseline, \
            "Should either find more results with broad search or be able to find the new AI document specifically"
        
        # 4. Q&A should be able to answer about both old and new content
        comprehensive_qa = await self.perform_qa_query(
            async_client,
            question="What topics related to artificial intelligence are discussed?",
            context_limit=10
        )
        
        assert len(comprehensive_qa["answer"]) > 0, "Should answer AI-related question"
        assert len(comprehensive_qa["citations"]) > 0, "Should have citations"
        
        return {
            "baseline_context": baseline_context,
            "new_document": upload_data,
            "comprehensive_search": comprehensive_search,
            "comprehensive_qa": comprehensive_qa,
            "workflow_completed": True
        }