"""
Send message streaming endpoint.
"""

import asyncio
import json
import logging
import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi.responses import StreamingResponse

from lifearchivist.config import get_settings
from lifearchivist.llm import LLMMessage

from ...error_formatting import create_error_metadata, format_llm_error
from ...prompt_utils import PromptFormatter
from ..shared.dependencies import get_server
from ..shared.exceptions import ServiceUnavailableError
from .request_models import SendMessageRequest
from .utils import serialize_for_json

router = APIRouter()
logger = logging.getLogger(__name__)


class EventType(Enum):
    """SSE event types."""

    USER_MESSAGE = "user_message"
    INTENT = "intent"
    CONTEXT = "context"
    SOURCES = "sources"
    CHUNK = "chunk"
    METADATA = "metadata"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StreamContext:
    """Context for streaming operations."""

    conversation_id: str
    request: SendMessageRequest
    start_time: float
    conversation: Optional[Dict[str, Any]] = None
    provider_id: Optional[str] = None
    model: Optional[str] = None
    user_message: Optional[Dict[str, Any]] = None
    sources: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self) -> None:
        if self.sources is None:
            self.sources = []


@dataclass
class StreamConfig:
    """Configuration for streaming."""

    temperature: float = 0.7
    max_tokens: int = 2000
    response_timeout: int = 30
    context_window_size: int = 10
    response_format: Optional[str] = None
    system_prompt: str = (
        "You are a helpful assistant that answers questions based on the provided context."
    )


@dataclass
class StreamMetadata:
    """Metadata for streaming response."""

    confidence_score: float
    method: str
    model: str
    provider_id: Optional[str]
    tokens_used: int
    finish_reason: Optional[str]
    latency_ms: int


class SSEFormatter:
    """Formats data as Server-Sent Events."""

    @staticmethod
    def format_event(event_type: EventType, data: Any) -> str:
        """Format data as SSE event."""
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(serialize_for_json(data))
        else:
            data_str = json.dumps(data)
        return f"event: {event_type.value}\ndata: {data_str}\n\n"

    @staticmethod
    def format_error(error: str, error_type: str) -> str:
        """Format error as SSE event."""
        return SSEFormatter.format_event(
            EventType.ERROR, {"error": error, "error_type": error_type}
        )


class StreamProcessor(ABC):
    """Abstract base class for stream processors."""

    @abstractmethod
    def process(self, context: StreamContext) -> AsyncGenerator[str, None]:
        """Process the stream."""
        ...


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


class DirectStreamProcessor(StreamProcessor):
    """Processor for direct LLM streaming without RAG service."""

    def __init__(self, server: Any):
        self.server = server
        self._validate_services()

    def _validate_services(self) -> None:
        """Validate required services."""
        if not self.server.service_container:
            raise ServiceUnavailableError("Service Container")

        required_services = [
            ("conversation_service", "Conversation Service"),
            ("message_service", "Message Service"),
            ("llamaindex_service", "LlamaIndex Service"),
            ("llm_provider_manager", "LLM Provider Manager"),
        ]

        for attr, name in required_services:
            if not getattr(self.server.service_container, attr, None):
                raise ServiceUnavailableError(name)

    async def process(self, context: StreamContext) -> AsyncGenerator[str, None]:
        """Process without RAG service."""
        try:
            await self._initialize_context(context)
            yield await self._save_user_message(context)

            await self._perform_search(context)
            yield SSEFormatter.format_event(EventType.SOURCES, context.sources)

            config = await self._get_stream_config(context)
            messages = self._build_messages(context, config)

            async for event in self._stream_response(context, messages, config):
                yield event

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            async for event in self._handle_error(e, context):
                yield event

    async def _initialize_context(self, context: StreamContext) -> None:
        """Initialize context with conversation data."""
        conv_service = self.server.service_container.conversation_service
        conv_result = await conv_service.get_conversation(context.conversation_id)

        if conv_result.is_failure():
            raise ValueError("Conversation not found")

        context.conversation = conv_result.unwrap()
        context.provider_id = context.conversation.get("provider_id")
        context.model = context.conversation.get("model") or get_settings().llm_model

    async def _save_user_message(self, context: StreamContext) -> str:
        """Save user message and return SSE event."""
        msg_service = self.server.service_container.message_service
        user_msg_result = await msg_service.add_message(
            conversation_id=context.conversation_id,
            role="user",
            content=context.request.content,
        )

        if user_msg_result.is_failure():
            raise ValueError("Failed to save user message")

        context.user_message = user_msg_result.unwrap()
        return SSEFormatter.format_event(EventType.USER_MESSAGE, context.user_message)

    async def _perform_search(self, context: StreamContext) -> None:
        """Perform semantic search."""
        llamaindex_service = self.server.service_container.llamaindex_service

        if not context.conversation:
            raise ValueError("Conversation not initialized")

        filters = self._build_search_filters(context.conversation)
        search_results = await llamaindex_service.semantic_search(
            query=context.request.content,
            top_k=context.request.context_limit,
            filters=filters,
        )

        context.sources = self._extract_sources(search_results)

    def _build_search_filters(
        self, conversation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Build search filters from conversation."""
        if conversation.get("context_documents"):
            return {"document_id": {"$in": conversation["context_documents"]}}
        return None

    def _extract_sources(self, search_results: List[Any]) -> List[Dict[str, Any]]:
        """Extract source data from search results."""
        return [
            {
                "document_id": result.get("document_id", ""),
                "node_id": result.get("node_id"),
                "score": result.get("score", 0.0),
                "text": result.get("text", ""),
                "metadata": result.get("metadata", {}),
            }
            for result in search_results
        ]

    async def _get_stream_config(self, context: StreamContext) -> StreamConfig:
        """Get streaming configuration."""
        config = StreamConfig()

        if not context.conversation:
            raise ValueError("Conversation not initialized")

        config.system_prompt = (
            context.conversation.get("system_prompt") or config.system_prompt
        )

        await self._load_user_preferences(config, context)
        return config

    async def _load_user_preferences(
        self, config: StreamConfig, context: StreamContext
    ) -> None:
        """Load user preferences into config."""
        conv_service = self.server.service_container.conversation_service
        if not conv_service or not context.conversation:
            return

        async with conv_service.db_pool.acquire() as conn:
            prefs = await conn.fetchrow(
                """SELECT response_format, temperature, max_output_tokens, 
                          response_timeout, context_window_size 
                   FROM user_preferences WHERE user_id = 'default'"""
            )

            if not prefs:
                return

            if prefs["response_format"]:
                config.response_format = prefs["response_format"]

            conv_temp = context.conversation.get("temperature", 0.7)
            if math.isclose(conv_temp, 0.7, rel_tol=1e-09, abs_tol=1e-09):
                config.temperature = prefs["temperature"] or config.temperature
            else:
                config.temperature = conv_temp

            conv_tokens = context.conversation.get("max_tokens", 2000)
            if conv_tokens == 2000:
                config.max_tokens = prefs["max_output_tokens"] or config.max_tokens
            else:
                config.max_tokens = conv_tokens

            if prefs["response_timeout"]:
                config.response_timeout = prefs["response_timeout"]

    def _build_messages(
        self, context: StreamContext, config: StreamConfig
    ) -> List[LLMMessage]:
        """Build LLM messages."""
        system_prompt = PromptFormatter.apply_response_format(
            config.system_prompt, config.response_format
        )

        system_content = self._build_system_content(
            system_prompt, context.sources or []
        )

        return [
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=context.request.content),
        ]

    def _build_system_content(
        self, system_prompt: str, sources: List[Dict[str, Any]]
    ) -> str:
        """Build system content with context."""
        if not sources:
            return system_prompt

        context_text = "\n\n".join(
            f"[Document {i+1}]\n{source.get('text', '')}"
            for i, source in enumerate(sources[:5])
        )
        return f"{system_prompt}\n\nContext:\n{context_text}"

    async def _stream_response(
        self, context: StreamContext, messages: List[LLMMessage], config: StreamConfig
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response."""
        provider_manager = self.server.service_container.llm_provider_manager

        accumulated_text = ""
        tokens_used = 0
        finish_reason = None

        try:
            async with asyncio.timeout(config.response_timeout):
                async for chunk in provider_manager.generate_stream(
                    messages=messages,
                    model=context.model,
                    provider_id=context.provider_id,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                ):
                    accumulated_text += chunk.content
                    yield SSEFormatter.format_event(
                        EventType.CHUNK, {"text": chunk.content}
                    )

                    if chunk.is_final:
                        tokens_used = chunk.tokens_used or 0
                        finish_reason = chunk.finish_reason

        except asyncio.TimeoutError:
            async for event in self._handle_timeout(context, config):
                yield event
            return
        except Exception as e:
            async for event in self._handle_generation_error(e, context):
                yield event
            return

        async for event in self._finalize_response(
            context, accumulated_text, tokens_used, finish_reason
        ):
            yield event

    async def _handle_timeout(
        self, context: StreamContext, config: StreamConfig
    ) -> AsyncGenerator[str, None]:
        """Handle timeout error."""
        latency_ms = int((time.time() - context.start_time) * 1000)
        message = f"Query timeout after {config.response_timeout} seconds. Please try again with a shorter query or increase the timeout in settings."

        await self._save_error_message(context, message, latency_ms)
        yield SSEFormatter.format_error(message, "TimeoutError")

    async def _handle_generation_error(
        self, error: Exception, context: StreamContext
    ) -> AsyncGenerator[str, None]:
        """Handle generation error."""
        latency_ms = int((time.time() - context.start_time) * 1000)
        model = context.model or get_settings().llm_model
        message = format_llm_error(error, model)

        await self._save_error_message(context, message, latency_ms)
        yield SSEFormatter.format_error(message, type(error).__name__)

    async def _save_error_message(
        self, context: StreamContext, message: str, latency_ms: int
    ) -> None:
        """Save error message to database."""
        msg_service = self.server.service_container.message_service
        model = context.model or get_settings().llm_model
        error_metadata = create_error_metadata(
            Exception(message), context.provider_id or "default", model
        )

        await msg_service.add_message(
            conversation_id=context.conversation_id,
            role="assistant",
            content=message,
            model=model,
            confidence=0.0,
            method="error",
            latency_ms=latency_ms,
            metadata=error_metadata,
        )

    async def _finalize_response(
        self,
        context: StreamContext,
        text: str,
        tokens: int,
        finish_reason: Optional[str],
    ) -> AsyncGenerator[str, None]:
        """Finalize and save response."""
        latency_ms = int((time.time() - context.start_time) * 1000)
        model = context.model or get_settings().llm_model

        metadata = StreamMetadata(
            confidence_score=0.8 if context.sources else 0.5,
            method="rag_with_provider" if context.sources else "direct_provider",
            model=model,
            provider_id=context.provider_id,
            tokens_used=tokens,
            finish_reason=finish_reason,
            latency_ms=latency_ms,
        )

        yield SSEFormatter.format_event(EventType.METADATA, metadata.__dict__)

        assistant_message = await self._save_assistant_message(context, text, metadata)

        if context.sources:
            await self._add_citations(assistant_message, context.sources)

        completion_data = {
            "user_message": context.user_message,
            "assistant_message": assistant_message,
            "latency_ms": latency_ms,
        }
        yield SSEFormatter.format_event(EventType.COMPLETE, completion_data)

    async def _save_assistant_message(
        self, context: StreamContext, text: str, metadata: StreamMetadata
    ) -> Dict[str, Any]:
        """Save assistant message."""
        msg_service = self.server.service_container.message_service

        result = await msg_service.add_message(
            conversation_id=context.conversation_id,
            role="assistant",
            content=text,
            model=metadata.model,
            confidence=metadata.confidence_score,
            method=metadata.method,
            latency_ms=metadata.latency_ms,
        )

        if result.is_failure():
            raise ValueError("Failed to save assistant message")

        message_dict: Dict[str, Any] = result.unwrap()
        return message_dict

    async def _add_citations(
        self, message: Dict[str, Any], sources: List[Dict[str, Any]]
    ) -> None:
        """Add citations to message."""
        msg_service = self.server.service_container.message_service

        citations = [
            {
                "document_id": source.get("document_id", ""),
                "chunk_id": source.get("node_id"),
                "score": source.get("score"),
                "snippet": source.get("text", "")[:500],
                "position": i,
            }
            for i, source in enumerate(sources)
        ]

        result = await msg_service.add_citations(
            message_id=str(message["id"]),
            citations=citations,
        )

        if result.is_success():
            message["citations"] = result.unwrap()

    async def _handle_error(
        self, error: Exception, context: StreamContext
    ) -> AsyncGenerator[str, None]:
        """Handle general errors."""
        try:
            latency_ms = int((time.time() - context.start_time) * 1000)
            message = format_llm_error(error, context.model or get_settings().llm_model)

            await self._save_error_message(context, message, latency_ms)
            yield SSEFormatter.format_error(str(error), type(error).__name__)
        except Exception as save_error:
            logger.error(f"Failed to save error message: {save_error}", exc_info=True)
            yield SSEFormatter.format_error(str(error), type(error).__name__)


class StreamingService:
    """Main service for handling streaming."""

    def __init__(self, server: Any):
        self.server = server
        self._validate_base_services()

    def _validate_base_services(self) -> None:
        """Validate base services are available."""
        if not self.server.service_container:
            raise ServiceUnavailableError("Service Container")

    async def create_stream(
        self, conversation_id: str, request: SendMessageRequest
    ) -> AsyncGenerator[str, None]:
        """Create and process stream."""
        context = StreamContext(
            conversation_id=conversation_id,
            request=request,
            start_time=time.time(),
        )

        processor = self._get_processor()
        async for event in processor.process(context):
            yield event

    def _get_processor(self) -> StreamProcessor:
        """Get appropriate stream processor."""
        if self.server.service_container and self.server.service_container.rag_service:
            return RAGStreamProcessor(
                self.server.service_container.rag_service, self.server
            )
        return DirectStreamProcessor(self.server)


@router.post(
    "/{conversation_id}/messages/stream",
    responses={
        200: {
            "description": "Server-Sent Events stream",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
        503: {
            "description": "Required service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Service container not available"}
                }
            },
        },
    },
)
async def send_message_streaming(
    request: SendMessageRequest,
    conversation_id: str = PathParam(..., description="Unique conversation identifier"),
) -> StreamingResponse:
    """
    Send a message and stream AI response using Server-Sent Events (SSE).

    Processes user message through RAG pipeline and streams response token-by-token.
    Returns SSE stream with multiple event types for real-time updates.

    ## Path Parameters

    - **conversation_id**: Unique identifier of the conversation

    ## Request Body

    - **content**: User message content
    - **context_limit**: Max context documents to retrieve (optional)

    ## SSE Event Types

    - **user_message**: User message saved
    - **intent**: Query classification (RAG service only)
    - **context**: Retrieved document context (RAG service only)
    - **sources**: Retrieved document chunks
    - **chunk**: Individual response tokens
    - **metadata**: Final statistics
    - **complete**: Processing complete with full messages
    - **error**: Any errors encountered

    ## Example SSE Stream

    ```
    event: user_message
    data: {"id": "msg_1", "content": "Hello", ...}

    event: sources
    data: [{"document_id": "doc_123", "score": 0.85, ...}]

    event: chunk
    data: {"text": "Based"}

    event: chunk
    data: {"text": " on"}

    event: metadata
    data: {"confidence_score": 0.8, "tokens_used": 150, ...}

    event: complete
    data: {"user_message": {...}, "assistant_message": {...}, "latency_ms": 1500}
    ```

    ## Processing Pipeline

    1. **Save User Message**: Store in database
    2. **Semantic Search**: Retrieve relevant context
    3. **Stream Sources**: Send retrieved documents
    4. **Generate Stream**: Stream AI response tokens
    5. **Save Assistant Message**: Store complete response
    6. **Add Citations**: Link to source documents
    7. **Send Complete**: Final message data

    ## RAG Service Integration

    If RAG service available, uses enhanced pipeline with:
    - Intent classification
    - Context retrieval
    - Conversation history
    - Advanced streaming

    ## Fallback Mode

    Without RAG service, uses direct LlamaIndex:
    - Semantic search for context
    - Direct LLM streaming
    - Citation tracking

    ## Error Handling

    - Errors sent as SSE error events
    - Error messages saved to database
    - User-friendly error formatting
    - Timeout handling (default 30s)

    ## Performance Notes

    - Streams tokens as generated
    - Low latency for first token
    - Efficient memory usage
    - Timeout configurable per user

    ## Notes

    - Returns StreamingResponse with text/event-stream
    - Connection kept alive during streaming
    - No caching headers set
    - Buffering disabled for real-time delivery
    """
    server = get_server()
    service = StreamingService(server)

    return StreamingResponse(
        service.create_stream(conversation_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
