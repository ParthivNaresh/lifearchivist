"""
Document lifecycle fixtures for testing routes that depend on processed documents.

This module provides fixtures that handle the complete document processing pipeline:
1. File creation → 2. Vault storage → 3. LlamaIndex processing → 4. Ready for search/query

These fixtures solve the critical testing gap where routes need pre-existing processed 
documents to function properly.
"""

from typing import Dict, Any, List, Tuple, Optional, Callable
import os
import pytest
import pytest_asyncio

from factories.file.temp_file_manager import TempFileManager
from lifearchivist.server.mcp_server import MCPServer
from factories.file.file_factory import FileFactory
from factories.document_factory import DocumentFactory
from ..utils.helpers import assert_valid_file_id, wait_for_condition

# ------------------------------------------------------------------
# Configuration: timeouts for readiness checks (overridable via env)
# ------------------------------------------------------------------
DEFAULT_TIMEOUT_SINGLE = float(os.getenv("TEST_TIMEOUT_SINGLE", "10.0"))
DEFAULT_TIMEOUT_BATCH = float(os.getenv("TEST_TIMEOUT_BATCH", "15.0"))
DEFAULT_TIMEOUT_QUICK = float(os.getenv("TEST_TIMEOUT_QUICK", "5.0"))


# ------------------------------------------------------------------
# Internal helpers to ingest files via the server and wait for readiness
# ------------------------------------------------------------------
async def ingest_and_wait_ready(
    server: MCPServer,
    test_file,
    *,
    extra_metadata: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_TIMEOUT_SINGLE,
    tfm: Optional[TempFileManager] = None,
) -> Dict[str, Any]:
    """Ingest a single TestFile and wait until it is ready in the index.

    Returns a standardized dict with essential fields for assertions.
    """
    # Manage temp file lifecycle internally if not provided
    if tfm is None:
        async with _TempFileManagerAsyncContext() as ctx:
            return await _ingest_with_manager(server, test_file, extra_metadata, timeout, ctx.tfm)
    else:
        return await _ingest_with_manager(server, test_file, extra_metadata, timeout, tfm)


async def _ingest_with_manager(
    server: MCPServer,
    test_file,
    extra_metadata: Optional[Dict[str, Any]],
    timeout: float,
    tfm: TempFileManager,
) -> Dict[str, Any]:
    temp_path = tfm.create_temp_file(test_file)
    import_params = DocumentFactory.build_ingest_request_from_test_file(
        test_file, temp_path=str(temp_path), extra_metadata=extra_metadata or {}
    )
    result = await server.execute_tool("file.import", import_params)
    assert result["success"], f"Document processing failed: {result.get('error')}"

    file_id = result["result"]["file_id"]
    assert_valid_file_id(file_id)

    async def check_ready():
        return await _check_document_ready(server, file_id)

    await wait_for_condition(
        check_ready,
        timeout=timeout,
        error_message=f"Document {file_id} not ready within timeout",
    )

    return {
        "file_id": file_id,
        "filename": test_file.filename,
        "hash": test_file.hash,
        "size": test_file.size,
        "mime_type": test_file.mime_type,
        "status": "ready",
        "metadata": result["result"],
    }


async def ingest_files(
    server: MCPServer,
    test_files: List,
    *,
    timeout_each: float = DEFAULT_TIMEOUT_BATCH,
    extra_metadata_provider: Optional[Callable[[Any], Optional[Dict[str, Any]]]] = None,
) -> List[Dict[str, Any]]:
    """Ingest a batch of TestFiles with a shared TempFileManager and wait for readiness."""
    results: List[Dict[str, Any]] = []
    with TempFileManager() as tfm:
        for tf in test_files:
            extra = extra_metadata_provider(tf) if extra_metadata_provider else None
            doc_info = await ingest_and_wait_ready(
                server, tf, extra_metadata=extra, timeout=timeout_each, tfm=tfm
            )
            results.append(doc_info)
    return results


class _TempFileManagerAsyncContext:
    """Async-friendly wrapper for TempFileManager to use with 'async with'."""

    def __init__(self):
        self.tfm: Optional[TempFileManager] = None

    async def __aenter__(self):
        self.tfm = TempFileManager()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.tfm is not None:
            self.tfm.cleanup()
        self.tfm = None


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
    
    # Create test file
    test_file = FileFactory.create_text_file(
        content=test_content.strip(),
        filename="test_document.txt",
        metadata={"category": "test", "source": "fixture"},
    )

    doc_info = await ingest_and_wait_ready(
        test_server, test_file, timeout=DEFAULT_TIMEOUT_SINGLE
    )
    return {
        **doc_info,
        "content": test_content.strip(),
    }


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
    
    # Build files list
    files: List = []
    for cfg in test_documents:
        files.append(
            FileFactory.create_text_file(
                content=cfg["content"].strip(),
                filename=cfg["filename"],
                metadata={"category": cfg["category"], "source": "fixture_batch"},
            )
        )

    def _extra(tf) -> Dict[str, Any]:
        # category provided in file metadata; also surface it at ingest
        return {"category": tf.metadata.get("category")}

    processed = await ingest_files(
        test_server, files, timeout_each=DEFAULT_TIMEOUT_BATCH, extra_metadata_provider=_extra
    )

    # Attach plain content for convenience in assertions
    for p, cfg in zip(processed, test_documents):
        p["content"] = cfg["content"].strip()
    return processed


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
    
    processed_domains: Dict[str, List[Dict[str, Any]]] = {}

    for domain_name, docs in domains.items():
        files_for_domain: List = []
        for cfg in docs:
            files_for_domain.append(
                FileFactory.create_text_file(
                    content=cfg["content"],
                    filename=cfg["filename"],
                    metadata={"domain": domain_name, "source": "domain_fixture"},
                )
            )

        def _extra(tf) -> Dict[str, Any]:
            return {"domain": domain_name}

        processed = await ingest_files(
            test_server,
            files_for_domain,
            timeout_each=DEFAULT_TIMEOUT_SINGLE,
            extra_metadata_provider=_extra,
        )

        # Attach content and group by domain
        for p, cfg in zip(processed, docs):
            p["content"] = cfg["content"]
        processed_domains[domain_name] = processed

    return processed_domains


# Helper functions

async def _check_document_ready(server: MCPServer, file_id: str) -> bool:
    """Check if a document is fully processed and ready for search/query."""
    try:
        # Check LlamaIndex for document
        docs = await server.llamaindex_service.query_documents_by_metadata(
            filters={"document_id": file_id}, limit=1
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
    
    test_file = FileFactory.create_text_file(content=content, filename="quick_test.txt")
    doc_info = await ingest_and_wait_ready(
        test_server, test_file, timeout=DEFAULT_TIMEOUT_QUICK
    )
    return doc_info["file_id"]


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