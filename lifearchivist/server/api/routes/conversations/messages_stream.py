"""
Send message streaming endpoint.
"""

import asyncio
import json
import logging
import time
from typing import AsyncGenerator, List

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

    if not server.service_container:
        raise ServiceUnavailableError("Service Container")

    if not server.service_container.conversation_service:
        raise ServiceUnavailableError("Conversation Service")

    if not server.service_container.message_service:
        raise ServiceUnavailableError("Message Service")

    if not server.service_container.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex Service")

    if not server.service_container.rag_service:
        raise ServiceUnavailableError("Conversation RAG Service")

    rag_service = server.service_container.rag_service

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for streaming response."""
        if rag_service:
            from lifearchivist.rag import ContextConfig, StreamEventType

            context_window_size = 10
            if (
                server.service_container
                and server.service_container.conversation_service
            ):
                db_pool = server.service_container.conversation_service.db_pool
                async with db_pool.acquire() as conn:
                    prefs = await conn.fetchrow(
                        "SELECT context_window_size FROM user_preferences WHERE user_id = 'default'"
                    )
                    if prefs and prefs["context_window_size"]:
                        context_window_size = prefs["context_window_size"]

            context_config = ContextConfig(
                enable_rag=True,
                similarity_top_k=request.context_limit,
                similarity_threshold=0.45,
                max_context_tokens=4000,
                include_metadata=True,
                include_conversation_history=True,
                conversation_history_limit=context_window_size,
            )

            async for event in rag_service.process_message_with_rag(
                conversation_id=conversation_id,
                message_content=request.content,
                context_config=context_config,
                user_id="default",
            ):
                event_dict = event.to_dict()
                event_type = event.type

                if event_type == StreamEventType.USER_MESSAGE:
                    yield f"event: user_message\ndata: {json.dumps(serialize_for_json(event_dict['data']))}\n\n"
                elif event_type == StreamEventType.INTENT:
                    yield f"event: intent\ndata: {json.dumps(event_dict['data'])}\n\n"
                elif event_type == StreamEventType.CONTEXT:
                    yield f"event: context\ndata: {json.dumps(event_dict['data'])}\n\n"
                elif event_type == StreamEventType.SOURCES:
                    yield f"event: sources\ndata: {json.dumps(event_dict['data'])}\n\n"
                elif event_type == StreamEventType.TOKEN:
                    yield f"event: chunk\ndata: {json.dumps({'text': event_dict['data']})}\n\n"
                elif event_type == StreamEventType.METADATA:
                    yield f"event: metadata\ndata: {json.dumps(event_dict['data'])}\n\n"
                elif event_type == StreamEventType.DONE:
                    yield f"event: complete\ndata: {json.dumps({'status': 'done'})}\n\n"
                elif event_type == StreamEventType.ERROR:
                    yield f"event: error\ndata: {json.dumps(event_dict['data'])}\n\n"

            return

        assert server.service_container

        conv_service = server.service_container.conversation_service
        msg_service = server.service_container.message_service
        llamaindex_service = server.service_container.llamaindex_service

        if not conv_service or not msg_service:
            yield f"event: error\ndata: {json.dumps({'error': 'Message service not available', 'error_type': 'ServiceUnavailable'})}\n\n"
            return

        if not llamaindex_service:
            yield f"event: error\ndata: {json.dumps({'error': 'LlamaIndex service not available', 'error_type': 'ServiceUnavailable'})}\n\n"
            return

        start_time = time.time()
        conversation = None
        provider_id = None
        model = None

        try:
            conv_result = await conv_service.get_conversation(conversation_id)
            if conv_result.is_failure():
                yield f"event: error\ndata: {json.dumps({'error': 'Conversation not found', 'error_type': 'NotFound'})}\n\n"
                return

            conversation = conv_result.unwrap()
            provider_id = conversation.get("provider_id")
            model = conversation.get("model") or get_settings().llm_model

            user_msg_result = await msg_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.content,
            )

            if user_msg_result.is_failure():
                yield f"event: error\ndata: {json.dumps({'error': 'Failed to save user message', 'error_type': 'DatabaseError'})}\n\n"
                return

            user_message = user_msg_result.unwrap()

            yield f"event: user_message\ndata: {json.dumps(serialize_for_json(user_message))}\n\n"

            filters = None
            if conversation.get("context_documents"):
                filters = {"document_id": {"$in": conversation["context_documents"]}}

            search_results = await llamaindex_service.semantic_search(
                query=request.content,
                top_k=request.context_limit,
                filters=filters,
            )

            sources_data = []
            for result in search_results:
                sources_data.append(
                    {
                        "document_id": result.get("document_id", ""),
                        "node_id": result.get("node_id"),
                        "score": result.get("score", 0.0),
                        "text": result.get("text", ""),
                        "metadata": result.get("metadata", {}),
                    }
                )

            yield f"event: sources\ndata: {json.dumps(sources_data)}\n\n"

            messages: List[LLMMessage] = []

            response_format = None
            if (
                server.service_container
                and server.service_container.conversation_service
            ):
                db_pool = server.service_container.conversation_service.db_pool
                async with db_pool.acquire() as conn:
                    prefs = await conn.fetchrow(
                        "SELECT response_format FROM user_preferences WHERE user_id = 'default'"
                    )
                    if prefs:
                        response_format = prefs["response_format"]

            base_system_prompt = (
                conversation.get("system_prompt")
                or "You are a helpful assistant that answers questions based on the provided context."
            )

            system_prompt = PromptFormatter.apply_response_format(
                base_system_prompt, response_format
            )

            if sources_data:
                context_text = "\n\n".join(
                    [
                        f"[Document {i+1}]\n{source.get('text', '')}"
                        for i, source in enumerate(sources_data[:5])
                    ]
                )
                system_content = f"{system_prompt}\n\nContext:\n{context_text}"
            else:
                system_content = system_prompt

            messages.append(LLMMessage(role="system", content=system_content))
            messages.append(LLMMessage(role="user", content=request.content))

            if (
                not server.service_container
                or not server.service_container.llm_provider_manager
            ):
                yield f"event: error\ndata: {json.dumps({'error': 'LLM provider manager not available', 'error_type': 'ServiceUnavailable'})}\n\n"
                return

            provider_manager = server.service_container.llm_provider_manager

            temperature = conversation.get("temperature", 0.7)
            max_tokens = conversation.get("max_tokens", 2000)

            if temperature == 0.7 or max_tokens == 2000:
                if (
                    server.service_container
                    and server.service_container.conversation_service
                ):
                    db_pool = server.service_container.conversation_service.db_pool
                    async with db_pool.acquire() as conn:
                        prefs = await conn.fetchrow(
                            "SELECT temperature, max_output_tokens FROM user_preferences WHERE user_id = 'default'"
                        )
                        if prefs:
                            if temperature == 0.7:
                                temperature = prefs["temperature"]
                            if max_tokens == 2000:
                                max_tokens = prefs["max_output_tokens"]

            response_timeout = 30
            if (
                server.service_container
                and server.service_container.conversation_service
            ):
                db_pool = server.service_container.conversation_service.db_pool
                async with db_pool.acquire() as conn:
                    timeout_prefs = await conn.fetchrow(
                        "SELECT response_timeout FROM user_preferences WHERE user_id = 'default'"
                    )
                    if timeout_prefs and timeout_prefs["response_timeout"]:
                        response_timeout = timeout_prefs["response_timeout"]

            accumulated_text = ""
            tokens_used = 0
            finish_reason = None

            try:
                async with asyncio.timeout(response_timeout):
                    async for chunk in provider_manager.generate_stream(
                        messages=messages,
                        model=model,
                        provider_id=provider_id,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ):
                        accumulated_text += chunk.content

                        yield f"event: chunk\ndata: {json.dumps({'text': chunk.content})}\n\n"

                        if chunk.is_final:
                            tokens_used = chunk.tokens_used or 0
                            finish_reason = chunk.finish_reason

            except asyncio.TimeoutError as e:
                latency_ms = int((time.time() - start_time) * 1000)
                user_friendly_message = f"Query timeout after {response_timeout} seconds. Please try again with a shorter query or increase the timeout in settings."
                error_metadata = create_error_metadata(
                    e, provider_id or "default", model
                )

                await msg_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=user_friendly_message,
                    model=model,
                    confidence=0.0,
                    method="error",
                    latency_ms=latency_ms,
                    metadata=error_metadata,
                )

                yield f"event: error\ndata: {json.dumps({'error': user_friendly_message, 'error_type': 'TimeoutError'})}\n\n"
                return
            except Exception as e:
                latency_ms = int((time.time() - start_time) * 1000)
                user_friendly_message = format_llm_error(e, model)
                error_metadata = create_error_metadata(
                    e, provider_id or "default", model
                )

                await msg_service.add_message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=user_friendly_message,
                    model=model,
                    confidence=0.0,
                    method="error",
                    latency_ms=latency_ms,
                    metadata=error_metadata,
                )

                yield f"event: error\ndata: {json.dumps({'error': user_friendly_message, 'error_type': type(e).__name__})}\n\n"
                return

            latency_ms = int((time.time() - start_time) * 1000)

            metadata_info = {
                "confidence_score": 0.8 if sources_data else 0.5,
                "method": "rag_with_provider" if sources_data else "direct_provider",
                "model": model,
                "provider_id": provider_id,
                "tokens_used": tokens_used,
                "finish_reason": finish_reason,
            }
            yield f"event: metadata\ndata: {json.dumps(metadata_info)}\n\n"

            confidence = metadata_info["confidence_score"]
            method = metadata_info["method"]

            assistant_msg_result = await msg_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=accumulated_text,
                model=model,
                confidence=confidence,
                method=method,
                latency_ms=latency_ms,
            )

            if assistant_msg_result.is_failure():
                yield f"event: error\ndata: {json.dumps({'error': 'Failed to save assistant message', 'error_type': 'DatabaseError'})}\n\n"
                return

            assistant_message = assistant_msg_result.unwrap()

            if sources_data:
                citations = []
                for i, source in enumerate(sources_data):
                    citations.append(
                        {
                            "document_id": source.get("document_id", ""),
                            "chunk_id": source.get("node_id"),
                            "score": source.get("score"),
                            "snippet": source.get("text", "")[:500],
                            "position": i,
                        }
                    )

                citation_result = await msg_service.add_citations(
                    message_id=str(assistant_message["id"]),
                    citations=citations,
                )

                if citation_result.is_success():
                    assistant_message["citations"] = citation_result.unwrap()

            completion_data = serialize_for_json(
                {
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "latency_ms": latency_ms,
                }
            )
            yield f"event: complete\ndata: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)

            try:
                latency_ms = int((time.time() - start_time) * 1000)
                final_provider_id = provider_id or "default"
                final_model = model or get_settings().llm_model
                user_friendly_message = format_llm_error(e, final_model)
                error_metadata = create_error_metadata(
                    e, final_provider_id, final_model
                )

                if msg_service:
                    await msg_service.add_message(
                        conversation_id=conversation_id,
                        role="assistant",
                        content=user_friendly_message,
                        model=final_model,
                        confidence=0.0,
                        method="error",
                        latency_ms=latency_ms,
                        metadata=error_metadata,
                    )
            except Exception as save_error:
                logger.error(
                    f"Failed to save error message: {save_error}", exc_info=True
                )

            yield f"event: error\ndata: {json.dumps({'error': str(e), 'error_type': type(e).__name__})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
