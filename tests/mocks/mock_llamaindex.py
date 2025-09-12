"""
Mock LlamaIndex components for testing.

This module provides test-only mocks to avoid external dependencies during testing.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, AsyncMock
from llama_index.core import VectorStoreIndex, StorageContext, Settings
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.vector_stores import SimpleVectorStore
from llama_index.core.embeddings import MockEmbedding
from llama_index.core.llms import MockLLM as BaseMockLLM


def setup_mock_llama_index():
    """
    Configure LlamaIndex with mock components for testing.
    
    This function should be called BEFORE creating LlamaIndexService to avoid:
    - Ollama connection attempts
    - HuggingFace model downloads
    - Any external service dependencies
    
    Note: This must be called before LlamaIndexService initialization
    to prevent the service from setting up real models.
    """
    # Use mock embedding to avoid HuggingFace downloads
    Settings.embed_model = MockEmbedding(embed_dim=384)
    
    # Use mock LLM to avoid Ollama connection
    Settings.llm = BaseMockLLM()
    
    # Configure other settings for testing
    from llama_index.core.node_parser import SentenceSplitter
    Settings.node_parser = SentenceSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separator="\n\n",
    )


def create_mock_index() -> VectorStoreIndex:
    """
    Create a mock VectorStoreIndex for testing.
    
    Returns:
        A VectorStoreIndex with mock storage components.
    """
    storage_context = StorageContext.from_defaults(
        vector_store=SimpleVectorStore(),
        docstore=SimpleDocumentStore(),
        index_store=SimpleIndexStore(),
    )
    return VectorStoreIndex([], storage_context=storage_context)


class MockLlamaIndexService:
    """
    Mock LlamaIndexService for unit testing.
    
    This mock provides the same interface as the real LlamaIndexService
    but with all methods mocked for fast, isolated testing.
    """
    
    def __init__(self, database=None, vault=None):
        self.database = database
        self.vault = vault
        self.index = create_mock_index()
        self.query_engine = MagicMock()
        
        # Mock all async methods
        self.add_document = AsyncMock(return_value=True)
        self.update_document_metadata = AsyncMock(return_value=True)
        self.query_documents_by_metadata = AsyncMock(return_value=[])
        self.query = AsyncMock(return_value={
            "answer": "Mock answer",
            "sources": [],
            "method": "mock",
            "metadata": {}
        })
        self.retrieve_similar = AsyncMock(return_value=[])
        self.get_document_analysis = AsyncMock(return_value={
            "document_id": "mock_id",
            "status": "indexed",
            "original_metadata": {},
            "processing_info": {},
            "storage_info": {},
            "chunks_preview": []
        })
        self.get_document_chunks = AsyncMock(return_value={
            "document_id": "mock_id",
            "chunks": [],
            "total": 0,
            "limit": 100,
            "offset": 0,
            "has_more": False
        })
        self.get_document_neighbors = AsyncMock(return_value={
            "document_id": "mock_id",
            "neighbors": [],
            "total_found": 0,
            "query_text": ""
        })
        self.clear_all_data = AsyncMock(return_value={
            "storage_files_deleted": 0,
            "storage_bytes_reclaimed": 0,
            "index_reset": True,
            "errors": []
        })
        self._persist_index = AsyncMock(return_value=None)
        self._initialize_empty_index = AsyncMock(return_value=None)