from typing import Any, Dict, Optional
from unittest.mock import Mock


class MockSearchService:
    async def semantic_search(
        self, query: str, top_k: int, similarity_threshold: float, filters: Dict[str, Any]
    ) -> Mock:
        return self._create_search_result(0.95)

    async def keyword_search(
        self, query: str, top_k: int, filters: Dict[str, Any]
    ) -> Mock:
        return self._create_search_result(0.85)

    async def hybrid_search(
        self, query: str, top_k: int, semantic_weight: float, filters: Dict[str, Any]
    ) -> Mock:
        return self._create_search_result(0.90)

    @staticmethod
    def _create_search_result(score: float) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.value = [
            {
                "document_id": "doc1",
                "score": score,
                "text": "Sample result",
                "metadata": {"title": "Test Doc"},
            }
        ]
        return result


class MockQueryService:
    async def query(
        self,
        question: str,
        similarity_top_k: int,
        response_mode: str,
        filters: Optional[Dict[str, Any]],
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.value = {
            "answer": "This is a test answer",
            "sources": [
                {
                    "document_id": "doc1",
                    "text": "Source text snippet",
                    "score": 0.95,
                    "metadata": {"title": "Test Document"},
                }
            ],
            "confidence_score": 0.85,
            "method": "llamaindex_rag",
            "statistics": {"tokens_used": 150},
        }
        return result


class MockLlamaIndexService:
    def __init__(self):
        self.search_service = MockSearchService()
        self.query_service = MockQueryService()

    async def query_documents_by_metadata(
        self, filters: Dict[str, Any], limit: int, offset: int = 0
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.is_success.return_value = True
        result.value = []
        result.unwrap.return_value = []
        return result

    async def delete_document(self, document_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.value = {"deleted": True, "document_id": document_id}
        return result

    async def update_document_metadata(
        self, document_id: str, metadata_updates: Dict[str, Any], merge_mode: str
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.value = {"updated": True, "document_id": document_id}
        return result

    async def clear_all_data(self) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.value = {"storage_files_deleted": 0, "storage_bytes_reclaimed": 0, "errors": []}
        return result

    async def get_document_analysis(self, document_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.value = {"document_id": document_id, "chunks": 0}
        return result

    async def get_document_chunks(
        self, document_id: str, limit: int, offset: int
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.value = {"chunks": [], "total": 0}
        return result

    async def get_document_neighbors(self, document_id: str, top_k: int) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.value = {"neighbors": []}
        return result
