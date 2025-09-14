import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import logging

from lifearchivist.tools.llamaindex.llamaindex_query_tool import LlamaIndexQueryTool


class TestLlamaIndexQueryToolMetadata:
    
    def test_metadata_structure(self):
        tool = LlamaIndexQueryTool()
        metadata = tool._get_metadata()
        
        assert metadata.name == "llamaindex.query"
        assert metadata.async_tool is True
        assert metadata.idempotent is True
        assert "question" in metadata.input_schema["required"]
        assert metadata.input_schema["properties"]["similarity_top_k"]["minimum"] == 1
        assert metadata.input_schema["properties"]["similarity_top_k"]["maximum"] == 20
        assert metadata.input_schema["properties"]["similarity_top_k"]["default"] == 5
        assert metadata.input_schema["properties"]["response_mode"]["default"] == "tree_summarize"
        assert "tree_summarize" in metadata.input_schema["properties"]["response_mode"]["enum"]
        assert "compact" in metadata.input_schema["properties"]["response_mode"]["enum"]
        assert "refine" in metadata.input_schema["properties"]["response_mode"]["enum"]
        assert "simple_summarize" in metadata.input_schema["properties"]["response_mode"]["enum"]


class TestLlamaIndexQueryToolExecute:
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        service = MagicMock()
        service.query = AsyncMock()
        return service
    
    @pytest.fixture
    def query_tool(self, mock_llamaindex_service):
        return LlamaIndexQueryTool(llamaindex_service=mock_llamaindex_service)
    
    @pytest.mark.asyncio
    async def test_execute_empty_question(self, query_tool):
        result = await query_tool.execute(question="")
        
        assert result["answer"] == "I encountered an error: Question cannot be empty"
        assert result["confidence"] == 0.0
        assert result["sources"] == []
        assert result["method"] == "llamaindex_error"
        assert result["metadata"]["error"] == "Question cannot be empty"
    
    @pytest.mark.asyncio
    async def test_execute_whitespace_question(self, query_tool):
        result = await query_tool.execute(question="   ")
        
        assert result["answer"] == "I encountered an error: Question cannot be empty"
        assert result["confidence"] == 0.0
        assert result["sources"] == []
    
    @pytest.mark.asyncio
    async def test_execute_no_service(self):
        tool = LlamaIndexQueryTool(llamaindex_service=None)
        result = await tool.execute(question="What is the meaning of life?")
        
        assert result["answer"] == "I encountered an error: LlamaIndex service not available"
        assert result["confidence"] == 0.0
        assert result["sources"] == []
        assert result["method"] == "llamaindex_error"
    
    @pytest.mark.asyncio
    async def test_execute_successful_query(self, query_tool, mock_llamaindex_service):
        mock_response = {
            "answer": "The document discusses machine learning algorithms.",
            "sources": [
                {
                    "document_id": "doc_123",
                    "title": "ML Guide",
                    "text": "Machine learning is a subset of artificial intelligence...",
                    "score": 0.85,
                    "metadata": {"title": "ML Guide"}
                }
            ],
            "method": "llamaindex_rag",
            "metadata": {"processing_time": 1.5}
        }
        mock_llamaindex_service.query.return_value = mock_response
        
        result = await query_tool.execute(
            question="What is machine learning?",
            similarity_top_k=5,
            response_mode="tree_summarize"
        )
        
        assert result["answer"] == "The document discusses machine learning algorithms."
        assert result["confidence"] > 0.5
        assert len(result["sources"]) == 1
        assert result["sources"][0]["document_id"] == "doc_123"
        assert result["sources"][0]["title"] == "ML Guide"
        assert result["method"] == "llamaindex_rag"
        assert "processing_time" in result["metadata"]
        
        mock_llamaindex_service.query.assert_called_once_with(
            question="What is machine learning?",
            similarity_top_k=5,
            response_mode="tree_summarize"
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_default_parameters(self, query_tool, mock_llamaindex_service):
        mock_llamaindex_service.query.return_value = {
            "answer": "Test answer",
            "sources": [],
            "method": "llamaindex_rag",
            "metadata": {}
        }
        
        await query_tool.execute(question="Test question")
        
        mock_llamaindex_service.query.assert_called_once_with(
            question="Test question",
            similarity_top_k=5,
            response_mode="tree_summarize"
        )
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("response_mode", ["compact", "refine", "simple_summarize"])
    async def test_execute_different_response_modes(self, query_tool, mock_llamaindex_service, response_mode):
        mock_llamaindex_service.query.return_value = {
            "answer": f"Answer using {response_mode}",
            "sources": [],
            "method": "llamaindex_rag",
            "metadata": {}
        }
        
        result = await query_tool.execute(
            question="Test question",
            response_mode=response_mode
        )
        
        assert result["answer"] == f"Answer using {response_mode}"
        mock_llamaindex_service.query.assert_called_with(
            question="Test question",
            similarity_top_k=5,
            response_mode=response_mode
        )
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("similarity_top_k", [1, 10, 20])
    async def test_execute_different_similarity_top_k(self, query_tool, mock_llamaindex_service, similarity_top_k):
        mock_llamaindex_service.query.return_value = {
            "answer": "Test answer",
            "sources": [],
            "method": "llamaindex_rag",
            "metadata": {}
        }
        
        await query_tool.execute(
            question="Test question",
            similarity_top_k=similarity_top_k
        )
        
        mock_llamaindex_service.query.assert_called_with(
            question="Test question",
            similarity_top_k=similarity_top_k,
            response_mode="tree_summarize"
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_multiple_sources(self, query_tool, mock_llamaindex_service):
        mock_response = {
            "answer": "Comprehensive answer from multiple sources",
            "sources": [
                {
                    "document_id": "doc_1",
                    "title": "Source 1",
                    "text": "First source content" * 100,
                    "score": 0.9
                },
                {
                    "document_id": "doc_2",
                    "title": "Source 2",
                    "text": "Second source content",
                    "score": 0.8
                },
                {
                    "document_id": "doc_3",
                    "metadata": {"title": "Source 3"},
                    "text": "Third source content",
                    "score": 0.7
                }
            ],
            "method": "llamaindex_rag",
            "metadata": {}
        }
        mock_llamaindex_service.query.return_value = mock_response
        
        result = await query_tool.execute(question="Complex question")
        
        assert len(result["sources"]) == 3
        assert result["sources"][0]["document_id"] == "doc_1"
        assert result["sources"][0]["title"] == "Source 1"
        assert len(result["sources"][0]["text"]) == 500
        assert result["sources"][1]["score"] == 0.8
        assert result["sources"][2]["title"] == "Source 3"
        assert result["confidence"] > 0.7
    
    @pytest.mark.asyncio
    async def test_execute_exception_handling(self, query_tool, mock_llamaindex_service):
        mock_llamaindex_service.query.side_effect = RuntimeError("Service error")
        
        result = await query_tool.execute(question="Test question")
        
        assert "Query failed: Service error" in result["answer"]
        assert result["confidence"] == 0.0
        assert result["sources"] == []
        assert result["method"] == "llamaindex_error"
        assert result["metadata"]["error"] == "Query failed: Service error"
    
    @pytest.mark.asyncio
    async def test_execute_with_error_in_answer(self, query_tool, mock_llamaindex_service):
        mock_llamaindex_service.query.return_value = {
            "answer": "Error: Unable to process the query",
            "sources": [],
            "method": "llamaindex_rag",
            "metadata": {}
        }
        
        with patch('lifearchivist.tools.llamaindex.llamaindex_query_tool.log_event') as mock_log:
            result = await query_tool.execute(question="Test question")
            
            assert result["answer"] == "Error: Unable to process the query"
            
            warning_logged = any(
                len(call) >= 2 and
                call[0][0] == "query_empty_response" and 
                "level" in call[1] and
                call[1]["level"] == logging.WARNING
                for call in mock_log.call_args_list
            )
            assert warning_logged
    
    @pytest.mark.asyncio
    async def test_execute_with_long_question(self, query_tool, mock_llamaindex_service):
        long_question = "What is " + "very " * 50 + "important?"
        mock_llamaindex_service.query.return_value = {
            "answer": "Answer to long question",
            "sources": [],
            "method": "llamaindex_rag",
            "metadata": {}
        }
        
        with patch('lifearchivist.tools.llamaindex.llamaindex_query_tool.log_event') as mock_log:
            await query_tool.execute(question=long_question)
            
            query_started_logged = any(
                call[0][0] == "query_started" and
                "..." in call[0][1]["question_preview"]
                for call in mock_log.call_args_list
            )
            assert query_started_logged


class TestTransformQueryResult:
    
    @pytest.fixture
    def query_tool(self):
        return LlamaIndexQueryTool()
    
    def test_transform_basic_result(self, query_tool):
        result = {
            "answer": "Test answer",
            "sources": [],
            "method": "test_method",
            "metadata": {"key": "value"}
        }
        
        transformed = query_tool._transform_query_result(result, "Test question")
        
        assert transformed["answer"] == "Test answer"
        assert transformed["confidence"] == 0.5
        assert transformed["sources"] == []
        assert transformed["method"] == "test_method"
        assert transformed["metadata"]["key"] == "value"
        assert transformed["metadata"]["question_length"] == 13
        assert transformed["metadata"]["original_sources_count"] == 0
    
    def test_transform_result_with_sources(self, query_tool):
        result = {
            "answer": "Answer with sources",
            "sources": [
                {
                    "document_id": "doc_1",
                    "title": "Title 1",
                    "text": "Long text content" * 50,
                    "score": 0.9
                },
                {
                    "document_id": "doc_2",
                    "metadata": {"title": "Title from metadata"},
                    "text": "Short text",
                    "score": 0.8
                }
            ],
            "method": "rag",
            "metadata": {}
        }
        
        transformed = query_tool._transform_query_result(result, "Question")
        
        assert len(transformed["sources"]) == 2
        assert transformed["sources"][0]["document_id"] == "doc_1"
        assert transformed["sources"][0]["title"] == "Title 1"
        assert len(transformed["sources"][0]["text"]) == 500
        assert transformed["sources"][0]["score"] == 0.9
        assert transformed["sources"][1]["title"] == "Title from metadata"
        assert transformed["confidence"] > 0.6
    
    def test_transform_result_missing_fields(self, query_tool):
        result = {
            "answer": "Minimal answer"
        }
        
        transformed = query_tool._transform_query_result(result, "Question")
        
        assert transformed["answer"] == "Minimal answer"
        assert transformed["sources"] == []
        assert transformed["method"] == "llamaindex_rag"
        assert transformed["metadata"]["original_sources_count"] == 0
    
    def test_transform_result_with_low_confidence(self, query_tool):
        result = {
            "answer": "Short",
            "sources": [],
            "method": "test",
            "metadata": {}
        }
        
        with patch('lifearchivist.tools.llamaindex.llamaindex_query_tool.log_event') as mock_log:
            transformed = query_tool._transform_query_result(result, "Question")
            
            assert transformed["confidence"] == 0.5
            
            low_confidence_logged = any(
                call[0][0] == "low_confidence_result"
                for call in mock_log.call_args_list
            )
            assert not low_confidence_logged


class TestCalculateConfidence:
    
    @pytest.fixture
    def query_tool(self):
        return LlamaIndexQueryTool()
    
    def test_confidence_empty_answer(self, query_tool):
        confidence = query_tool._calculate_confidence("", [], "Question?")
        assert confidence == 0.0
    
    def test_confidence_no_information_answer(self, query_tool):
        confidence = query_tool._calculate_confidence("I don't know", [], "Question?")
        assert confidence == 0.0
        
        confidence = query_tool._calculate_confidence("No information available", [], "Question?")
        assert confidence == 0.0
    
    def test_confidence_short_answer_no_sources(self, query_tool):
        confidence = query_tool._calculate_confidence("Short answer", [], "Question?")
        assert confidence == 0.5
    
    def test_confidence_long_answer_no_sources(self, query_tool):
        long_answer = "This is a " + "very " * 30 + "long answer"
        confidence = query_tool._calculate_confidence(long_answer, [], "Question?")
        assert confidence == 0.6
        
        very_long_answer = "This is a " + "very " * 100 + "long answer"
        confidence = query_tool._calculate_confidence(very_long_answer, [], "Question?")
        assert confidence == 0.7
    
    def test_confidence_with_sources(self, query_tool):
        sources = [{"score": 0.8}]
        confidence = query_tool._calculate_confidence("Answer", sources, "Question?")
        assert confidence == 0.76
        
        sources = [{"score": 0.9}, {"score": 0.8}, {"score": 0.7}]
        confidence = query_tool._calculate_confidence("Answer", sources, "Question?")
        assert confidence == 0.86
    
    def test_confidence_with_high_scoring_sources(self, query_tool):
        sources = [{"score": 1.0}, {"score": 0.95}, {"score": 0.9}, {"score": 0.85}]
        long_answer = "A" * 400
        confidence = query_tool._calculate_confidence(long_answer, sources, "Question?")
        assert confidence > 0.9
        assert confidence <= 1.0
    
    @pytest.mark.parametrize("error_phrase", [
        "error", "failed", "unable", "cannot", 
        "don't have", "not found", "insufficient"
    ])
    def test_confidence_with_error_phrases(self, query_tool, error_phrase):
        answer = f"The system {error_phrase} to process your request"
        sources = [{"score": 0.8}]
        
        with patch('lifearchivist.tools.llamaindex.llamaindex_query_tool.log_event') as mock_log:
            confidence = query_tool._calculate_confidence(answer, sources, "Question?")
            
            assert confidence < 0.5
            
            error_phrase_logged = any(
                call[0][0] == "confidence_reduced_error_phrases" and
                error_phrase in str(call[0][1]["detected_phrases"])
                for call in mock_log.call_args_list
            )
            assert error_phrase_logged
    
    def test_confidence_multiple_error_phrases(self, query_tool):
        answer = "Error: Unable to process, cannot find the information"
        sources = [{"score": 0.9}, {"score": 0.8}]
        
        confidence = query_tool._calculate_confidence(answer, sources, "Question?")
        assert confidence < 0.5
    
    def test_confidence_clamped_to_range(self, query_tool):
        sources = [{"score": 2.0}] * 10
        answer = "Perfect answer " * 100
        confidence = query_tool._calculate_confidence(answer, sources, "Question?")
        assert confidence == 1.0
        
        answer = "error failed unable cannot insufficient"
        confidence = query_tool._calculate_confidence(answer, [], "Question?")
        assert confidence == 0.2


class TestEmptyResponse:
    
    @pytest.fixture
    def query_tool(self):
        return LlamaIndexQueryTool()
    
    def test_empty_response_structure(self, query_tool):
        response = query_tool._empty_response("Test error")
        
        assert response["answer"] == "I encountered an error: Test error"
        assert response["confidence"] == 0.0
        assert response["sources"] == []
        assert response["method"] == "llamaindex_error"
        assert response["metadata"]["error"] == "Test error"
    
    def test_empty_response_logging(self, query_tool):
        with patch('lifearchivist.tools.llamaindex.llamaindex_query_tool.log_event') as mock_log:
            query_tool._empty_response("Service unavailable")
            
            mock_log.assert_called_once_with(
                "query_empty_response_generated",
                {"reason": "Service unavailable"},
                level=logging.DEBUG
            )


class TestIntegrationScenarios:
    
    @pytest.fixture
    def mock_llamaindex_service(self):
        service = MagicMock()
        service.query = AsyncMock()
        return service
    
    @pytest.fixture
    def query_tool(self, mock_llamaindex_service):
        return LlamaIndexQueryTool(llamaindex_service=mock_llamaindex_service)
    
    @pytest.mark.asyncio
    async def test_high_confidence_scenario(self, query_tool, mock_llamaindex_service):
        mock_llamaindex_service.query.return_value = {
            "answer": "A" * 400,
            "sources": [
                {"document_id": f"doc_{i}", "score": 0.9 - i*0.05, "text": f"Source {i}", "title": f"Title {i}"}
                for i in range(5)
            ],
            "method": "rag",
            "metadata": {}
        }
        
        result = await query_tool.execute(question="Important question?")
        
        assert result["confidence"] > 0.8
        assert len(result["sources"]) == 5
        assert result["method"] == "rag"
    
    @pytest.mark.asyncio
    async def test_low_confidence_scenario(self, query_tool, mock_llamaindex_service):
        mock_llamaindex_service.query.return_value = {
            "answer": "Cannot find information",
            "sources": [],
            "method": "rag",
            "metadata": {}
        }
        
        result = await query_tool.execute(question="Obscure question?")
        
        assert result["confidence"] < 0.3
        assert len(result["sources"]) == 0
    
    @pytest.mark.asyncio
    async def test_source_without_title(self, query_tool, mock_llamaindex_service):
        mock_llamaindex_service.query.return_value = {
            "answer": "Answer",
            "sources": [
                {
                    "document_id": "doc_1",
                    "text": "Source text",
                    "score": 0.8
                }
            ],
            "method": "rag",
            "metadata": {}
        }
        
        result = await query_tool.execute(question="Question?")
        
        assert result["sources"][0]["title"] == "Unknown Document"
        assert result["sources"][0]["document_id"] == "doc_1"
    
    @pytest.mark.asyncio
    async def test_source_with_missing_score(self, query_tool, mock_llamaindex_service):
        mock_llamaindex_service.query.return_value = {
            "answer": "Answer",
            "sources": [
                {
                    "document_id": "doc_1",
                    "title": "Title",
                    "text": "Text"
                }
            ],
            "method": "rag",
            "metadata": {}
        }
        
        result = await query_tool.execute(question="Question?")
        
        assert result["sources"][0]["score"] == 0.0
    
    @pytest.mark.asyncio
    async def test_async_exception_propagation(self, query_tool, mock_llamaindex_service):
        mock_llamaindex_service.query.side_effect = ValueError("Invalid configuration")
        
        result = await query_tool.execute(question="Test question")
        
        assert "Query failed: Invalid configuration" in result["answer"]
        assert result["confidence"] == 0.0
        assert result["method"] == "llamaindex_error"