"""
Document lifecycle fixtures for testing routes that depend on processed documents.

This module provides fixtures that handle the complete document processing pipeline:
1. File creation → 2. Vault storage → 3. LlamaIndex processing → 4. Ready for search/query

These fixtures solve the critical testing gap where routes need pre-existing processed 
documents to function properly.
"""

import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pytest
import pytest_asyncio

from lifearchivist.server.mcp_server import MCPServer
from ..factories.file_factory import FileFactory, TestFile, TempFileFactory
from ..utils.helpers import extract_file_id, assert_valid_file_id, wait_for_condition


@pytest_asyncio.fixture
async def single_processed_document(test_server: MCPServer) -> Dict[str, Any]:
    """
    Create a single fully processed document ready for testing.
    
    Returns:
        Document metadata with file_id, content, and processing status
    """
    # Create test content
    test_content = """
    This is a comprehensive test document for search and query functionality.
    It contains important information about artificial intelligence and machine learning.
    
    Key topics covered:
    - Natural language processing techniques
    - Document retrieval systems  
    - Vector embeddings and similarity search
    - Question answering systems
    
    This document was created for testing purposes and contains enough content
    to generate meaningful search results and answer relevant questions.
    """
    
    # Create temporary file
    test_file = FileFactory.create_text_file(
        content=test_content.strip(),
        filename="test_document.txt",
        metadata={"category": "test", "source": "fixture"}
    )
    
    temp_path = TempFileFactory.create_temp_file(test_file)
    
    try:
        # Process through the complete pipeline
        result = await test_server.execute_tool(
            "file.import", 
            {
                "path": str(temp_path),
                "metadata": {"original_filename": test_file.filename}
            }
        )
        
        assert result["success"], f"Document processing failed: {result.get('error')}"
        
        file_id = result["result"]["file_id"]
        assert_valid_file_id(file_id)
        
        # Wait for document to be fully processed and ready
        async def check_ready():
            return await _check_document_ready(test_server, file_id)
        
        await wait_for_condition(
            check_ready,
            timeout=10.0,
            error_message=f"Document {file_id} not ready within timeout"
        )
        
        return {
            "file_id": file_id,
            "content": test_content.strip(),
            "filename": test_file.filename,
            "hash": test_file.hash,
            "size": test_file.size,
            "mime_type": test_file.mime_type,
            "status": "ready",
            "metadata": result["result"]
        }
        
    finally:
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()


@pytest_asyncio.fixture
async def multiple_processed_documents(test_server: MCPServer) -> List[Dict[str, Any]]:
    """
    Create multiple fully processed documents with diverse content for comprehensive testing.
    
    Returns:
        List of document metadata dictionaries, each ready for search/query
    """
    # Define diverse test documents
    test_documents = [
        {
            "content": """
            Medical Research Report: COVID-19 Treatment Protocols
            
            This comprehensive medical document outlines treatment protocols for COVID-19 patients.
            Key findings include the effectiveness of remdesivir and dexamethasone.
            
            Patient outcomes showed:
            - 85% recovery rate with early intervention
            - Reduced mortality in ICU patients
            - Lower inflammatory markers with steroid treatment
            
            Healthcare professionals should follow these evidence-based protocols
            for optimal patient care and recovery outcomes.
            """,
            "filename": "medical_report.txt",
            "category": "medical"
        },
        {
            "content": """
            Financial Analysis: Q4 2024 Technology Sector Performance
            
            This quarterly financial report analyzes technology sector performance.
            Major tech companies showed strong growth despite market volatility.
            
            Key metrics:
            - Apple revenue increased 8% year-over-year
            - Microsoft cloud services grew 22%  
            - Google advertising revenue up 11%
            - Tesla delivered record vehicle numbers
            
            Investment recommendations favor cloud computing and AI companies
            for continued growth potential in 2025.
            """,
            "filename": "financial_report.pdf",
            "category": "financial"
        },
        {
            "content": """
            Real Estate Market Analysis: Housing Trends 2024
            
            The housing market has shown resilience despite economic headwinds.
            Mortgage rates have stabilized around 6.5% for 30-year fixed loans.
            
            Market trends:
            - Home prices increased 4.2% nationally
            - Inventory levels remain below historical averages
            - First-time buyer activity decreased 15%
            - Refinancing applications down 40%
            
            Regional variations show stronger performance in sunbelt states
            compared to coastal markets with higher interest rate sensitivity.
            """,
            "filename": "real_estate_analysis.txt", 
            "category": "real_estate"
        }
    ]
    
    processed_docs = []
    temp_paths = []
    
    try:
        # Process each document through the pipeline
        for doc_config in test_documents:
            # Create test file
            test_file = FileFactory.create_text_file(
                content=doc_config["content"].strip(),
                filename=doc_config["filename"],
                metadata={"category": doc_config["category"], "source": "fixture_batch"}
            )
            
            temp_path = TempFileFactory.create_temp_file(test_file)
            temp_paths.append(temp_path)
            
            # Process document
            result = await test_server.execute_tool(
                "file.import",
                {
                    "path": str(temp_path),
                    "metadata": {
                        "original_filename": test_file.filename,
                        "category": doc_config["category"]
                    }
                }
            )
            
            assert result["success"], f"Document processing failed: {result.get('error')}"
            
            file_id = result["result"]["file_id"]
            assert_valid_file_id(file_id)
            
            processed_docs.append({
                "file_id": file_id,
                "content": doc_config["content"].strip(),
                "filename": test_file.filename,
                "category": doc_config["category"],
                "hash": test_file.hash,
                "size": test_file.size,
                "mime_type": test_file.mime_type,
                "status": "ready",
                "metadata": result["result"]
            })
        
        # Wait for all documents to be ready
        for doc in processed_docs:
            file_id = doc["file_id"]
            
            async def check_doc_ready():
                return await _check_document_ready(test_server, file_id)
            
            await wait_for_condition(
                check_doc_ready,
                timeout=15.0,
                error_message=f"Document {file_id} not ready within timeout"
            )
        
        return processed_docs
        
    finally:
        # Cleanup temp files
        for temp_path in temp_paths:
            if temp_path.exists():
                temp_path.unlink()


@pytest_asyncio.fixture
async def populated_vault_with_search_ready_docs(
    test_server: MCPServer, 
    multiple_processed_documents: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Create a fully populated vault with documents ready for search and query operations.
    
    This fixture provides the complete testing environment that most routes need:
    - Documents stored in vault
    - Content indexed in LlamaIndex
    - Ready for search/query/analysis operations
    
    Returns:
        Dictionary containing vault info and document list for test assertions
    """
    # Verify vault has documents
    vault_info = await test_server.vault.get_vault_statistics()
    assert vault_info["total_files"] > 0, "Vault should contain processed files"
    
    # Verify LlamaIndex has indexed documents  
    llamaindex_docs = await test_server.llamaindex_service.query_documents_by_metadata(
        filters={}, limit=100
    )
    assert len(llamaindex_docs) >= len(multiple_processed_documents), \
        "LlamaIndex should contain all processed documents"
    
    # Verify documents are searchable
    search_result = await test_server.execute_tool(
        "index.search",
        {
            "query": "test document",
            "mode": "keyword", 
            "limit": 10
        }
    )
    assert search_result["success"], "Search should work with populated vault"
    assert len(search_result["result"]["results"]) > 0, "Search should return results"
    
    return {
        "vault_stats": vault_info,
        "documents": multiple_processed_documents,
        "document_count": len(multiple_processed_documents),
        "searchable": True,
        "ready_for_testing": True
    }


@pytest_asyncio.fixture
async def domain_specific_documents(test_server: MCPServer) -> Dict[str, List[Dict[str, Any]]]:
    """
    Create domain-specific document collections for targeted testing.
    
    Returns:
        Dictionary with documents grouped by domain (medical, financial, technical)
    """
    domains = {
        "medical": [
            {
                "content": "Patient blood pressure readings show hypertension requiring medication adjustment.",
                "filename": "bp_reading.txt"
            },
            {
                "content": "Laboratory results indicate elevated cholesterol levels and vitamin D deficiency.",
                "filename": "lab_results.txt" 
            }
        ],
        "financial": [
            {
                "content": "Quarterly earnings exceeded expectations with 12% revenue growth.",
                "filename": "earnings_q4.txt"
            },
            {
                "content": "Investment portfolio performance shows 8.5% annual returns.",
                "filename": "portfolio_report.txt"
            }
        ],
        "technical": [
            {
                "content": "API response times improved 40% after database optimization.",
                "filename": "performance_report.txt"
            },
            {
                "content": "System architecture supports horizontal scaling to 10x current load.",
                "filename": "scaling_analysis.txt"
            }
        ]
    }
    
    processed_domains = {}
    all_temp_paths = []
    
    try:
        for domain_name, docs in domains.items():
            processed_docs = []
            
            for doc_config in docs:
                # Create and process document
                test_file = FileFactory.create_text_file(
                    content=doc_config["content"],
                    filename=doc_config["filename"],
                    metadata={"domain": domain_name, "source": "domain_fixture"}
                )
                
                temp_path = TempFileFactory.create_temp_file(test_file)
                all_temp_paths.append(temp_path)
                
                result = await test_server.execute_tool(
                    "file.import",
                    {
                        "path": str(temp_path),
                        "metadata": {
                            "original_filename": test_file.filename,
                            "domain": domain_name
                        }
                    }
                )
                
                assert result["success"], f"Domain document processing failed: {result.get('error')}"
                
                file_id = result["result"]["file_id"]
                
                # Wait for processing
                async def check_domain_doc_ready():
                    return await _check_document_ready(test_server, file_id)
                
                await wait_for_condition(
                    check_domain_doc_ready,
                    timeout=10.0,
                    error_message=f"Domain document {file_id} not ready"
                )
                
                processed_docs.append({
                    "file_id": file_id,
                    "content": doc_config["content"],
                    "filename": test_file.filename,
                    "domain": domain_name,
                    "metadata": result["result"]
                })
            
            processed_domains[domain_name] = processed_docs
        
        return processed_domains
        
    finally:
        # Cleanup temp files
        for temp_path in all_temp_paths:
            if temp_path.exists():
                temp_path.unlink()


# Helper functions

async def _check_document_ready(server: MCPServer, file_id: str) -> bool:
    """Check if a document is fully processed and ready for search/query."""
    try:
        # Check LlamaIndex for document
        docs = await server.llamaindex_service.query_documents_by_metadata(
            filters={"file_id": file_id}, limit=1
        )
        
        if not docs:
            return False
            
        doc = docs[0]
        
        # Check status is ready
        status = doc.get("metadata", {}).get("status")
        if status != "ready":
            return False
            
        # Verify document has been processed (has nodes)
        node_count = doc.get("node_count", 0)
        if node_count <= 0:
            return False
        
        # Verify basic metadata fields exist
        metadata = doc.get("metadata", {})
        if not metadata.get("has_content", False):
            return False
        
        # If we get this far, the document is ready for testing
        return True
        
    except Exception as e:
        # Log the exception for debugging but return False
        print(f"Debug: _check_document_ready exception for {file_id}: {e}")
        return False


@pytest_asyncio.fixture
async def quick_test_document(test_server: MCPServer) -> str:
    """
    Create a single document quickly for simple tests.
    
    Returns:
        file_id of the processed document
    """
    content = "Quick test document for simple route testing."
    
    test_file = FileFactory.create_text_file(
        content=content,
        filename="quick_test.txt"
    )
    
    temp_path = TempFileFactory.create_temp_file(test_file)
    
    try:
        result = await test_server.execute_tool(
            "file.import",
            {"path": str(temp_path)}
        )
        
        assert result["success"]
        file_id = result["result"]["file_id"]
        
        # Wait for ready status
        async def check_quick_doc_ready():
            return await _check_document_ready(test_server, file_id)
        
        await wait_for_condition(
            check_quick_doc_ready,
            timeout=5.0,
            error_message="Quick document not ready"
        )
        
        return file_id
        
    finally:
        if temp_path.exists():
            temp_path.unlink()


# Convenience fixtures for common testing scenarios

@pytest_asyncio.fixture
async def empty_then_populated_vault(test_server: MCPServer) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Provide both empty vault state and then populated state for comparison testing.
    
    Returns:
        Tuple of (empty_stats, populated_stats)
    """
    # Get empty vault stats
    empty_stats = await test_server.vault.get_vault_statistics()
    
    # Ensure vault starts empty
    if empty_stats["total_files"] > 0:
        await test_server.vault.clear_all_files([])
        empty_stats = await test_server.vault.get_vault_statistics()
    
    # Create a test document
    await quick_test_document(test_server)
    
    # Get populated stats
    populated_stats = await test_server.vault.get_vault_statistics() 
    
    return empty_stats, populated_stats


@pytest.fixture
def document_categories() -> List[str]:
    """Provide list of document categories used in test fixtures."""
    return ["medical", "financial", "real_estate", "technical"]


@pytest.fixture  
def search_test_queries() -> Dict[str, str]:
    """Provide common search queries for testing against populated documents."""
    return {
        "medical": "blood pressure patient treatment",
        "financial": "earnings revenue growth investment",
        "real_estate": "housing market mortgage rates",
        "technical": "API performance system architecture",
        "general": "report analysis data"
    }