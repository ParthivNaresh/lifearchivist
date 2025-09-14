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
from tests.factories.file.file_factory import FileFactory
from tests.factories.document_factory import DocumentFactory
from tests.factories.metadata_factory import MetadataFactory


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

    @pytest.mark.asyncio
    async def test_update_metadata_add_documents_exception(self, service_with_documents):
        service_with_documents._persist_index = AsyncMock()
        service_with_documents.index.storage_context.docstore.add_documents.side_effect = Exception("update_failed")
        result = await service_with_documents.update_document_metadata(
            document_id="doc1",
            metadata_updates={"tags": ["x"]},
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


class TestQueryOperations:
    
    @pytest.fixture
    def service_with_query_engine(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            
            mock_query_engine = MagicMock()
            mock_response = MagicMock()
            mock_response.response = "This is the answer to your question"
            mock_response.source_nodes = []
            mock_query_engine.query = MagicMock(return_value=mock_response)
            
            service.query_engine = mock_query_engine
            service.index = MagicMock(spec=VectorStoreIndex)
            
            return service
    
    @pytest.mark.asyncio
    async def test_query_success(self, service_with_query_engine):
        question = "What is the meaning of life?"
        
        result = await service_with_query_engine.query(
            question=question,
            similarity_top_k=5,
            response_mode="tree_summarize"
        )
        
        assert result["answer"] == "This is the answer to your question"
        assert result["method"] == "llamaindex_rag"
        assert result["sources"] == []
        assert result["metadata"]["nodes_used"] == 0
        assert result["metadata"]["response_mode"] == "tree_summarize"
    
    @pytest.mark.asyncio
    async def test_query_with_sources(self, service_with_query_engine):
        mock_node = MagicMock()
        mock_node.node.metadata = {"document_id": "doc1", "title": "Test Doc"}
        mock_node.node.text = "This is the source text"
        mock_node.score = 0.95
        
        service_with_query_engine.query_engine.query.return_value.source_nodes = [mock_node]
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.extract_source_info') as mock_extract:
            mock_extract.return_value = {
                "document_id": "doc1",
                "title": "Test Doc",
                "text_preview": "This is the source...",
                "score": 0.95
            }
            
            result = await service_with_query_engine.query(
                question="Test question",
                similarity_top_k=3
            )
            
            assert len(result["sources"]) == 1
            assert result["sources"][0]["document_id"] == "doc1"
            assert result["metadata"]["nodes_used"] == 1
    
    @pytest.mark.asyncio
    async def test_query_no_engine(self, service_with_query_engine):
        service_with_query_engine.query_engine = None
        
        result = await service_with_query_engine.query(
            question="Test question"
        )
        
        assert "I encountered an error" in result["answer"]
        assert result["confidence"] == 0.0
        assert result["method"] == "llamaindex_error"
        assert "Query engine not available" in result["metadata"]["error"]
    
    @pytest.mark.asyncio
    async def test_query_timeout(self, service_with_query_engine):
        import asyncio
        
        async def slow_query(q):
            await asyncio.sleep(35)
            return MagicMock()
        
        with patch('asyncio.to_thread', side_effect=asyncio.TimeoutError()):
            result = await service_with_query_engine.query(
                question="Test question"
            )
            
            assert "Query timed out" in result["answer"]
            assert result["method"] == "llamaindex_error"
    
    @pytest.mark.asyncio
    async def test_query_attribute_error_usage(self, service_with_query_engine):
        service_with_query_engine.query_engine.query.side_effect = AttributeError("'NoneType' object has no attribute 'usage'")
        
        with pytest.raises(AttributeError):
            await service_with_query_engine.query(
                question="Test question"
            )
    
    @pytest.mark.asyncio
    async def test_query_general_exception(self, service_with_query_engine):
        service_with_query_engine.query_engine.query.side_effect = RuntimeError("Query failed")
        
        with pytest.raises(RuntimeError, match="Query failed"):
            await service_with_query_engine.query(
                question="Test question"
            )


class TestRetrievalOperations:
    
    @pytest.fixture
    def service_with_retriever(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            service.index = MagicMock(spec=VectorStoreIndex)
            return service
    
    @pytest.mark.asyncio
    async def test_retrieve_similar_success(self, service_with_retriever):
        mock_node1 = MagicMock()
        mock_node1.score = 0.9
        mock_node1.node.metadata = {"document_id": "doc1"}
        mock_node1.node.text = "Similar text 1"
        
        mock_node2 = MagicMock()
        mock_node2.score = 0.8
        mock_node2.node.metadata = {"document_id": "doc2"}
        mock_node2.node.text = "Similar text 2"
        
        mock_node3 = MagicMock()
        mock_node3.score = 0.6
        mock_node3.node.metadata = {"document_id": "doc3"}
        mock_node3.node.text = "Less similar text"
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.VectorIndexRetriever') as MockRetriever:
            mock_retriever = MockRetriever.return_value
            mock_retriever.retrieve.return_value = [mock_node1, mock_node2, mock_node3]
            
            with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.extract_source_info') as mock_extract:
                mock_extract.side_effect = [
                    {"document_id": "doc1", "score": 0.9},
                    {"document_id": "doc2", "score": 0.8},
                    None
                ]
                
                results = await service_with_retriever.retrieve_similar(
                    query="Find similar documents",
                    top_k=10,
                    similarity_threshold=0.7
                )
                
                assert len(results) == 2
                assert results[0]["document_id"] == "doc1"
                assert results[1]["document_id"] == "doc2"
    
    @pytest.mark.asyncio
    async def test_retrieve_similar_no_index(self, service_with_retriever):
        service_with_retriever.index = None
        
        results = await service_with_retriever.retrieve_similar(
            query="Test query",
            top_k=5
        )
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_retrieve_similar_exception(self, service_with_retriever):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.VectorIndexRetriever') as MockRetriever:
            MockRetriever.side_effect = Exception("Retrieval failed")
            
            results = await service_with_retriever.retrieve_similar(
                query="Test query"
            )
            
            assert results == []


class TestDocumentAnalysis:
    
    @pytest.fixture
    def service_with_documents(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            
            service.index = MagicMock(spec=VectorStoreIndex)
            service.index.ref_doc_info = {
                "doc1": MagicMock(node_ids=["node1", "node2", "node3"])
            }
            
            mock_docstore = MagicMock()
            mock_node = MagicMock()
            mock_node.text = "This is test content for the document"
            mock_node.metadata = {
                "document_id": "doc1",
                "title": "Test Document",
                "mime_type": "text/plain"
            }
            mock_docstore.get_node.return_value = mock_node
            
            service.index.storage_context.docstore = mock_docstore
            service.index.vector_store = SimpleVectorStore()
            
            return service
    
    @pytest.mark.asyncio
    async def test_get_document_analysis_success(self, service_with_documents):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.return_value = [
                {"text": "Chunk 1 text", "metadata": {"document_id": "doc1"}},
                {"text": "Chunk 2 text", "metadata": {"document_id": "doc1"}},
                {"text": "Chunk 3 text", "metadata": {"document_id": "doc1"}}
            ]
            
            with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.calculate_document_metrics') as mock_metrics:
                mock_metrics.return_value = {
                    "total_chars": 300,
                    "total_words": 50,
                    "avg_chunk_size": 100,
                    "node_count": 3
                }
                
                with patch.object(service_with_documents, '_get_embedding_stats') as mock_stats:
                    mock_stats.return_value = {
                        "model": "all-MiniLM-L6-v2",
                        "dimension": 384
                    }
                    
                    result = await service_with_documents.get_document_analysis("doc1")
                    
                    assert result["document_id"] == "doc1"
                    assert result["status"] == "indexed"
                    assert result["processing_info"]["total_chars"] == 300
                    assert result["processing_info"]["total_words"] == 50
                    assert result["processing_info"]["avg_chunk_size"] == 100
                    assert result["processing_info"]["node_count"] == 3
                    assert result["processing_info"]["embedding_model"] == "all-MiniLM-L6-v2"
                    assert result["processing_info"]["embedding_dimension"] == 384
                    assert len(result["chunks_preview"]) == 3
    
    @pytest.mark.asyncio
    async def test_get_document_analysis_no_index(self, service_with_documents):
        service_with_documents.index = None
        
        result = await service_with_documents.get_document_analysis("doc1")
        
        assert result["error"] == "Index not initialized"
    
    @pytest.mark.asyncio
    async def test_get_document_analysis_not_found(self, service_with_documents):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.return_value = []
            
            result = await service_with_documents.get_document_analysis("nonexistent")
            
            assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_get_document_analysis_exception(self, service_with_documents):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.side_effect = Exception("Analysis failed")
            
            result = await service_with_documents.get_document_analysis("doc1")
            
            assert "Analysis failed" in result["error"]


class TestDocumentChunks:
    
    @pytest.fixture
    def service_with_chunks(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            service.index = MagicMock(spec=VectorStoreIndex)
            return service
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_success(self, service_with_chunks):
        mock_chunks = [
            {
                "node_id": f"node_{i}",
                "text": f"This is chunk {i} with some text content",
                "metadata": {"document_id": "doc1"},
                "start_char": i * 100,
                "end_char": (i + 1) * 100,
                "relationships": {}
            }
            for i in range(5)
        ]
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.return_value = mock_chunks
            
            result = await service_with_chunks.get_document_chunks(
                document_id="doc1",
                limit=3,
                offset=1
            )
            
            assert result["document_id"] == "doc1"
            assert len(result["chunks"]) == 3
            assert result["total"] == 5
            assert result["limit"] == 3
            assert result["offset"] == 1
            assert result["has_more"] is True
            
            first_chunk = result["chunks"][0]
            assert first_chunk["chunk_index"] == 1
            assert first_chunk["node_id"] == "node_1"
            assert "text_length" in first_chunk
            assert "word_count" in first_chunk
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_no_index(self, service_with_chunks):
        service_with_chunks.index = None
        
        result = await service_with_chunks.get_document_chunks("doc1")
        
        assert result["error"] == "Index not initialized"
        assert result["chunks"] == []
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_not_found(self, service_with_chunks):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.return_value = []
            
            result = await service_with_chunks.get_document_chunks("nonexistent")
            
            assert "No chunks found" in result["error"]
            assert result["chunks"] == []
            assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_exception(self, service_with_chunks):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.side_effect = Exception("Chunks retrieval failed")
            
            result = await service_with_chunks.get_document_chunks("doc1")
            
            assert "Chunks retrieval failed" in result["error"]


class TestDocumentNeighbors:
    
    @pytest.fixture
    def service_with_neighbors(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            service.index = MagicMock(spec=VectorStoreIndex)
            return service
    
    @pytest.mark.asyncio
    async def test_get_document_neighbors_success(self, service_with_neighbors):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.return_value = [
                {"text": "Representative text from document", "metadata": {"document_id": "doc1"}}
            ]
            
            mock_node1 = MagicMock()
            mock_node1.score = 0.95
            mock_node1.node.metadata = {"document_id": "doc2"}
            mock_node1.node.text = "Similar document 2 text"
            
            mock_node2 = MagicMock()
            mock_node2.score = 0.85
            mock_node2.node.metadata = {"document_id": "doc1"}
            mock_node2.node.text = "Same document text"
            
            mock_node3 = MagicMock()
            mock_node3.score = 0.80
            mock_node3.node.metadata = {"document_id": "doc3"}
            mock_node3.node.text = "Similar document 3 text"
            
            with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.VectorIndexRetriever') as MockRetriever:
                mock_retriever = MockRetriever.return_value
                mock_retriever.retrieve.return_value = [mock_node1, mock_node2, mock_node3]
                
                with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.generate_text_preview') as mock_preview:
                    mock_preview.side_effect = ["Similar document 2...", "Same document...", "Similar document 3..."]
                    
                    result = await service_with_neighbors.get_document_neighbors(
                        document_id="doc1",
                        top_k=5
                    )
                    
                    assert result["document_id"] == "doc1"
                    assert len(result["neighbors"]) == 2
                    assert result["neighbors"][0]["document_id"] == "doc2"
                    assert result["neighbors"][0]["similarity_score"] == 0.95
                    assert result["neighbors"][1]["document_id"] == "doc3"
                    assert result["total_found"] == 2
    
    @pytest.mark.asyncio
    async def test_get_document_neighbors_no_index(self, service_with_neighbors):
        service_with_neighbors.index = None
        
        result = await service_with_neighbors.get_document_neighbors("doc1")
        
        assert result["error"] == "Index not initialized"
        assert result["neighbors"] == []
    
    @pytest.mark.asyncio
    async def test_get_document_neighbors_no_chunks(self, service_with_neighbors):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.return_value = []
            
            result = await service_with_neighbors.get_document_neighbors("doc1")
            
            assert "No chunks found" in result["error"]
            assert result["neighbors"] == []
    
    @pytest.mark.asyncio
    async def test_get_document_neighbors_no_text(self, service_with_neighbors):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service_utils.NodeProcessor.get_document_nodes_from_ref_doc_info') as mock_get_nodes:
            mock_get_nodes.return_value = [{"text": "", "metadata": {}}]
            
            result = await service_with_neighbors.get_document_neighbors("doc1")
            
            assert result["error"] == "No text content available"
            assert result["neighbors"] == []


class TestIndexPersistence:
    
    @pytest.fixture
    def service_with_persistence(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            service.index = MagicMock(spec=VectorStoreIndex)
            service.index.ref_doc_info = {"doc1": MagicMock()}
            service.index.storage_context.persist = MagicMock()
            return service
    
    @pytest.mark.asyncio
    async def test_persist_index_success(self, service_with_persistence):
        await service_with_persistence._persist_index()
        
        service_with_persistence.index.storage_context.persist.assert_called_once()
        persist_dir = service_with_persistence.index.storage_context.persist.call_args[1]["persist_dir"]
        assert "llamaindex_storage" in persist_dir
    
    @pytest.mark.asyncio
    async def test_persist_index_attribute_error(self, service_with_persistence):
        service_with_persistence.index.storage_context.persist.side_effect = AttributeError("persist method not found")
        
        await service_with_persistence._persist_index()
    
    @pytest.mark.asyncio
    async def test_persist_index_general_exception(self, service_with_persistence):
        service_with_persistence.index.storage_context.persist.side_effect = Exception("Persist failed")
        
        with pytest.raises(Exception, match="Persist failed"):
            await service_with_persistence._persist_index()
    
    @pytest.mark.asyncio
    async def test_persist_index_no_index(self, service_with_persistence):
        service_with_persistence.index = None
        
        await service_with_persistence._persist_index()


class TestDataCleanup:
    
    @pytest.fixture
    def service_with_data(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            service.index = MagicMock(spec=VectorStoreIndex)
            service.index.ref_doc_info = {
                "doc1": MagicMock(),
                "doc2": MagicMock(),
                "doc3": MagicMock()
            }
            service.query_engine = MagicMock()
            return service
    
    @pytest.mark.asyncio
    async def test_clear_all_data_success(self, service_with_data, tmp_path):
        storage_dir = tmp_path / "llamaindex_storage"
        storage_dir.mkdir()
        
        (storage_dir / "index.json").write_text("{}")
        (storage_dir / "docstore.json").write_text("{}")
        (storage_dir / "vector_store.json").write_text("{}")
        
        service_with_data.settings.lifearch_home = tmp_path
        
        with patch.object(service_with_data, '_initialize_empty_index', new_callable=AsyncMock):
            result = await service_with_data.clear_all_data()
            
            assert result["index_reset"] is True
            assert result["storage_files_deleted"] == 3
            assert result["storage_bytes_reclaimed"] > 0
            assert service_with_data.index is None
            assert service_with_data.query_engine is None
            assert not storage_dir.exists()
    
    @pytest.mark.asyncio
    async def test_clear_all_data_no_storage_dir(self, service_with_data, tmp_path):
        service_with_data.settings.lifearch_home = tmp_path
        
        with patch.object(service_with_data, '_initialize_empty_index', new_callable=AsyncMock):
            result = await service_with_data.clear_all_data()
            
            assert result["index_reset"] is True
            assert result["storage_files_deleted"] == 0
            assert result["storage_bytes_reclaimed"] == 0
    
    @pytest.mark.asyncio
    async def test_clear_all_data_exception(self, service_with_data, tmp_path):
        service_with_data.settings.lifearch_home = tmp_path
        
        with patch.object(service_with_data, '_initialize_empty_index', new_callable=AsyncMock) as mock_init:
            mock_init.side_effect = Exception("Init failed")
            
            result = await service_with_data.clear_all_data()
            
            assert result["index_reset"] is True
            assert "Init failed" in result["errors"][0]


class TestEmptyIndexInitialization:
    
    @pytest.fixture
    def service_for_init(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            return service
    
    @pytest.mark.asyncio
    async def test_initialize_empty_index_success(self, service_for_init, tmp_path):
        service_for_init.settings.lifearch_home = tmp_path
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.VectorStoreIndex') as MockIndex:
            mock_index = MockIndex.return_value
            mock_index.storage_context.persist = MagicMock()
            
            with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.VectorIndexRetriever'):
                with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_response_synthesizer'):
                    with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.RetrieverQueryEngine'):
                        await service_for_init._initialize_empty_index()
                        
                        assert service_for_init.index is not None
                        assert service_for_init.query_engine is not None
                        storage_dir = tmp_path / "llamaindex_storage"
                        assert storage_dir.exists()
    
    @pytest.mark.asyncio
    async def test_initialize_empty_index_persist_error(self, service_for_init, tmp_path):
        service_for_init.settings.lifearch_home = tmp_path
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.VectorStoreIndex') as MockIndex:
            mock_index = MockIndex.return_value
            mock_index.storage_context.persist.side_effect = AttributeError("persist not found")
            
            with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.VectorIndexRetriever'):
                with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_response_synthesizer'):
                    with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.RetrieverQueryEngine'):
                        await service_for_init._initialize_empty_index()
                        
                        storage_dir = tmp_path / "llamaindex_storage"
                        assert (storage_dir / "docstore.json").exists()
                        assert (storage_dir / "index_store.json").exists()
    
    @pytest.mark.asyncio
    async def test_initialize_empty_index_exception(self, service_for_init, tmp_path):
        service_for_init.settings.lifearch_home = tmp_path
        
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.VectorStoreIndex') as MockIndex:
            MockIndex.side_effect = Exception("Index creation failed")
            
            with pytest.raises(Exception, match="Index creation failed"):
                await service_for_init._initialize_empty_index()


class TestEmbeddingStats:
    
    @pytest.fixture
    def service_with_settings(self, test_vault, test_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.get_settings', return_value=test_settings):
            service = LlamaIndexService(vault=test_vault)
            return service
    
    def test_get_embedding_stats_success(self, service_with_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.Settings') as MockSettings:
            mock_embed_model = MagicMock()
            mock_embed_model.model_name = "all-MiniLM-L6-v2"
            mock_embed_model.embed_dim = 384
            mock_embed_model._max_length = 512
            MockSettings.embed_model = mock_embed_model
            
            stats = service_with_settings._get_embedding_stats()
            
            assert stats["model"] == "all-MiniLM-L6-v2"
            assert stats["dimension"] == 384
            assert stats["max_length"] == 512
    
    def test_get_embedding_stats_exception(self, service_with_settings):
        with patch('lifearchivist.storage.llamaindex_service.llamaindex_service.Settings') as MockSettings:
            MockSettings.embed_model = None
            
            stats = service_with_settings._get_embedding_stats()
            
            assert stats["model"] == "unknown"
            assert stats["dimension"] is None