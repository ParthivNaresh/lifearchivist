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
from lifearchivist.llm import LLMMessage

from ..dependencies import get_server
from ..error_formatting import create_error_metadata, format_llm_error

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
    provider_id: Optional[str] = Field(
        None, description="LLM provider ID (e.g., 'my-openai'). NULL = use default"
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
    model: Optional[str] = Field(None, description="New model")
    provider_id: Optional[str] = Field(None, description="New provider ID")
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
        provider_id=request.provider_id,
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
        model=request.model,
        provider_id=request.provider_id,
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

        start_time = time.time()

        # Step 1: Retrieve relevant documents using LlamaIndex (RAG retrieval only)
        filters = None
        if conversation.get("context_documents"):
            filters = {"document_id": {"$in": conversation["context_documents"]}}

        search_results = await llamaindex_service.semantic_search(
            query=request.content,
            top_k=request.context_limit,
            filters=filters,
        )

        # Convert search results to sources format
        sources = []
        for result in search_results:
            sources.append(
                {
                    "document_id": result.get("document_id", ""),
                    "node_id": result.get("node_id"),
                    "score": result.get("score", 0.0),
                    "text": result.get("text", ""),
                    "metadata": result.get("metadata", {}),
                }
            )

        # Step 2: Build LLM messages with RAG context
        messages = []

        # System message with context
        system_prompt = (
            conversation.get("system_prompt")
            or "You are a helpful assistant that answers questions based on the provided context."
        )

        if sources:
            context_text = "\n\n".join(
                [
                    f"[Document {i+1}]\n{source.get('text', '')}"
                    for i, source in enumerate(sources[:5])
                ]
            )
            system_content = f"{system_prompt}\n\nContext:\n{context_text}"
        else:
            system_content = system_prompt

        messages.append(LLMMessage(role="system", content=system_content))
        messages.append(LLMMessage(role="user", content=request.content))

        # Step 3: Generate response using provider manager
        provider_manager = server.service_container.llm_provider_manager
        if not provider_manager:
            raise HTTPException(
                status_code=503, detail="LLM provider manager not available"
            )

        provider_id = conversation.get("provider_id")
        model = conversation.get("model") or get_settings().llm_model
        temperature = conversation.get("temperature", 0.7)
        max_tokens = conversation.get("max_tokens", 2000)

        gen_result = await provider_manager.generate(
            messages=messages,
            model=model,
            provider_id=provider_id,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        if gen_result.is_failure():
            error = RuntimeError(gen_result.error)
            user_friendly_message = format_llm_error(error, model)
            error_metadata = create_error_metadata(
                error, provider_id or "default", model
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

            raise HTTPException(status_code=500, detail=gen_result.error)

        response = gen_result.unwrap()
        answer = response.content
        confidence = 0.8 if sources else 0.5
        method = "rag_with_provider" if sources else "direct_provider"

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
        start_time = time.time()
        conversation = None
        provider_id = None
        model = None

        try:
            # Verify conversation exists
            conv_result = await conv_service.get_conversation(conversation_id)
            if conv_result.is_failure():
                yield f"event: error\ndata: {json.dumps({'error': 'Conversation not found', 'error_type': 'NotFound'})}\n\n"
                return

            conversation = conv_result.unwrap()
            provider_id = conversation.get("provider_id")
            model = conversation.get("model") or get_settings().llm_model

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

            # Step 1: Retrieve relevant documents using LlamaIndex (RAG retrieval only)
            filters = None
            if conversation.get("context_documents"):
                filters = {"document_id": {"$in": conversation["context_documents"]}}

            search_results = await llamaindex_service.semantic_search(
                query=request.content,
                top_k=request.context_limit,
                filters=filters,
            )

            # Convert search results to sources format
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

            # Emit sources event
            yield f"event: sources\ndata: {json.dumps(sources_data)}\n\n"

            # Step 2: Build LLM messages with RAG context
            messages = []

            system_prompt = (
                conversation.get("system_prompt")
                or "You are a helpful assistant that answers questions based on the provided context."
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

            # Step 3: Stream response using provider manager
            provider_manager = server.service_container.llm_provider_manager
            if not provider_manager:
                yield f"event: error\ndata: {json.dumps({'error': 'LLM provider manager not available', 'error_type': 'ServiceUnavailable'})}\n\n"
                return

            provider_id = conversation.get("provider_id")
            model = conversation.get("model") or get_settings().llm_model
            temperature = conversation.get("temperature", 0.7)
            max_tokens = conversation.get("max_tokens", 2000)

            accumulated_text = ""
            tokens_used = 0
            finish_reason = None

            try:
                async with asyncio.timeout(120):  # 2 minute timeout
                    async for chunk in provider_manager.generate_stream(
                        messages=messages,
                        model=model,
                        provider_id=provider_id,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ):
                        accumulated_text += chunk.content

                        # Emit chunk event
                        yield f"event: chunk\ndata: {json.dumps({'text': chunk.content})}\n\n"

                        # Capture final metadata
                        if chunk.is_final:
                            tokens_used = chunk.tokens_used or 0
                            finish_reason = chunk.finish_reason

            except asyncio.TimeoutError as e:
                latency_ms = int((time.time() - start_time) * 1000)
                user_friendly_message = "Query timeout after 120 seconds. Please try again with a shorter query."
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

            # Emit metadata event
            metadata_info = {
                "confidence_score": 0.8 if sources_data else 0.5,
                "method": "rag_with_provider" if sources_data else "direct_provider",
                "model": model,
                "provider_id": provider_id,
                "tokens_used": tokens_used,
                "finish_reason": finish_reason,
            }
            yield f"event: metadata\ndata: {json.dumps(metadata_info)}\n\n"

            # Save complete assistant message
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
            import logging

            logging.error(f"Streaming error: {e}", exc_info=True)

            try:
                latency_ms = int((time.time() - start_time) * 1000)
                final_provider_id = provider_id or "default"
                final_model = model or get_settings().llm_model
                user_friendly_message = format_llm_error(e, final_model)
                error_metadata = create_error_metadata(
                    e, final_provider_id, final_model
                )

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
                logging.error(
                    f"Failed to save error message: {save_error}", exc_info=True
                )

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
