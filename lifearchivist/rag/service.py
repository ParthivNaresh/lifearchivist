"""
Conversation RAG service for orchestrating retrieval-augmented generation.

Bridges document retrieval with LLM generation for context-aware responses.
"""

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, AsyncGenerator, Dict, List, Optional, Tuple, cast

from ..llm import LLMProviderManager
from ..llm.base_provider import LLMMessage
from ..storage.database import ConversationService, MessageService
from ..utils.logging import log_event, track
from ..utils.result import Failure, Result, Success
from .prompts import PromptBuilder
from .types import (
    Citation,
    ContextConfig,
    MetadataInfo,
    StreamEvent,
    StreamEventType,
)

if TYPE_CHECKING:
    from ..server.activity_manager import ActivityManager


class ConversationRAGService:
    """
    Orchestrates retrieval-augmented generation for conversations.

    Coordinates between:
    - Document retrieval (QueryService)
    - LLM generation (LLMProviderManager)
    - Conversation persistence (ConversationService, MessageService)
    - Activity tracking (ActivityManager)
    """

    def __init__(
        self,
        search_service: Any,
        provider_manager: LLMProviderManager,
        conversation_service: ConversationService,
        message_service: MessageService,
        activity_manager: Optional["ActivityManager"] = None,
    ):
        """
        Initialize RAG service with dependencies.

        Args:
            search_service: Service for document retrieval (SearchService)
            provider_manager: Manager for LLM providers
            conversation_service: Service for conversation management
            message_service: Service for message persistence
            activity_manager: Optional activity tracking
        """
        self.search_service = search_service
        self.provider_manager = provider_manager
        self.conversation_service = conversation_service
        self.message_service = message_service
        self.activity_manager = activity_manager
        self.prompt_builder = PromptBuilder()

        self._sequence_counter = 0

    def _next_sequence(self) -> int:
        """Get next sequence number for events."""
        self._sequence_counter += 1
        return self._sequence_counter

    async def _validate_and_save_user_message(
        self,
        conversation_id: str,
        message_content: str,
    ) -> Result[Tuple[Dict, StreamEvent], StreamEvent]:
        """
        Validate conversation and save user message.

        Args:
            conversation_id: Conversation identifier
            message_content: User's message

        Returns:
            Result with (conversation, user_message_event) or error event
        """
        conversation_result = await self.conversation_service.get_conversation(
            conversation_id
        )
        if conversation_result.is_failure():
            return Failure(
                StreamEvent.error(
                    "ConversationNotFound",
                    f"Conversation {conversation_id} not found",
                    sequence=self._next_sequence(),
                )
            )

        conversation = conversation_result.unwrap()

        user_msg_result = await self.message_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message_content,
        )

        if user_msg_result.is_failure():
            return Failure(
                StreamEvent.error(
                    "MessageSaveFailed",
                    "Failed to save user message",
                    sequence=self._next_sequence(),
                )
            )

        user_message = user_msg_result.unwrap()
        user_message_event = StreamEvent(
            type=StreamEventType.USER_MESSAGE,
            data=user_message,
            sequence_number=self._next_sequence(),
        )

        return Success((conversation, user_message_event))

    async def _process_context_retrieval(
        self,
        message_content: str,
        config: ContextConfig,
    ) -> Tuple[str, List[Citation], List[StreamEvent]]:
        """
        Process context retrieval and return events.

        Args:
            message_content: User's message
            config: Context configuration

        Returns:
            Tuple of (context_text, citations, events_to_yield)
        """
        events = []

        is_document_query = self._classify_intent(message_content)
        events.append(
            StreamEvent.intent(
                is_document_query=is_document_query,
                requires_context=is_document_query and config.enable_rag,
                sequence=self._next_sequence(),
            )
        )

        citations: List[Citation] = []
        context = ""

        if is_document_query and config.enable_rag:
            context_result = await self._retrieve_context(message_content, config)

            if context_result.is_success():
                log_event("rag_context_unwrapping")
                context, citations = context_result.unwrap()
                log_event(
                    "rag_context_unwrapped",
                    {
                        "context_length": len(context),
                        "citations_count": len(citations),
                    },
                )
                events.append(
                    StreamEvent.context(
                        citations=citations,
                        context_length=len(context),
                        sequence=self._next_sequence(),
                    )
                )
                log_event("rag_context_event_yielded")

                events.append(
                    StreamEvent.sources(
                        citations=citations,
                        sequence=self._next_sequence(),
                    )
                )
                log_event("rag_sources_event_yielded")
            else:
                error_msg = context_result.error_or("Context retrieval failed")
                log_event(
                    "rag_context_retrieval_failed",
                    {"error": error_msg},
                    level=logging.WARNING,
                )

        return context, citations, events

    async def _get_user_preferences(
        self,
        user_id: str,
    ) -> Tuple[Optional[str], int]:
        """
        Get user preferences for response format and timeout.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (response_format, response_timeout)
        """
        response_format = None
        response_timeout = 30

        if self.conversation_service:
            async with self.conversation_service.db_pool.acquire() as conn:
                prefs = await conn.fetchrow(
                    "SELECT response_format, response_timeout FROM user_preferences WHERE user_id = $1",
                    user_id,
                )
                if prefs:
                    response_format = prefs["response_format"]
                    if prefs["response_timeout"]:
                        response_timeout = prefs["response_timeout"]

        return response_format, response_timeout

    async def _stream_llm_response(
        self,
        messages: List[LLMMessage],
        conversation: Dict,
        response_timeout: int,
    ) -> Tuple[str, Optional[int], Optional[float], List[StreamEvent]]:
        """
        Stream LLM response and collect token events.

        Args:
            messages: Messages to send to LLM
            conversation: Conversation dict
            response_timeout: Timeout in seconds

        Returns:
            Tuple of (accumulated_response, tokens_used, cost_usd, events)
        """
        accumulated_response = ""
        tokens_used = None
        cost_usd = None
        events = []

        log_event(
            "rag_llm_generation_starting",
            {
                "model": conversation["model"],
                "provider_id": conversation.get("provider_id"),
                "num_messages": len(messages),
                "timeout_seconds": response_timeout,
            },
        )

        import asyncio

        async with asyncio.timeout(response_timeout):
            async for chunk in self.provider_manager.generate_stream(
                messages=messages,
                model=conversation["model"],
                provider_id=conversation["provider_id"],
                temperature=conversation.get("temperature", 0.7),
                max_tokens=conversation.get("max_tokens", 2000),
            ):
                if chunk.content:
                    accumulated_response += chunk.content
                    events.append(
                        StreamEvent.token(
                            chunk.content,
                            sequence=self._next_sequence(),
                        )
                    )

                if chunk.is_final and chunk.metadata:
                    tokens_used = chunk.metadata.get("tokens_used")
                    cost_usd = chunk.metadata.get("cost_usd")

        return accumulated_response, tokens_used, cost_usd, events

    async def _handle_timeout_error(
        self,
        conversation_id: str,
        conversation: Dict,
        response_timeout: int,
        start_time: float,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Handle timeout error and save error message.

        Args:
            conversation_id: Conversation identifier
            conversation: Conversation dict
            response_timeout: Timeout that was exceeded
            start_time: Request start time

        Yields:
            Error event
        """
        error_message = f"Response generation timed out after {response_timeout} seconds. You can increase the timeout in Advanced Settings."

        log_event(
            "rag_timeout_error",
            {
                "conversation_id": conversation_id,
                "timeout_seconds": response_timeout,
            },
            level=logging.ERROR,
        )

        error_metadata = {
            "is_error": True,
            "error_type": "TimeoutError",
            "provider_id": conversation.get("provider_id", "default"),
            "model": conversation.get("model", "unknown"),
            "retryable": True,
            "raw_error": f"asyncio.TimeoutError: Response generation exceeded {response_timeout}s timeout",
        }

        processing_time_ms = int((time.time() - start_time) * 1000)

        await self.message_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=error_message,
            model=conversation.get("model"),
            confidence=0.0,
            method="error",
            latency_ms=processing_time_ms,
            metadata=error_metadata,
        )

        yield StreamEvent.error(
            error_type="TimeoutError",
            message=error_message,
            sequence=self._next_sequence(),
        )

    async def _handle_general_error(
        self,
        conversation_id: str,
        error: Exception,
        conversation: Optional[Dict],
        start_time: float,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Handle general error and save error message.

        Args:
            conversation_id: Conversation identifier
            error: Exception that occurred
            conversation: Conversation dict (may be None)
            start_time: Request start time

        Yields:
            Error event
        """
        log_event(
            "rag_processing_error",
            {
                "error": str(error),
                "error_type": type(error).__name__,
                "conversation_id": conversation_id,
            },
            level=logging.ERROR,
        )

        error_metadata = {
            "is_error": True,
            "error_type": type(error).__name__,
            "provider_id": (
                conversation.get("provider_id", "default")
                if conversation
                else "default"
            ),
            "model": (
                conversation.get("model", "unknown") if conversation else "unknown"
            ),
            "retryable": False,
            "raw_error": str(error)[:500],
        }

        processing_time_ms = int((time.time() - start_time) * 1000)

        await self.message_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=f"An error occurred: {str(error)}",
            model=conversation.get("model") if conversation else None,
            confidence=0.0,
            method="error",
            latency_ms=processing_time_ms,
            metadata=error_metadata,
        )

        yield StreamEvent.error(
            error_type=type(error).__name__,
            message=str(error),
            sequence=self._next_sequence(),
        )

    def _build_messages_for_llm(
        self,
        message_content: str,
        context: str,
        conversation_history: List[LLMMessage],
        conversation: Dict,
        response_format: Optional[str],
        config: ContextConfig,
    ) -> List[LLMMessage]:
        """
        Build messages for LLM generation.

        Args:
            message_content: User's message
            context: Retrieved context
            conversation_history: Previous messages
            conversation: Conversation dict
            response_format: User's preferred format
            config: Context configuration

        Returns:
            List of messages for LLM
        """
        history = conversation_history if config.include_conversation_history else []

        return self.prompt_builder.build_rag_messages(
            user_query=message_content,
            context=context,
            conversation_history=history,
            system_prompt=conversation.get("system_prompt"),
            response_format=response_format,
        )

    async def _finalize_response(
        self,
        conversation_id: str,
        message_content: str,
        accumulated_response: str,
        citations: List[Citation],
        context: str,
        conversation: Dict,
        start_time: float,
        tokens_used: Optional[int],
        cost_usd: Optional[float],
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Finalize response with metadata and persistence.

        Args:
            conversation_id: Conversation identifier
            message_content: User's message
            accumulated_response: Generated response
            citations: Source citations
            context: Retrieved context
            conversation: Conversation dict
            start_time: Request start time
            tokens_used: Tokens consumed
            cost_usd: Cost in USD

        Yields:
            Metadata and done events
        """
        processing_time_ms = int((time.time() - start_time) * 1000)

        confidence_score = self._calculate_confidence(
            accumulated_response, citations, context
        )

        metadata = MetadataInfo(
            model=conversation["model"],
            provider_id=conversation["provider_id"],
            confidence_score=confidence_score,
            response_mode="rag" if context else "direct",
            num_sources=len(citations),
            context_length=len(context),
            answer_length=len(accumulated_response),
            unique_documents=len({c.document_id for c in citations}),
            processing_time_ms=processing_time_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

        yield StreamEvent.metadata(metadata, sequence=self._next_sequence())

        await self._save_assistant_message(
            conversation_id=conversation_id,
            assistant_response=accumulated_response,
            citations=citations,
            metadata=metadata.to_dict(),
        )

        if self.activity_manager:
            await self._track_activity(
                message_content,
                accumulated_response,
                citations,
                processing_time_ms,
            )

        yield StreamEvent.done(sequence=self._next_sequence())

    @track(
        operation="rag_process_message",
        include_args=["conversation_id"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def process_message_with_rag(
        self,
        conversation_id: str,
        message_content: str,
        context_config: Optional[ContextConfig] = None,
        user_id: str = "default",
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Process a message with RAG pipeline.

        Yields events in order:
        1. Intent classification
        2. Context retrieval (if needed)
        3. Token streaming
        4. Metadata summary
        5. Done signal

        Args:
            conversation_id: Conversation identifier
            message_content: User's message
            context_config: RAG configuration
            user_id: User identifier

        Yields:
            StreamEvent objects for real-time updates
        """
        start_time = time.time()
        config = context_config or ContextConfig()
        conversation = None
        response_timeout = 30

        try:
            validation_result = await self._validate_and_save_user_message(
                conversation_id, message_content
            )

            if validation_result.is_failure():
                failure_result = cast(Failure[StreamEvent], validation_result)
                yield failure_result.error
                return

            conversation, user_message_event = validation_result.unwrap()
            yield user_message_event

            context, citations, context_events = await self._process_context_retrieval(
                message_content, config
            )
            for event in context_events:
                yield event

            log_event(
                "rag_getting_conversation_history",
                {
                    "conversation_id": conversation_id,
                    "limit": config.conversation_history_limit,
                },
            )

            conversation_history = await self._get_conversation_history(
                conversation_id, config.conversation_history_limit
            )

            response_format, response_timeout = await self._get_user_preferences(
                user_id
            )

            log_event(
                "rag_building_messages",
                {
                    "has_context": bool(context),
                    "history_count": len(conversation_history),
                    "has_system_prompt": bool(conversation.get("system_prompt")),
                },
            )

            messages = self._build_messages_for_llm(
                message_content,
                context,
                conversation_history,
                conversation,
                response_format,
                config,
            )

            (
                accumulated_response,
                tokens_used,
                cost_usd,
                token_events,
            ) = await self._stream_llm_response(
                messages, conversation, response_timeout
            )

            for event in token_events:
                yield event

            async for event in self._finalize_response(
                conversation_id,
                message_content,
                accumulated_response,
                citations,
                context,
                conversation,
                start_time,
                tokens_used,
                cost_usd,
            ):
                yield event

        except asyncio.TimeoutError:
            async for event in self._handle_timeout_error(
                conversation_id,
                conversation or {},
                response_timeout,
                start_time,
            ):
                yield event

        except Exception as e:
            async for event in self._handle_general_error(
                conversation_id, e, conversation, start_time
            ):
                yield event

    def _classify_intent(self, query: str) -> bool:
        """
        Classify if query requires document retrieval.

        Args:
            query: User's query

        Returns:
            True if document retrieval needed
        """
        query_lower = query.lower().strip()

        chitchat_patterns = [
            "hi",
            "hello",
            "hey",
            "thanks",
            "thank you",
            "bye",
            "goodbye",
            "how are you",
            "what's up",
        ]

        if query_lower in chitchat_patterns:
            return False

        if len(query.split()) < 3 and "?" not in query:
            return False

        document_keywords = [
            "document",
            "file",
            "show",
            "find",
            "search",
            "what",
            "when",
            "where",
            "who",
            "how",
            "why",
            "tell me",
            "explain",
            "describe",
            "list",
            "summary",
            "based on",
            "according to",
        ]

        return any(keyword in query_lower for keyword in document_keywords)

    async def _retrieve_context(
        self,
        query: str,
        config: ContextConfig,
    ) -> Result[Tuple[str, List[Citation]], str]:
        """
        Retrieve relevant context from documents.

        Args:
            query: User's query
            config: Context configuration

        Returns:
            Result with (context_text, citations) or error
        """
        try:
            search_result = await self.search_service.semantic_search(
                query=query,
                top_k=config.similarity_top_k,
                similarity_threshold=config.similarity_threshold,
                filters=config.filters,
            )

            if search_result.is_failure():
                return cast(Result[Tuple[str, List[Citation]], str], search_result)

            source_chunks = search_result.unwrap()

            context_text = "\n\n".join(
                chunk.get("text", "") for chunk in source_chunks if chunk.get("text")
            )

            log_event(
                "rag_creating_citations",
                {
                    "source_chunks_count": len(source_chunks),
                    "threshold": config.similarity_threshold,
                },
            )

            citations = []
            for i, chunk in enumerate(source_chunks):
                try:
                    score = chunk.get("score", 0)
                    if score >= config.similarity_threshold:
                        log_event(
                            "rag_creating_citation",
                            {
                                "index": i,
                                "score": score,
                                "has_text": bool(chunk.get("text")),
                                "has_document_id": bool(chunk.get("document_id")),
                                "has_node_id": bool(chunk.get("node_id")),
                            },
                        )
                        citation = Citation.from_chunk(chunk)
                        log_event(
                            "rag_citation_created",
                            {
                                "index": i,
                                "citation_document_id": citation.document_id,
                                "citation_chunk_id": citation.chunk_id,
                            },
                        )
                        citations.append(citation)
                        log_event(
                            "rag_citation_appended",
                            {"index": i, "total_citations": len(citations)},
                        )
                except Exception as e:
                    log_event(
                        "rag_citation_creation_failed",
                        {
                            "index": i,
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "chunk_keys": list(chunk.keys()) if chunk else [],
                            "chunk_data": str(chunk)[:500] if chunk else None,
                        },
                        level=logging.ERROR,
                    )
                    raise

            log_event("rag_all_citations_created", {"total": len(citations)})

            if config.rerank and citations:
                log_event("rag_reranking_citations", {"count": len(citations)})
                citations = self._rerank_citations(citations, query)
                log_event("rag_citations_reranked")

            log_event(
                "rag_truncating_context",
                {
                    "original_length": len(context_text),
                    "max_tokens": config.max_context_tokens,
                },
            )
            context_text = self._truncate_context(
                context_text, config.max_context_tokens
            )
            log_event("rag_context_truncated", {"final_length": len(context_text)})

            log_event("rag_returning_success")
            return Success((context_text, citations))

        except Exception as e:
            return Failure(
                error=f"Context retrieval failed: {str(e)}",
                error_type="ContextRetrievalError",
            )

    async def _get_conversation_history(
        self,
        conversation_id: str,
        limit: int,
    ) -> List[LLMMessage]:
        """
        Get recent conversation history.

        Args:
            conversation_id: Conversation identifier
            limit: Number of message pairs to retrieve

        Returns:
            List of previous messages (limit * 2 messages total)
        """
        if limit <= 0:
            return []

        try:
            # Fetch limit * 2 messages to get complete pairs
            messages_result = await self.message_service.get_messages(
                conversation_id=conversation_id,
                limit=limit * 2,
                offset=0,
            )

            if messages_result.is_failure():
                return []

            messages = messages_result.unwrap().get("messages", [])

            # Convert to LLMMessage objects
            llm_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "assistant"
                llm_messages.append(LLMMessage(role=role, content=msg["content"]))

            # Return the most recent pairs (already limited by the query)
            return llm_messages

        except Exception as e:
            log_event(
                "conversation_history_retrieval_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            return []

    def _calculate_confidence(
        self,
        response: str,
        citations: List[Citation],
        context: str,
    ) -> float:
        """
        Calculate confidence score for response.

        Args:
            response: Generated response
            citations: Source citations
            context: Retrieved context

        Returns:
            Confidence score (0-1)
        """
        if not response:
            return 0.0

        base_score = 0.5

        if citations:
            avg_relevance = sum(c.relevance_score for c in citations) / len(citations)
            base_score += avg_relevance * 0.3

        if context and len(response) > len(context) * 0.1:
            base_score += 0.1

        if len(citations) >= 3:
            base_score += 0.1

        return min(base_score, 1.0)

    def _rerank_citations(
        self,
        citations: List[Citation],
        query: str,
    ) -> List[Citation]:
        """
        Rerank citations for better relevance.

        Simple keyword-based reranking for now.
        Could be enhanced with cross-encoder models.

        Args:
            citations: Original citations
            query: User's query

        Returns:
            Reranked citations
        """
        query_terms = set(query.lower().split())

        for citation in citations:
            text_terms = set(citation.text_snippet.lower().split())
            overlap = len(query_terms & text_terms) / len(query_terms)
            citation.confidence = citation.relevance_score * (1 + overlap * 0.5)

        return sorted(citations, key=lambda c: c.confidence, reverse=True)

    def _truncate_context(self, context: str, max_tokens: int) -> str:
        """
        Truncate context to maximum token limit.

        Simple character-based truncation.
        Could be enhanced with proper tokenization.

        Args:
            context: Full context text
            max_tokens: Maximum tokens allowed

        Returns:
            Truncated context
        """
        estimated_chars = max_tokens * 4
        if len(context) > estimated_chars:
            return context[:estimated_chars] + "..."
        return context

    async def _save_assistant_message(
        self,
        conversation_id: str,
        assistant_response: str,
        citations: List[Citation],
        metadata: Dict,
    ) -> None:
        """
        Save assistant message to database.

        Args:
            conversation_id: Conversation identifier
            assistant_response: Generated response
            citations: Source citations
            metadata: Processing metadata
        """
        try:
            metadata_copy = metadata.copy()
            if "citations" in metadata_copy:
                del metadata_copy["citations"]

            result = await self.message_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_response,
                model=metadata.get("model"),
                confidence=metadata.get("confidence_score"),
                method=metadata.get("response_mode"),
                latency_ms=metadata.get("processing_time_ms"),
                metadata=metadata_copy,
            )

            if result.is_failure():
                log_event(
                    "message_save_failed",
                    {"error": str(result.error)},
                    level=logging.ERROR,
                )
                return

            assistant_message = result.unwrap()
            message_id = str(assistant_message["id"])

            if citations:
                citation_dicts = []
                for i, citation in enumerate(citations):
                    citation_dicts.append(
                        {
                            "document_id": citation.document_id,
                            "chunk_id": citation.chunk_id,
                            "score": citation.relevance_score,
                            "snippet": citation.text_snippet[:500],
                            "position": i,
                        }
                    )

                citations_result = await self.message_service.add_citations(
                    message_id=message_id,
                    citations=citation_dicts,
                )

                if citations_result.is_failure():
                    log_event(
                        "citations_save_failed",
                        {
                            "message_id": message_id,
                            "error": str(citations_result.error),
                        },
                        level=logging.WARNING,
                    )

        except Exception as e:
            log_event(
                "message_save_failed",
                {"error": str(e)},
                level=logging.ERROR,
            )

    async def _track_activity(
        self,
        query: str,
        response: str,
        citations: List[Citation],
        processing_time_ms: int,
    ) -> None:
        """
        Track RAG activity event.

        Args:
            query: User's query
            response: Generated response
            citations: Source citations
            processing_time_ms: Processing time
        """
        try:
            if self.activity_manager:
                await self.activity_manager.add_event(
                    event_type="rag_query",
                    data={
                        "query": query[:100],
                        "response_length": len(response),
                        "sources_count": len(citations),
                        "unique_documents": len({c.document_id for c in citations}),
                        "avg_relevance": (
                            sum(c.relevance_score for c in citations) / len(citations)
                            if citations
                            else 0
                        ),
                        "processing_time_ms": processing_time_ms,
                    },
                )
        except Exception as e:
            log_event(
                "activity_tracking_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
