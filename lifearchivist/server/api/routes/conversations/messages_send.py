"""
Send message endpoint.
"""

import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from lifearchivist.config import get_settings
from lifearchivist.llm import LLMMessage

from ...error_formatting import create_error_metadata, format_llm_error
from ...prompt_utils import PromptFormatter
from ..constants import ErrorMessages
from ..shared.dependencies import get_server
from .models import SendMessageRequest

router = APIRouter()


@router.post("/{conversation_id}/messages")
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
        raise HTTPException(
            status_code=503, detail=ErrorMessages.SERVICES_NOT_AVAILABLE
        )

    conv_service = server.service_container.conversation_service
    msg_service = server.service_container.message_service
    llamaindex_service = server.service_container.llamaindex_service

    if not conv_service or not msg_service:
        raise HTTPException(status_code=503, detail="Message service not available")

    if not llamaindex_service:
        raise HTTPException(status_code=503, detail="LlamaIndex service not available")

    try:
        if not conv_service:
            raise HTTPException(
                status_code=503, detail=ErrorMessages.CONVERSATION_SERVICE_NOT_AVAILABLE
            )

        conv_result = await conv_service.get_conversation(conversation_id)
        if conv_result.is_failure():
            return JSONResponse(
                content=conv_result.to_dict(),
                status_code=conv_result.status_code,
            )

        conversation = conv_result.unwrap()

        if not msg_service:
            raise HTTPException(status_code=503, detail="Message service not available")

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

        messages = []

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
            raise HTTPException(
                status_code=503, detail="LLM provider manager not available"
            )

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

            raise HTTPException(status_code=500, detail=gen_result.error)

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
            return JSONResponse(
                content=assistant_msg_result.to_dict(),
                status_code=assistant_msg_result.status_code,
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
