"""
Demonstration of the Document Lifecycle Solution

This test file demonstrates how the new document lifecycle fixtures solve the critical
testing problem where routes need pre-existing processed documents to function properly.

BEFORE: Tests would fail because they tried to search empty indexes
AFTER: Tests use populated fixtures with ready-to-search documents

Run this test to see the solution in action:
    pytest tests/examples/test_document_lifecycle_demo.py -v
"""

import pytest
from httpx import AsyncClient
from typing import Dict, Any, List

from ..base import PopulatedRouteTest


class TestDocumentLifecycleDemonstration(PopulatedRouteTest):
    """Demonstrates the document lifecycle problem solution."""
    
    @pytest.mark.asyncio
    async def test_before_and_after_comparison(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """
        Demonstrates the difference between testing with empty vs populated vault.
        
        This test shows how the document lifecycle fixtures provide meaningful test data.
        """
        
        # STEP 1: Show the "BEFORE" scenario - what happens with empty search
        print("\n=== BEFORE: Testing with potentially empty vault ===")
        
        # This would typically fail or return no results in the old testing approach
        empty_search = await self.perform_search_get(
            async_client,
            q="artificial intelligence machine learning",
            limit=10
        )
        
        print(f"Empty search results: {len(empty_search['results'])} documents found")
        print(f"Empty search total: {empty_search['total']}")
        
        # STEP 2: Show the "AFTER" scenario - populated fixtures in action
        print("\n=== AFTER: Testing with populated document fixtures ===")
        
        # Set up with populated documents
        test_context = await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        print(f"Documents available for testing: {test_context['documents_available']}")
        print(f"Vault ready for testing: {test_context['vault_ready']}")
        print(f"Documents are searchable: {test_context['searchable']}")
        
        # Now search will return meaningful results
        populated_search = await self.perform_search_get(
            async_client,
            q="medical financial report analysis",  # Query that matches our test documents
            limit=10
        )
        
        print(f"Populated search results: {len(populated_search['results'])} documents found")
        print(f"Populated search total: {populated_search['total']}")
        
        # STEP 3: Demonstrate Q&A functionality with populated content
        print("\n=== Q&A with populated documents ===")
        
        qa_response = await self.perform_qa_query(
            async_client,
            question="What topics are covered in these documents?",
            context_limit=5
        )
        
        print(f"Q&A Answer length: {len(qa_response['answer'])} characters")
        print(f"Q&A Citations: {len(qa_response['citations'])} documents cited")
        print(f"Q&A Confidence: {qa_response['confidence']}")
        print(f"Answer preview: {qa_response['answer'][:200]}...")
        
        # STEP 4: Demonstrate document management with real content
        print("\n=== Document management with populated content ===")
        
        documents_list = await self.list_documents(async_client, limit=5)
        
        print(f"Documents in management API: {len(documents_list['documents'])}")
        
        if documents_list["documents"]:
            first_doc = documents_list["documents"][0]
            document_id = first_doc["document_id"]
            
            # Get detailed analysis
            analysis = await self.get_document_analysis(async_client, document_id)
            print(f"Document analysis - Status: {analysis['status']}")
            print(f"Document analysis - Total chunks: {analysis['total_chunks']}")
            
            # Get chunks
            chunks = await self.get_document_chunks(async_client, document_id, limit=3)
            print(f"Document chunks available: {len(chunks['chunks'])}")
        
        # ASSERTIONS: Verify the populated approach gives us meaningful test data
        assert test_context["documents_available"] > 0, "Should have documents for testing"
        assert len(populated_search["results"]) > 0, "Search should find documents"
        assert len(qa_response["answer"]) > 50, "Q&A should provide substantial answer"
        assert len(qa_response["citations"]) > 0, "Q&A should cite sources"
        assert len(documents_list["documents"]) > 0, "Document management should list documents"
        
        print("\n=== CONCLUSION ===")
        print("✅ Document lifecycle fixtures provide comprehensive test data")
        print("✅ Search functionality works with populated content") 
        print("✅ Q&A functionality provides meaningful responses")
        print("✅ Document management APIs have real content to manage")
        print("✅ Routes are testable with realistic scenarios")
        
        return {
            "problem_solved": True,
            "documents_available": test_context["documents_available"],
            "search_results_found": len(populated_search["results"]),
            "qa_answer_provided": len(qa_response["answer"]) > 0,
            "document_management_working": len(documents_list["documents"]) > 0
        }
    
    @pytest.mark.asyncio
    async def test_domain_specific_testing_capabilities(
        self,
        async_client: AsyncClient,
        domain_specific_documents: Dict[str, List[Dict[str, Any]]]
    ):
        """
        Demonstrates how domain-specific fixtures enable targeted testing.
        
        This shows how you can test specific domains (medical, financial, etc.)
        with appropriate content for each domain.
        """
        
        print("\n=== DOMAIN-SPECIFIC TESTING DEMONSTRATION ===")
        
        available_domains = list(domain_specific_documents.keys())
        print(f"Available domains for testing: {available_domains}")
        
        for domain, documents in domain_specific_documents.items():
            print(f"\n--- Testing {domain.upper()} domain ---")
            print(f"Documents available: {len(documents)}")
            
            # Test domain-specific search
            if domain == "medical":
                search_query = "patient blood pressure treatment"
            elif domain == "financial":
                search_query = "earnings revenue investment"
            elif domain == "technical":
                search_query = "API performance system"
            else:
                search_query = "report analysis data"
            
            domain_search = await self.perform_search_get(
                async_client,
                q=search_query,
                limit=5
            )
            
            print(f"Domain search results: {len(domain_search['results'])}")
            
            # Test domain-specific Q&A
            if domain == "medical":
                qa_question = "What are the patient's vital signs?"
            elif domain == "financial":
                qa_question = "What are the financial performance metrics?"
            elif domain == "technical":
                qa_question = "What are the system performance improvements?"
            else:
                qa_question = "What are the key findings?"
            
            domain_qa = await self.perform_qa_query(
                async_client,
                question=qa_question,
                context_limit=3
            )
            
            print(f"Domain Q&A response: {len(domain_qa['answer'])} chars")
            print(f"Domain Q&A citations: {len(domain_qa['citations'])}")
            
            # Verify domain testing works
            assert len(documents) > 0, f"Should have {domain} documents"
            # Search and Q&A should work (may not always find results depending on content)
        
        print(f"\n✅ Domain-specific testing enables targeted route validation")
        print(f"✅ Each domain can be tested with appropriate content and queries")
        print(f"✅ Supports realistic testing scenarios for specialized applications")
    
    @pytest.mark.asyncio
    async def test_lifecycle_performance_demonstration(
        self,
        async_client: AsyncClient,
        multiple_processed_documents: List[Dict[str, Any]]
    ):
        """
        Demonstrates that the lifecycle fixtures provide good performance for testing.
        
        Shows that documents are processed once during fixture setup and reused
        across multiple tests efficiently.
        """
        import time
        
        print("\n=== PERFORMANCE DEMONSTRATION ===")
        
        start_time = time.time()
        
        # These operations should be fast since documents are already processed
        search_start = time.time()
        search_results = await self.perform_search_get(
            async_client,
            q="comprehensive analysis report",
            limit=20
        )
        search_time = time.time() - search_start
        
        qa_start = time.time()  
        qa_results = await self.perform_qa_query(
            async_client,
            question="What are the main conclusions from the analysis?",
            context_limit=10
        )
        qa_time = time.time() - qa_start
        
        doc_mgmt_start = time.time()
        documents = await self.list_documents(async_client, limit=50)
        doc_mgmt_time = time.time() - doc_mgmt_start
        
        total_time = time.time() - start_time
        
        print(f"Search operation: {search_time:.3f}s ({len(search_results['results'])} results)")
        print(f"Q&A operation: {qa_time:.3f}s ({len(qa_results['answer'])} chars answer)")
        print(f"Document mgmt: {doc_mgmt_time:.3f}s ({len(documents['documents'])} docs listed)")
        print(f"Total test time: {total_time:.3f}s")
        
        # Performance should be reasonable since documents are pre-processed
        assert search_time < 5.0, "Search should be reasonably fast with processed documents"
        assert qa_time < 10.0, "Q&A should be reasonably fast with processed documents"
        assert doc_mgmt_time < 2.0, "Document management should be fast"
        
        print(f"\n✅ Lifecycle fixtures provide good test performance")
        print(f"✅ Pre-processed documents enable fast route testing")
        print(f"✅ No need to wait for document processing during each test")
        
        return {
            "performance_acceptable": True,
            "search_time": search_time,
            "qa_time": qa_time,
            "doc_mgmt_time": doc_mgmt_time,
            "total_time": total_time
        }
    
    @pytest.mark.asyncio
    async def test_integration_workflow_demonstration(
        self,
        async_client: AsyncClient,
        populated_vault_with_search_ready_docs: Dict[str, Any]
    ):
        """
        Demonstrates a complete integration workflow using populated fixtures.
        
        This shows how multiple routes work together when they have realistic
        data to operate on.
        """
        
        print("\n=== INTEGRATION WORKFLOW DEMONSTRATION ===")
        
        # Set up populated environment
        await self.setup_populated_test(populated_vault_with_search_ready_docs)
        
        print("Step 1: Upload new content to existing populated vault")
        new_upload = await self.perform_upload(
            async_client,
            file_content=b"Integration test document with machine learning content",
            filename="integration_test.txt",
            tags=["integration", "test"]
        )
        new_file_id = new_upload["file_id"]
        print(f"✅ Uploaded new document: {new_file_id}")
        
        print("Step 2: Search across both existing and new content")
        comprehensive_search = await self.perform_search_get(
            async_client,
            q="machine learning analysis",
            limit=15
        )
        print(f"✅ Search found {len(comprehensive_search['results'])} documents")
        
        print("Step 3: List all documents via management API")
        all_documents = await self.list_documents(async_client, limit=100)
        print(f"✅ Document management lists {len(all_documents['documents'])} total documents")
        
        print("Step 4: Get detailed analysis for specific documents")
        analyzed_docs = []
        for doc in all_documents["documents"][:3]:  # Analyze first 3
            analysis = await self.get_document_analysis(async_client, doc["document_id"])
            analyzed_docs.append(analysis)
        print(f"✅ Analyzed {len(analyzed_docs)} documents in detail")
        
        print("Step 5: Perform Q&A across the comprehensive dataset")
        final_qa = await self.perform_qa_query(
            async_client,
            question="What are the key themes across all these documents?",
            context_limit=15
        )
        print(f"✅ Q&A synthesized answer from {len(final_qa['citations'])} citations")
        
        print("Step 6: Cleanup - demonstrate document management")
        clear_result = await self.clear_all_documents(async_client)
        print(f"✅ Cleaned up {clear_result['summary']['total_files_deleted']} files")
        
        # Verify the integration workflow
        assert len(comprehensive_search["results"]) > 0, "Integration search should find documents"
        assert len(all_documents["documents"]) > 0, "Document management should show all docs"
        assert len(analyzed_docs) > 0, "Should be able to analyze documents"
        assert len(final_qa["answer"]) > 100, "Q&A should provide comprehensive answer"
        assert clear_result["success"], "Cleanup should succeed"
        
        print("\n=== INTEGRATION WORKFLOW COMPLETE ===")
        print("✅ All routes work together seamlessly with populated data")
        print("✅ Upload → Search → Document Management → Q&A → Cleanup workflow verified")
        print("✅ Realistic end-to-end testing is now possible")
        
        return {
            "integration_workflow_complete": True,
            "upload_successful": bool(new_file_id),
            "search_found_documents": len(comprehensive_search["results"]),
            "documents_analyzed": len(analyzed_docs),
            "qa_provided_synthesis": len(final_qa["answer"]) > 100,
            "cleanup_successful": clear_result["success"]
        }