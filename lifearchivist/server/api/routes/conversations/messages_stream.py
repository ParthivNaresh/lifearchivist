"""
Send message streaming endpoint.
"""

import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Request
from fastapi import Path as PathParam
from fastapi.responses import StreamingResponse

from .....llm.agent.cancellation import CancellationReason, CancellationToken
from .....llm.processors.service import StreamingService
from .....utils.logx import log_event
from ..shared.dependencies import get_server
from .request_models import SendMessageRequest

router = APIRouter()
logger = logging.getLogger(__name__)


async def _stream_with_disconnect_detection(
    service: StreamingService,
    conversation_id: str,
    request_body: SendMessageRequest,
    http_request: Request,
) -> AsyncGenerator[str, None]:
    """
    Wrapper that detects client disconnection and triggers cancellation.

    This is necessary because FastAPI's StreamingResponse doesn't automatically
    propagate client disconnection to nested async generators.
    """
    cancellation_token = CancellationToken()

    async def monitor_disconnect() -> None:
        """Background task to monitor for client disconnection."""
        try:
            while not cancellation_token.is_cancelled:
                if await http_request.is_disconnected():
                    log_event(
                        "client_disconnected",
                        {"conversation_id": conversation_id},
                    )
                    cancellation_token.cancel(
                        CancellationReason.USER_REQUESTED,
                        "Client disconnected",
                    )
                    break
                await asyncio.sleep(0.1)
        except Exception as e:
            log_event(
                "disconnect_monitor_error",
                {"conversation_id": conversation_id, "error": str(e)},
            )

    monitor_task = asyncio.create_task(monitor_disconnect())

    try:
        async for event in service.create_stream_with_token(
            conversation_id, request_body, cancellation_token
        ):
            if cancellation_token.is_cancelled:
                log_event(
                    "stream_cancelled_by_token",
                    {"conversation_id": conversation_id},
                )
                break
            yield event
    except asyncio.CancelledError:
        log_event(
            "stream_cancelled_error",
            {"conversation_id": conversation_id},
        )
        cancellation_token.cancel(
            CancellationReason.USER_REQUESTED,
            "Stream cancelled",
        )
    finally:
        cancellation_token.cancel(
            CancellationReason.USER_REQUESTED,
            "Stream ended",
        )
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


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
    http_request: Request,
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
        _stream_with_disconnect_detection(
            service, conversation_id, request, http_request
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
