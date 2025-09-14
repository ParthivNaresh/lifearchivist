import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from lifearchivist.tools.search.search_tool import IndexSearchTool
from tests.factories.document_factory import DocumentFactory
from tests.factories.file.file_factory import FileFactory


class TestIndexSearchToolMetadata:
    
    def test_metadata_structure(self):
        tool = IndexSearchTool()
        metadata = tool._get_metadata()
        
        assert metadata.name == "index.search"
        assert metadata.async_tool is True
        assert metadata.idempotent is True
        assert "query" in metadata.input_schema["required"]
        assert metadata.input_schema["properties"]["mode"]["enum"] == ["keyword", "semantic", "hybrid"]
        assert metadata.input_schema["properties"]["limit"]["minimum"] == 1
        assert metadata.input_schema["properties"]["limit"]["maximum"] == 100
        assert metadata.input_schema["properties"]["offset"]["minimum"] == 0


class TestIndexSearchToolExecute:
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        service = MagicMock()
        service.retrieve_similar = AsyncMock(return_value=[])
        service.query_documents_by_metadata = AsyncMock(return_value=[])
        return service
    
    @pytest.fixture
    def search_tool(self, mock_llamaindex_service):
        tool = IndexSearchTool(llamaindex_service=mock_llamaindex_service)
        return tool
    
    @pytest.mark.asyncio
    async def test_execute_empty_query(self, search_tool):
        result = await search_tool.execute(query="")
        
        assert result["results"] == []
        assert result["total"] == 0
        assert result["error"] == "Query cannot be empty"
    
    @pytest.mark.asyncio
    async def test_execute_no_service(self):
        tool = IndexSearchTool(llamaindex_service=None)
        result = await tool.execute(query="test query")
        
        assert result["results"] == []
        assert result["total"] == 0
        assert result["error"] == "Search service not available"
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("mode", ["semantic", "keyword", "hybrid"])
    async def test_execute_different_modes(self, search_tool, mock_llamaindex_service, mode):
        test_files = [FileFactory.create_text_file(content=f"Content {i}") for i in range(3)]
        nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        mock_llamaindex_service.retrieve_similar.return_value = nodes
        
        docs = [DocumentFactory.from_test_file(tf) for tf in test_files]
        mock_llamaindex_service.query_documents_by_metadata.return_value = docs
        
        result = await search_tool.execute(query="test query", mode=mode)
        
        assert "results" in result
        assert "total" in result
        assert "query_time_ms" in result
        assert result["query_time_ms"] > 0
    
    @pytest.mark.asyncio
    async def test_execute_with_filters(self, search_tool, mock_llamaindex_service):
        test_file = FileFactory.create_text_file(content="Test content")
        node = DocumentFactory.build_semantic_node_from_test_file(test_file)
        node["metadata"]["mime_type"] = "text/plain"
        node["metadata"]["status"] = "ready"
        mock_llamaindex_service.retrieve_similar.return_value = [node]
        
        filters = {"mime_type": "text/plain", "status": "ready"}
        result = await search_tool.execute(query="test", mode="semantic", filters=filters)
        
        assert len(result["results"]) == 1
        assert result["total"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_with_pagination(self, search_tool, mock_llamaindex_service):
        test_files = [FileFactory.create_text_file(content=f"Content {i}") for i in range(10)]
        nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        mock_llamaindex_service.retrieve_similar.return_value = nodes
        
        result = await search_tool.execute(query="test", mode="semantic", limit=5, offset=2)
        
        assert len(result["results"]) <= 5
        assert "total" in result
    
    @pytest.mark.asyncio
    async def test_execute_include_content(self, search_tool, mock_llamaindex_service):
        test_file = FileFactory.create_text_file(content="Full document content here")
        node = DocumentFactory.build_semantic_node_from_test_file(test_file)
        mock_llamaindex_service.retrieve_similar.return_value = [node]
        
        result = await search_tool.execute(query="test", mode="semantic", include_content=True)
        
        assert len(result["results"]) == 1
        assert "content" in result["results"][0]
        assert result["results"][0]["content"] == "Full document content here"
    
    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, search_tool, mock_llamaindex_service):
        mock_llamaindex_service.retrieve_similar.side_effect = RuntimeError("Service error")
        
        result = await search_tool.execute(query="test", mode="semantic")
        
        assert result["results"] == []
        assert result["total"] == 0
        assert "Search failed" in result["error"]
        assert "Service error" in result["error"]


class TestSemanticSearch:
    
    @pytest.fixture
    def search_tool_with_service(self):
        service = MagicMock()
        service.retrieve_similar = AsyncMock()
        tool = IndexSearchTool(llamaindex_service=service)
        return tool, service
    
    @pytest.mark.asyncio
    async def test_semantic_search_basic(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_files = [FileFactory.create_text_file(content=f"Doc {i}") for i in range(3)]
        nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        service.retrieve_similar.return_value = nodes
        
        result = await tool._semantic_search("query", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) == 3
        assert result["total"] == 3
        assert result["query_time_ms"] > 0
        service.retrieve_similar.assert_called_once_with(
            query="query",
            top_k=20,
            similarity_threshold=0.3
        )
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_filters(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_files = [FileFactory.create_text_file(content=f"Doc {i}") for i in range(5)]
        nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        for i, node in enumerate(nodes):
            node["metadata"]["mime_type"] = "text/plain" if i < 3 else "application/pdf"
        service.retrieve_similar.return_value = nodes
        
        filters = {"mime_type": "text/plain"}
        result = await tool._semantic_search("query", limit=10, offset=0, filters=filters, include_content=False)
        
        assert len(result["results"]) == 3
        assert all(r["mime_type"] == "text/plain" for r in result["results"])
    
    @pytest.mark.asyncio
    async def test_semantic_search_pagination(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_files = [FileFactory.create_text_file(content=f"Doc {i}") for i in range(10)]
        nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        service.retrieve_similar.return_value = nodes
        
        result = await tool._semantic_search("query", limit=3, offset=2, filters={}, include_content=False)
        
        assert len(result["results"]) == 3
        assert result["total"] == 10
    
    @pytest.mark.asyncio
    async def test_semantic_search_limit_handling(self, search_tool_with_service):
        tool, service = search_tool_with_service
        service.retrieve_similar.return_value = []
        
        await tool._semantic_search("query", limit=100, offset=0, filters={}, include_content=False)
        
        service.retrieve_similar.assert_called_once_with(
            query="query",
            top_k=50,
            similarity_threshold=0.3
        )
    
    @pytest.mark.asyncio
    async def test_semantic_search_with_content_inclusion(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_file = FileFactory.create_text_file(content="Document with full content")
        node = DocumentFactory.build_semantic_node_from_test_file(test_file)
        service.retrieve_similar.return_value = [node]
        
        result = await tool._semantic_search("query", limit=10, offset=0, filters={}, include_content=True)
        
        assert len(result["results"]) == 1
        assert result["results"][0]["content"] == "Document with full content"
    
    @pytest.mark.asyncio
    async def test_semantic_search_empty_results(self, search_tool_with_service):
        tool, service = search_tool_with_service
        service.retrieve_similar.return_value = []
        
        result = await tool._semantic_search("query", limit=10, offset=0, filters={}, include_content=False)
        
        assert result["results"] == []
        assert result["total"] == 0
        assert result["query_time_ms"] >= 0
    
    @pytest.mark.asyncio
    async def test_semantic_search_offset_beyond_results(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_files = [FileFactory.create_text_file(content=f"Doc {i}") for i in range(3)]
        nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        service.retrieve_similar.return_value = nodes
        
        result = await tool._semantic_search("query", limit=10, offset=10, filters={}, include_content=False)
        
        assert result["results"] == []
        assert result["total"] == 3
    
    @pytest.mark.asyncio
    async def test_semantic_search_complex_filters(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_files = [FileFactory.create_text_file(content=f"Doc {i}") for i in range(5)]
        nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        for i, node in enumerate(nodes):
            node["metadata"]["mime_type"] = "text/plain" if i < 3 else "application/pdf"
            node["metadata"]["status"] = "ready" if i % 2 == 0 else "processing"
            node["metadata"]["tags"] = ["important"] if i < 2 else ["archive"]
        service.retrieve_similar.return_value = nodes
        
        filters = {
            "mime_type": "text/plain",
            "status": "ready",
            "tags": ["important", "archive"]
        }
        result = await tool._semantic_search("query", limit=10, offset=0, filters=filters, include_content=False)

        assert len(result["results"]) == 2
        assert all(r["mime_type"] == "text/plain" for r in result["results"])
        assert all(r["status"] == "ready" for r in result["results"] if "status" in r)
        for r in result["results"]:
            assert any(tag in ["important", "archive"] for tag in r.get("tags", []))
    
    @pytest.mark.asyncio
    async def test_semantic_search_slow_query_logging(self, search_tool_with_service, monkeypatch):
        tool, service = search_tool_with_service
        test_files = [FileFactory.create_text_file(content=f"Doc {i}") for i in range(3)]
        nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        
        async def slow_retrieve(*args, **kwargs):
            await asyncio.sleep(1.1)
            return nodes
        
        service.retrieve_similar = slow_retrieve
        
        with patch('lifearchivist.tools.search.search_tool.log_event') as mock_log:
            result = await tool._semantic_search("query", limit=10, offset=0, filters={}, include_content=False)
            
            slow_search_logged = any(
                call[0][0] == "slow_semantic_search" 
                for call in mock_log.call_args_list
            )
            assert slow_search_logged


class TestKeywordSearch:
    
    @pytest.fixture
    def search_tool_with_service(self):
        service = MagicMock()
        service.query_documents_by_metadata = AsyncMock()
        tool = IndexSearchTool(llamaindex_service=service)
        return tool, service
    
    @pytest.mark.asyncio
    async def test_keyword_search_basic(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_files = [
            FileFactory.create_text_file(content="apple banana cherry"),
            FileFactory.create_text_file(content="banana cherry date"),
            FileFactory.create_text_file(content="elderberry fig"),
        ]
        docs = [DocumentFactory.from_test_file(tf) for tf in test_files]
        service.query_documents_by_metadata.return_value = docs
        
        result = await tool._keyword_search("banana", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) == 2
        assert result["total"] == 2
        assert all(r["match_type"] == "keyword" for r in result["results"])
    
    @pytest.mark.asyncio
    async def test_keyword_search_multi_word_query(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_files = [
            FileFactory.create_text_file(content="apple banana cherry"),
            FileFactory.create_text_file(content="banana cherry date"),
            FileFactory.create_text_file(content="apple date"),
        ]
        docs = [DocumentFactory.from_test_file(tf) for tf in test_files]
        service.query_documents_by_metadata.return_value = docs
        
        result = await tool._keyword_search("apple banana", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) == 3
        assert result["results"][0]["score"] == 1.0
        assert result["results"][1]["score"] == 0.5
        assert result["results"][2]["score"] == 0.5
    
    @pytest.mark.asyncio
    async def test_keyword_search_no_matches(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_files = [FileFactory.create_text_file(content="apple banana cherry")]
        docs = [DocumentFactory.from_test_file(tf) for tf in test_files]
        service.query_documents_by_metadata.return_value = docs
        
        result = await tool._keyword_search("zebra", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) == 0
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_keyword_search_with_filters(self, search_tool_with_service):
        tool, service = search_tool_with_service
        service.query_documents_by_metadata.return_value = []
        
        filters = {"mime_type": "text/plain", "status": "ready"}
        await tool._keyword_search("test", limit=10, offset=0, filters=filters, include_content=False)
        
        service.query_documents_by_metadata.assert_called_once_with(
            filters=filters,
            limit=200
        )
    
    @pytest.mark.asyncio
    async def test_keyword_search_include_content(self, search_tool_with_service):
        tool, service = search_tool_with_service
        test_file = FileFactory.create_text_file(content="Full content with keyword")
        doc = DocumentFactory.from_test_file(test_file)
        service.query_documents_by_metadata.return_value = [doc]
        
        result = await tool._keyword_search("keyword", limit=10, offset=0, filters={}, include_content=True)
        
        assert len(result["results"]) == 1
        assert result["results"][0]["content"] is not None


class TestHybridSearch:
    
    @pytest.fixture
    def search_tool_with_service(self):
        service = MagicMock()
        service.retrieve_similar = AsyncMock()
        service.query_documents_by_metadata = AsyncMock()
        tool = IndexSearchTool(llamaindex_service=service)
        return tool, service
    
    @pytest.mark.asyncio
    async def test_hybrid_search_combines_results(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        semantic_files = [FileFactory.create_text_file(content=f"Semantic {i}") for i in range(3)]
        semantic_nodes = DocumentFactory.build_semantic_nodes_for_files(semantic_files)
        service.retrieve_similar.return_value = semantic_nodes
        
        keyword_files = [FileFactory.create_text_file(content=f"Keyword {i}") for i in range(2)]
        keyword_docs = [DocumentFactory.from_test_file(tf) for tf in keyword_files]
        service.query_documents_by_metadata.return_value = keyword_docs
        
        result = await tool._hybrid_search("test", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) >= 2
        assert result["total"] >= 2
        assert any(r["match_type"] == "hybrid_semantic" for r in result["results"])
    
    @pytest.mark.asyncio
    async def test_hybrid_search_deduplication(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        test_file = FileFactory.create_text_file(content="Common document")
        test_file.test_id = "doc_common"
        
        semantic_node = DocumentFactory.build_semantic_node_from_test_file(test_file, score=0.8)
        service.retrieve_similar.return_value = [semantic_node]
        
        keyword_doc = DocumentFactory.from_test_file(test_file, document_id="doc_common")
        keyword_doc["text_preview"] = "Common document"
        service.query_documents_by_metadata.return_value = [keyword_doc]
        
        result = await tool._hybrid_search("common", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) == 1
        assert result["results"][0]["match_type"] == "hybrid_both"
        assert result["results"][0]["score"] > 0.8
    
    @pytest.mark.asyncio
    async def test_hybrid_search_score_boosting(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        test_file = FileFactory.create_text_file(content="Test content")
        semantic_node = DocumentFactory.build_semantic_node_from_test_file(test_file, score=0.5)
        service.retrieve_similar.return_value = [semantic_node]
        service.query_documents_by_metadata.return_value = []
        
        result = await tool._hybrid_search("test", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) == 1
        assert result["results"][0]["score"] == 0.5 * 1.2
    
    @pytest.mark.asyncio
    async def test_hybrid_search_parallel_execution(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        async def slow_semantic(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {"results": [], "total": 0, "query_time_ms": 100}
        
        async def slow_keyword(*args, **kwargs):
            await asyncio.sleep(0.1)
            return {"results": [], "total": 0, "query_time_ms": 100}
        
        with patch.object(tool, '_semantic_search', slow_semantic):
            with patch.object(tool, '_keyword_search', slow_keyword):
                import time
                start = time.time()
                await tool._hybrid_search("test", limit=10, offset=0, filters={}, include_content=False)
                elapsed = time.time() - start
                
                assert elapsed < 0.15
    
    @pytest.mark.asyncio
    async def test_hybrid_search_empty_results(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        service.retrieve_similar.return_value = []
        service.query_documents_by_metadata.return_value = []
        
        result = await tool._hybrid_search("test", limit=10, offset=0, filters={}, include_content=False)
        
        assert result["results"] == []
        assert result["total"] == 0
        assert result["query_time_ms"] >= 0
    
    @pytest.mark.asyncio
    async def test_hybrid_search_only_semantic_results(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        test_files = [FileFactory.create_text_file(content=f"Semantic {i}") for i in range(3)]
        semantic_nodes = DocumentFactory.build_semantic_nodes_for_files(test_files)
        service.retrieve_similar.return_value = semantic_nodes
        service.query_documents_by_metadata.return_value = []
        
        result = await tool._hybrid_search("test", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) == 3
        assert all(r["match_type"] == "hybrid_semantic" for r in result["results"])

        original_scores = [0.9, 0.85, 0.8]
        expected_boosted_scores = sorted([s * 1.2 for s in original_scores], reverse=True)
        actual_scores = [r["score"] for r in result["results"]]
        
        for actual, expected in zip(actual_scores, expected_boosted_scores):
            assert abs(actual - expected) < 0.01
    
    @pytest.mark.asyncio
    async def test_hybrid_search_only_keyword_results(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        service.retrieve_similar.return_value = []
        keyword_files = [FileFactory.create_text_file(content=f"Keyword {i}") for i in range(2)]
        keyword_docs = [DocumentFactory.from_test_file(tf) for tf in keyword_files]
        service.query_documents_by_metadata.return_value = keyword_docs
        
        result = await tool._hybrid_search("keyword", limit=10, offset=0, filters={}, include_content=False)
        
        assert len(result["results"]) == 2
        assert all(r["match_type"] == "hybrid_keyword" for r in result["results"])
    
    @pytest.mark.asyncio
    async def test_hybrid_search_with_pagination(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        semantic_files = [FileFactory.create_text_file(content=f"Semantic {i}") for i in range(10)]
        semantic_nodes = DocumentFactory.build_semantic_nodes_for_files(semantic_files)
        service.retrieve_similar.return_value = semantic_nodes
        
        keyword_files = [FileFactory.create_text_file(content=f"Keyword {i}") for i in range(5)]
        keyword_docs = [DocumentFactory.from_test_file(tf) for tf in keyword_files]
        service.query_documents_by_metadata.return_value = keyword_docs
        result = await tool._hybrid_search("test", limit=3, offset=2, filters={}, include_content=False)

        assert len(result["results"]) == 1
        assert result["total"] == 3
    
    @pytest.mark.asyncio
    async def test_hybrid_search_with_filters(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        test_file = FileFactory.create_text_file(content="Filtered content")
        semantic_node = DocumentFactory.build_semantic_node_from_test_file(test_file)
        semantic_node["metadata"]["mime_type"] = "text/plain"
        service.retrieve_similar.return_value = [semantic_node]
        
        keyword_doc = DocumentFactory.from_test_file(test_file)
        keyword_doc["metadata"] = {"mime_type": "text/plain"}
        service.query_documents_by_metadata.return_value = [keyword_doc]
        
        filters = {"mime_type": "text/plain"}
        result = await tool._hybrid_search("test", limit=10, offset=0, filters=filters, include_content=False)
        
        assert len(result["results"]) >= 1
        assert all(r["mime_type"] == "text/plain" for r in result["results"])
    
    @pytest.mark.asyncio
    async def test_hybrid_search_slow_query_logging(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        async def slow_semantic(*args, **kwargs):
            await asyncio.sleep(2.1)
            return {"results": [], "total": 0, "query_time_ms": 2100}
        
        async def slow_keyword(*args, **kwargs):
            await asyncio.sleep(2.1)
            return {"results": [], "total": 0, "query_time_ms": 2100}
        
        with patch.object(tool, '_semantic_search', slow_semantic):
            with patch.object(tool, '_keyword_search', slow_keyword):
                with patch('lifearchivist.tools.search.search_tool.log_event') as mock_log:
                    result = await tool._hybrid_search("test", limit=10, offset=0, filters={}, include_content=False)
                    
                    slow_search_logged = any(
                        call[0][0] == "slow_hybrid_search" 
                        for call in mock_log.call_args_list
                    )
                    assert slow_search_logged
    
    @pytest.mark.asyncio
    async def test_hybrid_search_score_sorting(self, search_tool_with_service):
        tool, service = search_tool_with_service
        
        test_files = [FileFactory.create_text_file(content=f"Doc {i}") for i in range(3)]
        semantic_nodes = DocumentFactory.build_semantic_nodes_for_files(test_files, start_score=0.9, step=0.2)
        service.retrieve_similar.return_value = semantic_nodes
        service.query_documents_by_metadata.return_value = []
        
        result = await tool._hybrid_search("test", limit=10, offset=0, filters={}, include_content=False)
        
        scores = [r["score"] for r in result["results"]]
        assert scores == sorted(scores, reverse=True)


class TestFilterApplication:
    
    @pytest.fixture
    def search_tool(self):
        return IndexSearchTool()
    
    def test_apply_filters_empty_filters(self, search_tool):
        nodes = [{"metadata": {}} for _ in range(3)]
        result = search_tool._apply_filters(nodes, {})
        assert len(result) == 3
    
    def test_apply_filters_mime_type(self, search_tool):
        nodes = [
            {"metadata": {"mime_type": "text/plain"}},
            {"metadata": {"mime_type": "application/pdf"}},
            {"metadata": {"mime_type": "text/plain"}},
        ]
        result = search_tool._apply_filters(nodes, {"mime_type": "text/plain"})
        assert len(result) == 2
    
    def test_apply_filters_status(self, search_tool):
        nodes = [
            {"metadata": {"status": "ready"}},
            {"metadata": {"status": "processing"}},
            {"metadata": {"status": "ready"}},
        ]
        result = search_tool._apply_filters(nodes, {"status": "ready"})
        assert len(result) == 2
    
    def test_apply_filters_tags_any_match(self, search_tool):
        nodes = [
            {"metadata": {"tags": ["medical", "important"]}},
            {"metadata": {"tags": ["financial"]}},
            {"metadata": {"tags": ["medical", "archive"]}},
            {"metadata": {"tags": []}},
        ]
        result = search_tool._apply_filters(nodes, {"tags": ["medical", "financial"]})
        assert len(result) == 3
    
    def test_apply_filters_multiple_criteria(self, search_tool):
        nodes = [
            {"metadata": {"mime_type": "text/plain", "status": "ready", "tags": ["medical"]}},
            {"metadata": {"mime_type": "text/plain", "status": "processing", "tags": ["medical"]}},
            {"metadata": {"mime_type": "application/pdf", "status": "ready", "tags": ["medical"]}},
        ]
        filters = {
            "mime_type": "text/plain",
            "status": "ready",
            "tags": ["medical"]
        }
        result = search_tool._apply_filters(nodes, filters)
        assert len(result) == 1
    
    def test_apply_filters_missing_metadata_fields(self, search_tool):
        nodes = [
            {"metadata": {}},
            {"metadata": {"mime_type": "text/plain"}},
            {"metadata": {"status": "ready"}},
        ]
        result = search_tool._apply_filters(nodes, {"mime_type": "text/plain"})
        assert len(result) == 1


class TestResultConversion:
    
    @pytest.fixture
    def search_tool(self):
        return IndexSearchTool()
    
    def test_convert_nodes_basic(self, search_tool):
        nodes = [
            {
                "text": "Document content here",
                "score": 0.85,
                "metadata": {
                    "document_id": "doc_123",
                    "mime_type": "text/plain",
                    "size_bytes": 1024,
                    "tags": ["test"]
                }
            }
        ]
        
        results = search_tool._convert_nodes_to_search_results(
            nodes, "query", "semantic", include_content=False
        )
        
        assert len(results) == 1
        assert results[0]["document_id"] == "doc_123"
        assert results[0]["score"] == 0.85
        assert results[0]["match_type"] == "semantic"
        assert "content" not in results[0]
    
    def test_convert_nodes_with_content(self, search_tool):
        nodes = [{"text": "Full text", "metadata": {"document_id": "doc_1"}}]
        
        results = search_tool._convert_nodes_to_search_results(
            nodes, "query", "keyword", include_content=True
        )
        
        assert results[0]["content"] == "Full text"
    
    def test_convert_nodes_title_extraction(self, search_tool):
        nodes = [
            {"text": "Content", "metadata": {"original_path": "/path/to/document.txt"}},
            {"text": "Content", "metadata": {"title": "Custom Title"}},
            {"text": "Content", "metadata": {}},
        ]
        
        results = search_tool._convert_nodes_to_search_results(
            nodes, "query", "semantic", include_content=False
        )
        
        assert results[0]["title"] == "document.txt"
        assert results[1]["title"] == "Custom Title"
        assert results[2]["title"] == "Untitled"


class TestSnippetCreation:
    
    @pytest.fixture
    def search_tool(self):
        return IndexSearchTool()
    
    def test_create_snippet_short_text(self, search_tool):
        text = "Short text"
        snippet = search_tool._create_snippet(text, "query", max_length=300)
        assert snippet == "Short text"
    
    def test_create_snippet_long_text_no_query_match(self, search_tool):
        text = "a" * 500
        snippet = search_tool._create_snippet(text, "xyz", max_length=300)
        assert len(snippet) <= 306
        assert snippet.endswith("...")
    
    def test_create_snippet_with_query_match(self, search_tool):
        text = "a" * 100 + " keyword " + "b" * 400
        snippet = search_tool._create_snippet(text, "keyword", max_length=300)
        assert "keyword" in snippet
        assert len(snippet) <= 306
    
    def test_create_snippet_empty_text(self, search_tool):
        snippet = search_tool._create_snippet("", "query", max_length=300)
        assert snippet == ""
    
    @pytest.mark.parametrize("query,expected_in_snippet", [
        ("beginning", True),
        ("middle", True),
        ("end", False),
        ("notfound", False),
    ])
    def test_create_snippet_query_positioning(self, search_tool, query, expected_in_snippet):
        text = "beginning " + "x" * 200 + " middle " + "y" * 200 + " end"
        snippet = search_tool._create_snippet(text, query, max_length=100)
        
        if expected_in_snippet:
            assert query in snippet
        else:
            assert len(snippet) > 0


class TestErrorHandling:
    
    @pytest.fixture
    def search_tool(self):
        service = MagicMock()
        return IndexSearchTool(llamaindex_service=service)
    
    def test_empty_search_result(self, search_tool):
        result = search_tool._empty_search_result("Test error")
        
        assert result["results"] == []
        assert result["total"] == 0
        assert result["query_time_ms"] == 0
        assert result["error"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_semantic_search_exception(self, search_tool):
        search_tool.llamaindex_service.retrieve_similar = AsyncMock(
            side_effect=Exception("Retrieval failed")
        )
        
        with patch.object(search_tool, '_empty_search_result') as mock_empty:
            mock_empty.return_value = {"error": "mocked"}
            
            with pytest.raises(Exception):
                await search_tool._semantic_search("query", 10, 0, {}, False)
    
    @pytest.mark.asyncio
    async def test_keyword_search_exception(self, search_tool):
        search_tool.llamaindex_service.query_documents_by_metadata = AsyncMock(
            side_effect=Exception("Query failed")
        )
        
        with pytest.raises(Exception):
            await search_tool._keyword_search("query", 10, 0, {}, False)