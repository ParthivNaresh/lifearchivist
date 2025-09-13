import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY
from typing import Dict, Any, List
from pathlib import Path

from llama_index.core import Document, VectorStoreIndex, StorageContext
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.vector_stores import SimpleVectorStore

from lifearchivist.storage.llamaindex_service.llamaindex_service import LlamaIndexService
from lifearchivist.storage.llamaindex_service.llamaindex_service_utils import (
    DocumentFilter,
    NodeProcessor,
    calculate_document_metrics,
    create_error_response,
)
from factories.file.file_factory import FileFactory
from factories.document_factory import DocumentFactory
from factories.metadata_factory import MetadataFactory


class TestLlamaIndexServiceInitialization:
    
    def test_initialization_with_vault(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            assert service.vault == test_vault
            assert service.database is None
            assert service.settings == test_settings
    
    def test_initialization_without_vault(self, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService()
            assert service.vault is None
            assert service.database is None
            assert service.settings == test_settings
    
    def test_setup_llamaindex_creates_new_index_when_not_exists(self, test_vault, test_settings):
        storage_dir = test_settings.lifearch_home / "llamaindex_storage"
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            
            assert service.index is not None
            assert isinstance(service.index, VectorStoreIndex)
            assert storage_dir.exists()
    
    def test_setup_llamaindex_loads_existing_index(self, test_vault, test_settings):
        storage_dir = test_settings.lifearch_home / "llamaindex_storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        storage_context = StorageContext.from_defaults(
            vector_store=SimpleVectorStore(),
            docstore=SimpleDocumentStore(),
            index_store=SimpleIndexStore(),
        )
        test_index = VectorStoreIndex([], storage_context=storage_context)
        
        test_doc = Document(
            text="Test document for existing index",
            metadata={"test_marker": "existing_index_test"},
            id_="test_doc_1"
        )
        test_index.insert(test_doc)
        
        test_index.storage_context.persist(persist_dir=str(storage_dir))
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            
            assert service.index is not None
            assert isinstance(service.index, VectorStoreIndex)
            
            assert hasattr(service.index, 'ref_doc_info')
            assert 'test_doc_1' in service.index.ref_doc_info
            
            docstore = service.index.storage_context.docstore
            node_ids = service.index.ref_doc_info['test_doc_1'].node_ids
            if node_ids:
                first_node = docstore.get_node(node_ids[0])
                assert first_node is not None
                assert first_node.metadata.get("test_marker") == "existing_index_test"
    
    def test_setup_llamaindex_handles_wrong_index_type_creates_new(self, test_vault, test_settings):
        storage_dir = test_settings.lifearch_home / "llamaindex_storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            
            assert service.index is not None
            assert isinstance(service.index, VectorStoreIndex)
            assert len(service.index.ref_doc_info) == 0
    
    def test_setup_query_engine_with_index(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            
            if service.index:
                assert service.query_engine is not None
    
    def test_setup_query_engine_without_index(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            service.index = None
            service.query_engine = None
            service._setup_query_engine()
            
            assert service.query_engine is None


class TestDocumentOperations:
    
    @pytest.fixture
    def service_with_index(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            service.index = MagicMock(spec=VectorStoreIndex)
            service.index.ref_doc_info = {}
            service.index.insert = MagicMock()
            return service
    
    @pytest.mark.asyncio
    async def test_add_document_success(self, service_with_index):
        test_file = FileFactory.create_text_file(
            content="Test document content for indexing",
            filename="test_doc.txt"
        )
        
        service_with_index._persist_index = AsyncMock()
        
        result = await service_with_index.add_document(
            document_id=test_file.test_id,
            content=test_file.content.decode('utf-8'),
            metadata=test_file.to_llamaindex_format()["metadata"]
        )
        
        assert result is True
        service_with_index.index.insert.assert_called_once()
        service_with_index._persist_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_document_no_index(self, service_with_index):
        service_with_index.index = None
        
        result = await service_with_index.add_document(
            document_id="test_doc_1",
            content="Test content",
            metadata={}
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_add_document_with_empty_content(self, service_with_index):
        service_with_index._persist_index = AsyncMock()
        
        result = await service_with_index.add_document(
            document_id="test_doc_2",
            content="",
            metadata={"mime_type": "text/plain"}
        )
        
        assert result is True
        service_with_index.index.insert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_document_exception_handling(self, service_with_index):
        service_with_index.index.insert.side_effect = Exception("Insert failed")
        
        result = await service_with_index.add_document(
            document_id="test_doc_3",
            content="Test content",
            metadata={}
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("metadata,expected_fields", [
        (None, 1),
        ({"mime_type": "text/plain"}, 2),
        ({"mime_type": "text/plain", "size": 100, "tags": ["test"]}, 4),
    ])
    async def test_add_document_metadata_handling(self, service_with_index, metadata, expected_fields):
        service_with_index._persist_index = AsyncMock()
        
        await service_with_index.add_document(
            document_id="test_doc",
            content="Test content",
            metadata=metadata
        )
        
        call_args = service_with_index.index.insert.call_args[0][0]
        assert isinstance(call_args, Document)
        assert "document_id" in call_args.metadata
        if metadata:
            for key in metadata:
                assert key in call_args.metadata


class TestMetadataOperations:
    
    @pytest.fixture
    def service_with_documents(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            
            mock_node1 = MagicMock()
            mock_node1.metadata = {"document_id": "doc1", "tags": ["old"]}
            
            mock_node2 = MagicMock()
            mock_node2.metadata = {"document_id": "doc1", "tags": ["old"]}
            
            mock_docstore = MagicMock()
            mock_docstore.get_node = MagicMock(side_effect=[mock_node1, mock_node2])
            mock_docstore.add_documents = MagicMock()
            
            service.index = MagicMock(spec=VectorStoreIndex)
            service.index.ref_doc_info = {
                "doc1": MagicMock(node_ids=["node1", "node2"])
            }
            service.index.storage_context.docstore = mock_docstore
            
            return service
    
    @pytest.mark.asyncio
    async def test_update_metadata_merge_mode(self, service_with_documents):
        service_with_documents._persist_index = AsyncMock()
        
        metadata_updates = MetadataFactory.create_document_metadata(
            tags=["new"],
            extra={"status": "updated"}
        )
        
        result = await service_with_documents.update_document_metadata(
            document_id="doc1",
            metadata_updates={"tags": ["new"], "status": "updated"},
            merge_mode="update"
        )
        
        assert result is True
        assert service_with_documents.index.storage_context.docstore.add_documents.call_count == 2
        service_with_documents._persist_index.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_metadata_replace_mode(self, service_with_documents):
        service_with_documents._persist_index = AsyncMock()
        
        result = await service_with_documents.update_document_metadata(
            document_id="doc1",
            metadata_updates={"status": "replaced"},
            merge_mode="replace"
        )
        
        assert result is True
        assert service_with_documents.index.storage_context.docstore.add_documents.call_count == 2
    
    @pytest.mark.asyncio
    async def test_update_metadata_document_not_found(self, service_with_documents):
        result = await service_with_documents.update_document_metadata(
            document_id="nonexistent",
            metadata_updates={"status": "updated"},
            merge_mode="update"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_metadata_no_index(self, service_with_documents):
        service_with_documents.index = None
        
        result = await service_with_documents.update_document_metadata(
            document_id="doc1",
            metadata_updates={"status": "updated"},
            merge_mode="update"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_update_metadata_list_field_merging(self, service_with_documents):
        service_with_documents._persist_index = AsyncMock()
        
        mock_node = MagicMock()
        mock_node.metadata = {"document_id": "doc1", "tags": ["existing"], "content_dates": ["2024-01-01"]}
        service_with_documents.index.storage_context.docstore.get_node = MagicMock(return_value=mock_node)
        
        result = await service_with_documents.update_document_metadata(
            document_id="doc1",
            metadata_updates={
                "tags": ["new_tag"],
                "content_dates": ["2024-01-02"],
                "provenance": ["source1"]
            },
            merge_mode="update"
        )
        
        assert result is True
        updated_metadata = mock_node.metadata
        assert "existing" in updated_metadata["tags"]
        assert "new_tag" in updated_metadata["tags"]
        assert "2024-01-01" in updated_metadata["content_dates"]
        assert "2024-01-02" in updated_metadata["content_dates"]
        assert "source1" in updated_metadata["provenance"]
    
    @pytest.mark.asyncio
    async def test_update_metadata_node_failure_handling(self, service_with_documents):
        service_with_documents._persist_index = AsyncMock()
        service_with_documents.index.storage_context.docstore.get_node = MagicMock(return_value=None)
        
        result = await service_with_documents.update_document_metadata(
            document_id="doc1",
            metadata_updates={"status": "updated"},
            merge_mode="update"
        )
        
        assert result is False


class TestQueryByMetadata:
    
    @pytest.fixture
    def service_with_test_documents(self, test_llamaindex_service):
        mock_docstore = MagicMock()
        test_llamaindex_service.index = MagicMock(spec=VectorStoreIndex)
        
        docs_data = DocumentFactory.build_raw_documents_set(count=5)
        
        ref_doc_info = {}
        for doc in docs_data:
            doc_id = doc["document_id"]
            node_ids = [f"node_{doc_id}_{i}" for i in range(doc["node_count"])]
            ref_doc_info[doc_id] = MagicMock(node_ids=node_ids)
            
            for i, node_id in enumerate(node_ids):
                mock_node = MagicMock()
                mock_node.metadata = doc["metadata"]
                mock_node.text = doc["text_preview"]
                mock_docstore.get_node = MagicMock(return_value=mock_node)
        
        test_llamaindex_service.index.ref_doc_info = ref_doc_info
        test_llamaindex_service.index.storage_context.docstore = mock_docstore
        
        return test_llamaindex_service, docs_data
    
    @pytest.mark.asyncio
    async def test_query_documents_no_filters(self, service_with_test_documents):
        service, expected_docs = service_with_test_documents
        
        results = await service.query_documents_by_metadata(
            filters={},
            limit=10,
            offset=0
        )
        
        assert isinstance(results, list)
        assert len(results) <= 10
    
    @pytest.mark.asyncio
    async def test_query_documents_with_status_filter(self, service_with_test_documents):
        service, _ = service_with_test_documents
        
        filters = MetadataFactory.create_search_filters(status="ready")
        
        results = await service.query_documents_by_metadata(
            filters=filters,
            limit=10,
            offset=0
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_query_documents_with_pagination(self, service_with_test_documents):
        service, _ = service_with_test_documents
        
        results_page1 = await service.query_documents_by_metadata(
            filters={},
            limit=2,
            offset=0
        )
        
        results_page2 = await service.query_documents_by_metadata(
            filters={},
            limit=2,
            offset=2
        )
        
        assert len(results_page1) <= 2
        assert len(results_page2) <= 2
    
    @pytest.mark.asyncio
    async def test_query_documents_no_index(self, test_llamaindex_service):
        test_llamaindex_service.index = None
        
        results = await test_llamaindex_service.query_documents_by_metadata(
            filters={},
            limit=10,
            offset=0
        )
        
        assert results == []