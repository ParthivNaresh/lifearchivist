"""
Send message streaming endpoint.
"""

import logging

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi.responses import StreamingResponse

from .....llm.processors.service import StreamingService
from ..shared.dependencies import get_server
from .request_models import SendMessageRequest

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
