"""
Conversation API routes.

Provides REST endpoints for conversation management:
- Create conversations
- List conversations
- Get conversation details
- Update conversations
- Archive conversations
- Send messages (standard and streaming)
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from lifearchivist.config import get_settings

from ..dependencies import get_server

router = APIRouter(prefix="/api", tags=["conversations"])


def serialize_for_json(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable types.

    Handles:
    - UUID -> str
    - datetime -> ISO format str
    - dict -> recursively serialize values
    - list -> recursively serialize items
    """
    if isinstance(obj, UUID):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    else:
        return obj


class CreateConversationRequest(BaseModel):
    """Request model for creating a conversation."""

    title: Optional[str] = Field(None, description="Conversation title")
    model: Optional[str] = Field(
        None, description="LLM model to use (defaults to current settings)"
    )
    context_documents: Optional[List[str]] = Field(
        None, description="Document IDs for context"
    )
    system_prompt: Optional[str] = Field(None, description="Custom system prompt")
    temperature: float = Field(default=0.7, ge=0, le=2, description="LLM temperature")
    max_tokens: int = Field(
        default=2000, ge=1, le=100000, description="Max tokens per response"
    )


class UpdateConversationRequest(BaseModel):
    """Request model for updating a conversation."""

    title: Optional[str] = Field(None, description="New title")
    context_documents: Optional[List[str]] = Field(
        None, description="New context documents"
    )
    system_prompt: Optional[str] = Field(None, description="New system prompt")
    temperature: Optional[float] = Field(
        None, ge=0, le=2, description="New temperature"
    )
    max_tokens: Optional[int] = Field(
        None, ge=1, le=100000, description="New max tokens"
    )


class SendMessageRequest(BaseModel):
    """Request model for sending a message."""

    content: str = Field(..., description="Message content (user question)")
    context_limit: int = Field(
        default=5, ge=1, le=20, description="Number of context documents to use"
    )


@router.post("/conversations")
async def create_conversation(request: CreateConversationRequest):
    """
    Create a new conversation.

    Returns the created conversation with ID.
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503, detail="Conversation service not available"
        )

    service = server.service_container.conversation_service

    # Create conversation
    result = await service.create_conversation(
        user_id="default",  # Single-user mode for now
        title=request.title,
        model=request.model,
        context_documents=request.context_documents,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    # Handle result
    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )

    conversation = result.unwrap()

    return {
        "success": True,
        "conversation": conversation,
    }


@router.get("/conversations")
async def list_conversations(
    limit: int = 50,
    offset: int = 0,
    include_archived: bool = False,
):
    """
    List conversations for the current user.

    Supports pagination and filtering.
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503, detail="Conversation service not available"
        )

    service = server.service_container.conversation_service

    # List conversations
    result = await service.list_conversations(
        user_id="default",  # Single-user mode
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )

    # Handle result
    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )

    data = result.unwrap()

    return {
        "success": True,
        **data,
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    include_messages: bool = True,
    message_limit: int = 50,
):
    """
    Get a conversation by ID.

    Optionally includes message history.
    """
    server = get_server()

    if not server.service_container:
        raise HTTPException(status_code=503, detail="Services not available")

    conv_service = server.service_container.conversation_service
    msg_service = server.service_container.message_service

    if not conv_service:
        raise HTTPException(
            status_code=503, detail="Conversation service not available"
        )

    # Get conversation
    conv_result = await conv_service.get_conversation(conversation_id)

    if conv_result.is_failure():
        return JSONResponse(
            content=conv_result.to_dict(),
            status_code=conv_result.status_code,
        )

    conversation = conv_result.unwrap()

    # Optionally get messages
    if include_messages and msg_service:
        msg_result = await msg_service.get_messages(
            conversation_id=conversation_id,
            limit=message_limit,
            offset=0,
            include_citations=True,
        )

        if msg_result.is_success():
            messages_data = msg_result.unwrap()
            conversation["messages"] = messages_data["messages"]
            conversation["message_count"] = messages_data["total"]
        else:
            # Don't fail if messages fail, just omit them
            conversation["messages"] = []
            conversation["message_count"] = 0

    return {
        "success": True,
        "conversation": conversation,
    }


@router.patch("/conversations/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
):
    """
    Update a conversation's settings.

    Only provided fields will be updated.
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503, detail="Conversation service not available"
        )

    service = server.service_container.conversation_service

    # Update conversation
    result = await service.update_conversation(
        conversation_id=conversation_id,
        title=request.title,
        context_documents=request.context_documents,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    # Handle result
    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )

    conversation = result.unwrap()

    return {
        "success": True,
        "conversation": conversation,
    }


@router.delete("/conversations/{conversation_id}")
async def archive_conversation(conversation_id: str):
    """
    Archive (soft delete) a conversation.

    Archived conversations can be restored by updating archived_at to null.
    """
    server = get_server()

    if (
        not server.service_container
        or not server.service_container.conversation_service
    ):
        raise HTTPException(
            status_code=503, detail="Conversation service not available"
        )

    service = server.service_container.conversation_service

    # Archive conversation
    result = await service.archive_conversation(conversation_id)

    # Handle result
    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )

    conversation = result.unwrap()

    return {
        "success": True,
        "conversation": conversation,
        "message": "Conversation archived successfully",
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
):
    """
    Send a message (question) and get AI response.

    This endpoint:
    1. Adds user question to conversation
    2. Queries LlamaIndex for answer using RAG
    3. Adds AI response with citations
    4. Returns both messages
    """
    server = get_server()

    if not server.service_container:
        raise HTTPException(status_code=503, detail="Services not available")

    conv_service = server.service_container.conversation_service
    msg_service = server.service_container.message_service
    llamaindex_service = server.service_container.llamaindex_service

    if not conv_service or not msg_service:
        raise HTTPException(status_code=503, detail="Message service not available")

    if not llamaindex_service:
        raise HTTPException(status_code=503, detail="LlamaIndex service not available")

    try:
        # Verify conversation exists
        conv_result = await conv_service.get_conversation(conversation_id)
        if conv_result.is_failure():
            return JSONResponse(
                content=conv_result.to_dict(),
                status_code=conv_result.status_code,
            )

        conversation = conv_result.unwrap()

        # Add user message
        user_msg_result = await msg_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.content,
        )

        if user_msg_result.is_failure():
            return JSONResponse(
                content=user_msg_result.to_dict(),
                status_code=user_msg_result.status_code,
            )

        user_message = user_msg_result.unwrap()

        # Query LlamaIndex for answer
        start_time = time.time()

        # Build filters from conversation context
        filters = None
        if conversation.get("context_documents"):
            filters = {"document_id": {"$in": conversation["context_documents"]}}

        # Query with RAG
        rag_response = await llamaindex_service.query(
            question=request.content,
            similarity_top_k=request.context_limit,
            response_mode="tree_summarize",
            filters=filters,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Handle RAG errors
        if rag_response.get("error"):
            error_msg = rag_response.get("error_message", "Query failed")

            # Get model from conversation or use current settings
            model = conversation.get("model") or get_settings().llm_model

            # Add error response message
            await msg_service.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=f"I encountered an error: {error_msg}",
                model=model,
                confidence=0.0,
                method="error",
                latency_ms=latency_ms,
            )

            raise HTTPException(status_code=500, detail=error_msg)

        # Extract response data
        answer = rag_response.get("answer", "")
        sources = rag_response.get("sources", [])
        confidence = rag_response.get("confidence", 0.5)
        method = rag_response.get("method", "rag")

        # Get model from conversation or use current settings
        model = conversation.get("model") or get_settings().llm_model

        # Add assistant message
        assistant_msg_result = await msg_service.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            model=model,
            confidence=confidence,
            method=method,
            latency_ms=latency_ms,
        )

        if assistant_msg_result.is_failure():
            return JSONResponse(
                content=assistant_msg_result.to_dict(),
                status_code=assistant_msg_result.status_code,
            )

        assistant_message = assistant_msg_result.unwrap()

        # Add citations if available
        if sources:
            citations = []
            for i, source in enumerate(sources):
                citations.append(
                    {
                        "document_id": source.get("document_id", ""),
                        "chunk_id": source.get("node_id"),
                        "score": source.get("score"),
                        "snippet": source.get("text", "")[:500],  # Limit snippet size
                        "position": i,
                    }
                )

            citation_result = await msg_service.add_citations(
                message_id=str(assistant_message["id"]),
                citations=citations,
            )

            if citation_result.is_success():
                assistant_message["citations"] = citation_result.unwrap()

        return {
            "success": True,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "latency_ms": latency_ms,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/conversations/{conversation_id}/messages/stream")
async def send_message_streaming(
    conversation_id: str,
    request: SendMessageRequest,
):
    """
    Send a message and stream AI response using Server-Sent Events (SSE).

    This endpoint:
    1. Saves user message
    2. Streams AI response token-by-token
    3. Saves complete assistant message with citations
    4. Returns SSE stream with events:
       - user_message: User message saved
       - intent_check: Query classification
       - sources: Retrieved document chunks
       - chunk: Individual tokens
       - metadata: Final statistics
       - complete: Final saved message
       - error: Any errors

    Returns:
        StreamingResponse with text/event-stream content type
    """
    server = get_server()

    if not server.service_container:
        raise HTTPException(status_code=503, detail="Services not available")

    conv_service = server.service_container.conversation_service
    msg_service = server.service_container.message_service
    llamaindex_service = server.service_container.llamaindex_service

    if not conv_service or not msg_service:
        raise HTTPException(status_code=503, detail="Message service not available")

    if not llamaindex_service:
        raise HTTPException(status_code=503, detail="LlamaIndex service not available")

    async def event_generator():
        """Generate SSE events for streaming response."""
        try:
            # Verify conversation exists
            conv_result = await conv_service.get_conversation(conversation_id)
            if conv_result.is_failure():
                yield f"event: error\ndata: {json.dumps({'error': 'Conversation not found', 'error_type': 'NotFound'})}\n\n"
                return

            conversation = conv_result.unwrap()

            # Add user message
            user_msg_result = await msg_service.add_message(
                conversation_id=conversation_id,
                role="user",
                content=request.content,
            )

            if user_msg_result.is_failure():
                yield f"event: error\ndata: {json.dumps({'error': 'Failed to save user message', 'error_type': 'DatabaseError'})}\n\n"
                return

            user_message = user_msg_result.unwrap()

            # Send user message event (serialize all types)
            yield f"event: user_message\ndata: {json.dumps(serialize_for_json(user_message))}\n\n"

            # Build filters from conversation context
            filters = None
            if conversation.get("context_documents"):
                filters = {"document_id": {"$in": conversation["context_documents"]}}

            # Track timing and accumulate response
            start_time = time.time()
            accumulated_text = ""
            sources_data = []
            metadata_info = {}

            # Stream query response with timeout
            try:
                async with asyncio.timeout(120):  # 2 minute timeout
                    async for event in llamaindex_service.query_streaming(
                        question=request.content,
                        similarity_top_k=request.context_limit,
                        response_mode="tree_summarize",
                        filters=filters,
                    ):
                        event_type = event.get("type")
                        event_data = event.get("data")

                        if event_type == "intent_check":
                            yield f"event: intent_check\ndata: {json.dumps(event_data)}\n\n"

                        elif event_type == "sources":
                            sources_data = event_data
                            yield f"event: sources\ndata: {json.dumps(event_data)}\n\n"

                        elif event_type == "chunk":
                            accumulated_text += event_data
                            yield f"event: chunk\ndata: {json.dumps({'text': event_data})}\n\n"

                        elif event_type == "metadata":
                            metadata_info = event_data
                            yield f"event: metadata\ndata: {json.dumps(event_data)}\n\n"

                        elif event_type == "error":
                            yield f"event: error\ndata: {json.dumps(event_data)}\n\n"
                            return

            except asyncio.TimeoutError:
                yield f"event: error\ndata: {json.dumps({'error': 'Query timeout after 120 seconds', 'error_type': 'TimeoutError'})}\n\n"
                return

            latency_ms = int((time.time() - start_time) * 1000)

            # Get model from conversation or use current settings
            model = conversation.get("model") or get_settings().llm_model

            # Save complete assistant message
            confidence = metadata_info.get("confidence_score", 0.5)
            method = metadata_info.get("method", "llamaindex_rag")

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

            # Add citations if available
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

            # Send completion event with final message (serialize all types)
            completion_data = serialize_for_json(
                {
                    "user_message": user_message,
                    "assistant_message": assistant_message,
                    "latency_ms": latency_ms,
                }
            )
            yield f"event: complete\ndata: {json.dumps(completion_data)}\n\n"

        except Exception as e:
            # Log error and send error event
            import logging

            logging.error(f"Streaming error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e), 'error_type': type(e).__name__})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: str,
    limit: int = 50,
    offset: int = 0,
    include_citations: bool = True,
):
    """
    Get message history for a conversation.

    Returns paginated messages with optional citations.
    """
    server = get_server()

    if not server.service_container or not server.service_container.message_service:
        raise HTTPException(status_code=503, detail="Message service not available")

    service = server.service_container.message_service

    # Get messages
    result = await service.get_messages(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset,
        include_citations=include_citations,
    )

    # Handle result
    if result.is_failure():
        return JSONResponse(
            content=result.to_dict(),
            status_code=result.status_code,
        )

    data = result.unwrap()

    return {
        "success": True,
        **data,
    }
