from typing import Any, AsyncGenerator

from lifearchivist.server.api.routes.conversations.misc_models import (
    EventType,
    StreamContext,
)
from lifearchivist.utils.sse import SSEFormatter

from .base import StreamProcessor


class RAGStreamProcessor(StreamProcessor):
    """Processor for RAG-based streaming."""

    def __init__(self, rag_service: Any, server: Any):
        self.rag_service = rag_service
        self.server = server

    async def process(self, context: StreamContext) -> AsyncGenerator[str, None]:
        """Process using RAG service."""

        config = await self._get_context_config(context)

        async for event in self.rag_service.process_message_with_rag(
            conversation_id=context.conversation_id,
            message_content=context.request.content,
            context_config=config,
            user_id="default",
        ):
            yield self._format_rag_event(event)

    async def _get_context_config(self, context: StreamContext) -> Any:
        """Get context configuration for RAG."""
        from lifearchivist.rag import ContextConfig

        context_window_size = await self._fetch_context_window_size()

        return ContextConfig(
            enable_rag=True,
            similarity_top_k=context.request.context_limit,
            similarity_threshold=0.45,
            max_context_tokens=4000,
            include_metadata=True,
            include_conversation_history=True,
            conversation_history_limit=context_window_size,
        )

    async def _fetch_context_window_size(self) -> int:
        """Fetch context window size from preferences."""
        if not self.server.service_container:
            return 10

        conv_service = self.server.service_container.conversation_service
        if not conv_service:
            return 10

        async with conv_service.db_pool.acquire() as conn:
            prefs = await conn.fetchrow(
                "SELECT context_window_size FROM user_preferences WHERE user_id = 'default'"
            )
            return (
                prefs["context_window_size"]
                if prefs and prefs["context_window_size"]
                else 10
            )

    def _format_rag_event(self, event: Any) -> str:
        """Format RAG event for SSE."""
        from lifearchivist.rag import StreamEventType

        event_dict = event.to_dict()
        event_type = event.type

        mapping = {
            StreamEventType.USER_MESSAGE: EventType.USER_MESSAGE,
            StreamEventType.ASSISTANT_MESSAGE_CREATED: EventType.ASSISTANT_MESSAGE_CREATED,
            StreamEventType.INTENT: EventType.INTENT,
            StreamEventType.CONTEXT: EventType.CONTEXT,
            StreamEventType.SOURCES: EventType.SOURCES,
            StreamEventType.METADATA: EventType.METADATA,
        }

        if event_type in mapping:
            return SSEFormatter.format_event(mapping[event_type], event_dict["data"])
        elif event_type == StreamEventType.TOKEN:
            return SSEFormatter.format_event(
                EventType.CHUNK, {"text": event_dict["data"]}
            )
        elif event_type == StreamEventType.DONE:
            return SSEFormatter.format_event(EventType.COMPLETE, {"status": "done"})
        elif event_type == StreamEventType.ERROR:
            return SSEFormatter.format_event(EventType.ERROR, event_dict["data"])

        return ""
