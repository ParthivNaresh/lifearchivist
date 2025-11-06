"""
Send message endpoint.
"""

import time
from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status
from pydantic import BaseModel, Field

from lifearchivist.config import get_settings
from lifearchivist.llm import LLMMessage

from ...error_formatting import create_error_metadata, format_llm_error
from ...prompt_utils import PromptFormatter
from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ResourceNotFoundError,
    ServiceUnavailableError,
)
from .models import SendMessageRequest

router = APIRouter()


class SendMessageResponse(BaseModel):
    """Response from sending a message."""

    success: bool = Field(
        default=True, description="Whether message was sent successfully"
    )
    user_message: Dict[str, Any] = Field(..., description="User message data")
    assistant_message: Dict[str, Any] = Field(
        ..., description="Assistant response data"
    )
    latency_ms: int = Field(..., description="Response latency in milliseconds")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "user_message": {
                    "id": "msg_1",
                    "role": "user",
                    "content": "What is this about?",
                },
                "assistant_message": {
                    "id": "msg_2",
                    "role": "assistant",
                    "content": "Based on the documents...",
                    "citations": [],
                },
                "latency_ms": 1500,
            }
        }


@router.post(
    "/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {
            "description": "Conversation not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Conversation not found: invalid-id"}
                }
            },
        },
        503: {
            "description": "Required service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "Message service not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Send message failed: <error message>"}
                }
            },
        },
    },
)
async def send_message(
    request: SendMessageRequest,
    conversation_id: str = PathParam(..., description="Unique conversation identifier"),
) -> SendMessageResponse:
    """
    Send a message and get AI response with RAG.

    Processes user message through RAG pipeline: adds message to conversation,
    retrieves relevant context, generates AI response, and returns both messages.

    ## Path Parameters

    - **conversation_id**: Unique identifier of the conversation

    ## Request Body

    - **content**: User message content
    - **context_limit**: Max context documents to retrieve (optional)

    ## Response Fields

    - **success**: Whether operation succeeded
    - **user_message**: User message object
    - **assistant_message**: AI response object with citations
    - **latency_ms**: Response generation time

    ## Example Request

    ```json
    {
        "content": "What does the document say about AI?",
        "context_limit": 5
    }
    ```

    ## Example Response

    ```json
    {
        "success": true,
        "user_message": {
            "id": "msg_1",
            "conversation_id": "conv_123",
            "role": "user",
            "content": "What does the document say about AI?",
            "created_at": "2025-01-08T14:30:00Z"
        },
        "assistant_message": {
            "id": "msg_2",
            "conversation_id": "conv_123",
            "role": "assistant",
            "content": "According to the documents, AI...",
            "model": "gpt-4",
            "confidence": 0.8,
            "method": "rag_with_provider",
            "latency_ms": 1500,
            "created_at": "2025-01-08T14:30:02Z",
            "citations": [
                {
                    "document_id": "doc_123",
                    "chunk_id": "chunk_1",
                    "score": 0.85,
                    "snippet": "AI is...",
                    "position": 0
                }
            ]
        },
        "latency_ms": 1500
    }
    ```

    ## Processing Pipeline

    1. **Add User Message**: Store user message in database
    2. **Semantic Search**: Retrieve relevant document chunks
    3. **Build Context**: Format context from search results
    4. **Generate Response**: Call LLM with context
    5. **Add Assistant Message**: Store AI response
    6. **Add Citations**: Link response to source documents
    7. **Return Both Messages**: User message + AI response

    ## RAG Features

    - **Context Documents**: Uses conversation's context_documents if set
    - **Semantic Search**: Vector similarity search for relevant chunks
    - **Citation Tracking**: Links responses to source documents
    - **Confidence Scoring**: 0.8 with sources, 0.5 without
    - **Method Tracking**: "rag_with_provider" or "direct_provider"

    ## Configuration

    Uses conversation settings:
    - **model**: LLM model to use
    - **provider_id**: LLM provider
    - **temperature**: Response randomness
    - **max_tokens**: Response length limit
    - **system_prompt**: Custom system instructions
    - **context_documents**: Document filter for RAG

    ## User Preferences

    Falls back to user preferences for:
    - **temperature**: Default 0.7
    - **max_tokens**: Default 2000
    - **response_format**: Output formatting

    ## Error Handling

    - LLM errors stored as assistant messages
    - User-friendly error messages
    - Error metadata tracked
    - Latency recorded even on errors

    ## Performance Notes

    - Latency includes full pipeline
    - Semantic search cached
    - Concurrent operations where possible
    - Typical latency: 1-3 seconds

    ## Notes

    - Returns 404 if conversation doesn't exist
    - Both messages stored before returning
    - Citations added asynchronously
    - Confidence based on context availability
    - Method indicates RAG vs direct
    """
    server = get_server()

    if not server.service_container:
        raise ServiceUnavailableError("Service container")

    conv_service = server.service_container.conversation_service
    msg_service = server.service_container.message_service
    llamaindex_service = server.service_container.llamaindex_service

    if not conv_service or not msg_service:
        raise ServiceUnavailableError("Message service")

    if not llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    try:
        conv_result = await conv_service.get_conversation(conversation_id)
        if conv_result.is_failure():
            error_msg = conv_result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Conversation", conversation_id)
            raise InternalServerError("Get conversation", Exception(error_msg))

        conversation = conv_result.unwrap()

        user_msg_result = await msg_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.content,
        )

        if user_msg_result.is_failure():
            raise InternalServerError(
                "Add user message", Exception(user_msg_result.error)
            )

        user_message = user_msg_result.unwrap()

        start_time = time.time()

        filters = None
        if conversation.get("context_documents"):
            filters = {"document_id": {"$in": conversation["context_documents"]}}

        search_results = await llamaindex_service.semantic_search(
            query=request.content,
            top_k=request.context_limit,
            filters=filters,
        )

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

        messages: List[LLMMessage] = []

        response_format = None
        if server.service_container and server.service_container.conversation_service:
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

        provider_manager = server.service_container.llm_provider_manager
        if not provider_manager:
            raise ServiceUnavailableError("LLM provider manager")

        provider_id = conversation.get("provider_id")
        model = conversation.get("model") or get_settings().llm_model

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

            raise InternalServerError("Generate response", Exception(gen_result.error))

        response = gen_result.unwrap()
        answer = response.content
        confidence = 0.8 if sources else 0.5
        method = "rag_with_provider" if sources else "direct_provider"

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
            raise InternalServerError(
                "Add assistant message", Exception(assistant_msg_result.error)
            )

        assistant_message = assistant_msg_result.unwrap()

        if sources:
            citations = []
            for i, source in enumerate(sources):
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

        return SendMessageResponse(
            success=True,
            user_message=user_message,
            assistant_message=assistant_message,
            latency_ms=latency_ms,
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Send message", e) from e
