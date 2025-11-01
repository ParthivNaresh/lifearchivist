from contextlib import asynccontextmanager
from typing import Any, Dict, Optional
from unittest.mock import Mock


class MockConversationService:
    def __init__(self):
        self.db_pool = Mock()
        self.db_pool.acquire = self._mock_acquire

    def _mock_acquire(self):
        @asynccontextmanager
        async def mock_connection():
            conn = Mock()
            conn.fetchrow = self._mock_fetchrow
            conn.execute = self._mock_execute
            yield conn

        return mock_connection()

    async def _mock_fetchrow(self, query: str, *args: Any) -> Dict[str, Any]:
        return {
            "temperature": 0.7,
            "max_output_tokens": 2000,
            "response_format": "concise",
            "context_window_size": 10,
            "response_timeout": 30,
        }

    async def _mock_execute(self, query: str, *args: Any) -> None:
        pass

    async def create_conversation(
        self,
        user_id: str,
        title: Optional[str] = None,
        model: Optional[str] = None,
        provider_id: Optional[str] = None,
        context_documents: Optional[list[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = {
            "id": "test_conv_id",
            "title": title or "New Conversation",
            "model": model,
            "provider_id": provider_id,
        }
        return result

    async def list_conversations(
        self,
        user_id: str,
        limit: int,
        offset: int,
        include_archived: bool,
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = {
            "conversations": [],
            "total": 0,
        }
        return result

    async def get_conversation(self, conversation_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = {
            "id": conversation_id,
            "title": "Test Conversation",
            "model": "llama3.2:1b",
        }
        return result

    async def update_conversation(
        self,
        conversation_id: str,
        title: Optional[str] = None,
        model: Optional[str] = None,
        provider_id: Optional[str] = None,
        context_documents: Optional[list[str]] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = {
            "id": conversation_id,
            "title": title or "Updated Conversation",
        }
        return result

    async def archive_conversation(self, conversation_id: str) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = {
            "id": conversation_id,
            "archived_at": "2025-01-06T00:00:00Z",
        }
        return result


class MockMessageService:
    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        model: Optional[str] = None,
        confidence: Optional[float] = None,
        method: Optional[str] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = {
            "id": "test_msg_id",
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
        }
        return result

    async def get_messages(
        self,
        conversation_id: str,
        limit: int,
        offset: int,
        include_citations: bool,
    ) -> Mock:
        result = Mock()
        result.is_failure.return_value = False
        result.unwrap.return_value = {
            "messages": [],
            "total": 0,
        }
        return result

    async def add_citations(
        self, message_id: str, citations: list[Dict[str, Any]]
    ) -> Mock:
        result = Mock()
        result.is_success.return_value = True
        result.unwrap.return_value = citations
        return result
