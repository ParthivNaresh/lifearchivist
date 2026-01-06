import asyncio
import logging
import math
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from lifearchivist.server.api.error_formatting import (
    create_error_metadata,
    format_llm_error,
)
from lifearchivist.server.api.prompt_utils import PromptFormatter
from lifearchivist.server.api.routes.conversations.misc_models import (
    EventType,
    StreamConfig,
    StreamContext,
    StreamMetadata,
)
from lifearchivist.server.api.routes.shared.exceptions import ServiceUnavailableError
from lifearchivist.utils.logx import log_event
from lifearchivist.utils.sse import SSEFormatter

from ...config import get_settings
from ...llm import LLMMessage
from ...utils.logx import track
from .base import StreamProcessor

logger = logging.getLogger(__name__)


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

    @track(operation="direct_process")
    async def process(self, context: StreamContext) -> AsyncGenerator[str, None]:
        """Process without RAG service."""
        processing_message_id = None
        try:
            await self._initialize_context(context)
            yield await self._save_user_message(context)

            processing_message_id = await self._create_processing_message(context)
            await self._broadcast_message_status(
                context.conversation_id, processing_message_id, "processing"
            )

            await self._perform_search(context)
            yield SSEFormatter.format_event(EventType.SOURCES, context.sources)

            config = await self._get_stream_config(context)
            messages = self._build_messages(context, config)

            async for event in self._stream_response(context, messages, config):
                yield event

            if processing_message_id:
                await self._finalize_processing_message(
                    processing_message_id, context.accumulated_text or ""
                )
                await self._broadcast_message_status(
                    conversation_id=context.conversation_id,
                    message_id=processing_message_id,
                    status="completed",
                    content=context.accumulated_text,
                )

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            if processing_message_id:
                await self._mark_message_failed(processing_message_id)
                await self._broadcast_message_status(
                    context.conversation_id, processing_message_id, "failed"
                )
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

    async def _create_processing_message(self, context: StreamContext) -> str:
        """Create placeholder message with processing status."""
        msg_service = self.server.service_container.message_service
        result = await msg_service.add_message(
            conversation_id=context.conversation_id,
            role="assistant",
            content="",
            status="processing",
        )

        if result.is_failure():
            raise ValueError("Failed to create processing message")

        message = result.unwrap()
        message_id = str(message["id"])

        # log_event(
        #     "message_processing_started",
        #     {
        #         "message_id": message_id,
        #         "conversation_id": context.conversation_id,
        #     },
        # )

        return message_id

    async def _broadcast_message_status(
        self,
        conversation_id: str,
        message_id: str,
        status: str,
        content: Optional[str] = None,
    ) -> None:
        """Broadcast message status update via WebSocket."""
        if (
            not hasattr(self.server, "websocket_broadcaster")
            or not self.server.websocket_broadcaster
        ):
            return

        await self.server.websocket_broadcaster.broadcast_message_status(
            conversation_id=conversation_id,
            message_id=message_id,
            status=status,
            content=content,
        )

        # log_event(
        #     "message_status_broadcasted",
        #     {
        #         "message_id": message_id,
        #         "conversation_id": conversation_id,
        #         "status": status,
        #     },
        # )

    async def _finalize_processing_message(self, message_id: str, content: str) -> None:
        """Update processing message with final content and completed status."""
        msg_service = self.server.service_container.message_service
        result = await msg_service.update_message_status(
            message_id=message_id,
            status="completed",
            content=content,
        )

        if result.is_failure():
            logger.warning(f"Failed to finalize processing message: {result.error}")
            return

        # log_event(
        #     "message_processing_completed",
        #     {
        #         "message_id": message_id,
        #         "content_length": len(content),
        #     },
        # )

    async def _mark_message_failed(self, message_id: str) -> None:
        """Mark message as failed."""
        msg_service = self.server.service_container.message_service
        result = await msg_service.update_message_status(
            message_id=message_id,
            status="failed",
        )

        if result.is_failure():
            logger.warning(f"Failed to mark message as failed: {result.error}")
            return

        log_event(
            "message_processing_failed",
            {
                "message_id": message_id,
            },
        )

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
            context.accumulated_text = accumulated_text
            async for event in self._handle_timeout(context, config):
                yield event
            return
        except Exception as e:
            context.accumulated_text = accumulated_text
            async for event in self._handle_generation_error(e, context):
                yield event
            return

        context.accumulated_text = accumulated_text
        async for event in self._finalize_response(
            context, accumulated_text, tokens_used, finish_reason
        ):
            yield event

    async def _stream_llm_only(
        self, context: StreamContext, messages: List[LLMMessage], config: StreamConfig
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response chunks only, without saving a new message."""
        provider_manager = self.server.service_container.llm_provider_manager

        accumulated_text = ""

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

        except asyncio.TimeoutError:
            context.accumulated_text = accumulated_text
            async for event in self._handle_timeout(context, config):
                yield event
            return
        except Exception as e:
            context.accumulated_text = accumulated_text
            async for event in self._handle_generation_error(e, context):
                yield event
            return

        context.accumulated_text = accumulated_text

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
