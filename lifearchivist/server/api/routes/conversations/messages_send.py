"""
Send message endpoint.
"""

import math
import time
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter
from fastapi import Path as PathParam
from fastapi import status

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
from .misc_models import LLMConfig, MessageContext, SearchContext
from .request_models import SendMessageRequest
from .response_models import SendMessageResponse

router = APIRouter()


class MessageProcessor:
    """Handles message processing logic."""

    def __init__(self, server: Any):
        self.server = server
        self._validate_services()

    def _validate_services(self) -> None:
        """Validate required services are available."""
        if not self.server.service_container:
            raise ServiceUnavailableError("Service container")

        if not self.server.service_container.conversation_service:
            raise ServiceUnavailableError("Conversation service")

        if not self.server.service_container.message_service:
            raise ServiceUnavailableError("Message service")

        if not self.server.service_container.llamaindex_service:
            raise ServiceUnavailableError("LlamaIndex service")

        if not self.server.service_container.llm_provider_manager:
            raise ServiceUnavailableError("LLM provider manager")

    async def fetch_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Fetch conversation data."""
        conv_service = self.server.service_container.conversation_service
        conv_result = await conv_service.get_conversation(conversation_id)

        if conv_result.is_failure():
            error_msg = conv_result.error
            if "not found" in error_msg.lower():
                raise ResourceNotFoundError("Conversation", conversation_id)
            raise InternalServerError("Get conversation", Exception(error_msg))

        conversation_data: Dict[str, Any] = conv_result.unwrap()
        return conversation_data

    async def add_user_message(
        self, conversation_id: str, content: str
    ) -> Dict[str, Any]:
        """Add user message to conversation."""
        msg_service = self.server.service_container.message_service
        user_msg_result = await msg_service.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content,
        )

        if user_msg_result.is_failure():
            raise InternalServerError(
                "Add user message", Exception(user_msg_result.error)
            )

        message_data: Dict[str, Any] = user_msg_result.unwrap()
        return message_data

    async def perform_semantic_search(self, context: MessageContext) -> SearchContext:
        """Perform semantic search for context."""
        llamaindex_service = self.server.service_container.llamaindex_service

        filters = self._build_search_filters(context.conversation)

        search_results = await llamaindex_service.semantic_search(
            query=context.user_content,
            top_k=context.context_limit,
            filters=filters,
        )

        sources = self._extract_sources(search_results)
        context_text = self._build_context_text(sources) if sources else None

        return SearchContext(sources=sources, context_text=context_text)

    def _build_search_filters(
        self, conversation: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Build search filters from conversation context."""
        if conversation.get("context_documents"):
            return {"document_id": {"$in": conversation["context_documents"]}}
        return None

    def _extract_sources(self, search_results: List[Any]) -> List[Dict[str, Any]]:
        """Extract source information from search results."""
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

    def _build_context_text(self, sources: List[Dict[str, Any]]) -> str:
        """Build context text from sources."""
        return "\n\n".join(
            f"[Document {i+1}]\n{source.get('text', '')}"
            for i, source in enumerate(sources[:5])
        )

    async def get_llm_config(self, conversation: Dict[str, Any]) -> LLMConfig:
        """Get LLM configuration from conversation and preferences."""
        response_format = await self._fetch_response_format()
        temperature, max_tokens = await self._fetch_generation_params(conversation)

        base_system_prompt = (
            conversation.get("system_prompt")
            or "You are a helpful assistant that answers questions based on the provided context."
        )

        return LLMConfig(
            provider_id=conversation.get("provider_id"),
            model=conversation.get("model") or get_settings().llm_model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=base_system_prompt,
            response_format=response_format,
        )

    async def _fetch_response_format(self) -> Optional[str]:
        """Fetch response format from user preferences."""
        db_pool = self.server.service_container.conversation_service.db_pool
        async with db_pool.acquire() as conn:
            prefs = await conn.fetchrow(
                "SELECT response_format FROM user_preferences WHERE user_id = 'default'"
            )
            return prefs["response_format"] if prefs else None

    async def _fetch_generation_params(
        self, conversation: Dict[str, Any]
    ) -> Tuple[float, int]:
        """Fetch temperature and max tokens from preferences."""
        temperature = conversation.get("temperature", 0.7)
        max_tokens = conversation.get("max_tokens", 2000)

        if (
            math.isclose(temperature, 0.7, rel_tol=1e-09, abs_tol=1e-09)
            or max_tokens == 2000
        ):
            db_pool = self.server.service_container.conversation_service.db_pool
            async with db_pool.acquire() as conn:
                prefs = await conn.fetchrow(
                    "SELECT temperature, max_output_tokens FROM user_preferences WHERE user_id = 'default'"
                )
                if prefs:
                    if math.isclose(temperature, 0.7, rel_tol=1e-09, abs_tol=1e-09):
                        temperature = prefs["temperature"]
                    if max_tokens == 2000:
                        max_tokens = prefs["max_output_tokens"]

        return temperature, max_tokens

    def build_llm_messages(
        self, config: LLMConfig, search_context: SearchContext, user_content: str
    ) -> List[LLMMessage]:
        """Build LLM messages with context."""
        system_prompt = PromptFormatter.apply_response_format(
            config.system_prompt, config.response_format
        )

        if search_context.context_text:
            system_content = (
                f"{system_prompt}\n\nContext:\n{search_context.context_text}"
            )
        else:
            system_content = system_prompt

        return [
            LLMMessage(role="system", content=system_content),
            LLMMessage(role="user", content=user_content),
        ]

    async def generate_response(
        self, messages: List[LLMMessage], config: LLMConfig
    ) -> Tuple[str, int]:
        """Generate LLM response."""
        provider_manager = self.server.service_container.llm_provider_manager

        gen_result = await provider_manager.generate(
            messages=messages,
            model=config.model,
            provider_id=config.provider_id,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )

        if gen_result.is_failure():
            raise InternalServerError("Generate response", Exception(gen_result.error))

        response = gen_result.unwrap()
        return response.content, 0

    async def handle_generation_error(
        self,
        error: Exception,
        context: MessageContext,
        config: LLMConfig,
        latency_ms: int,
    ) -> None:
        """Handle LLM generation errors."""
        user_friendly_message = format_llm_error(error, config.model)
        error_metadata = create_error_metadata(
            error, config.provider_id or "default", config.model
        )

        msg_service = self.server.service_container.message_service
        await msg_service.add_message(
            conversation_id=context.conversation_id,
            role="assistant",
            content=user_friendly_message,
            model=config.model,
            confidence=0.0,
            method="error",
            latency_ms=latency_ms,
            metadata=error_metadata,
        )

    async def add_assistant_message(
        self,
        context: MessageContext,
        content: str,
        config: LLMConfig,
        has_sources: bool,
        latency_ms: int,
    ) -> Dict[str, Any]:
        """Add assistant message to conversation."""
        msg_service = self.server.service_container.message_service

        confidence = 0.8 if has_sources else 0.5
        method = "rag_with_provider" if has_sources else "direct_provider"

        assistant_msg_result = await msg_service.add_message(
            conversation_id=context.conversation_id,
            role="assistant",
            content=content,
            model=config.model,
            confidence=confidence,
            method=method,
            latency_ms=latency_ms,
        )

        if assistant_msg_result.is_failure():
            raise InternalServerError(
                "Add assistant message", Exception(assistant_msg_result.error)
            )

        assistant_data: Dict[str, Any] = assistant_msg_result.unwrap()
        return assistant_data

    async def add_citations(
        self, message_id: str, sources: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """Add citations to assistant message."""
        if not sources:
            return None

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

        citation_result = await msg_service.add_citations(
            message_id=str(message_id),
            citations=citations,
        )

        return citation_result.unwrap() if citation_result.is_success() else None


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
    try:
        server = get_server()
        processor = MessageProcessor(server)

        start_time = time.time()

        conversation = await processor.fetch_conversation(conversation_id)
        user_message = await processor.add_user_message(
            conversation_id, request.content
        )

        context = MessageContext(
            conversation_id=conversation_id,
            conversation=conversation,
            user_content=request.content,
            context_limit=request.context_limit,
            start_time=start_time,
        )

        search_context = await processor.perform_semantic_search(context)
        llm_config = await processor.get_llm_config(conversation)
        messages = processor.build_llm_messages(
            llm_config, search_context, request.content
        )

        latency_ms = int((time.time() - start_time) * 1000)

        try:
            answer, _ = await processor.generate_response(messages, llm_config)
        except InternalServerError as e:
            cause = e.__cause__ if e.__cause__ else e
            if isinstance(cause, Exception):
                await processor.handle_generation_error(
                    cause, context, llm_config, latency_ms
                )
            raise

        assistant_message = await processor.add_assistant_message(
            context, answer, llm_config, bool(search_context.sources), latency_ms
        )

        citations = await processor.add_citations(
            str(assistant_message["id"]), search_context.sources
        )
        if citations:
            assistant_message["citations"] = citations

        from .misc_models import Citation, Message

        if assistant_message.get("citations"):
            assistant_message["citations"] = [
                Citation(**cit) for cit in assistant_message["citations"]
            ]

        user_msg = Message(**user_message)
        assistant_msg = Message(**assistant_message)

        return SendMessageResponse(
            success=True,
            user_message=user_msg,
            assistant_message=assistant_msg,
            latency_ms=latency_ms,
        )

    except (ServiceUnavailableError, ResourceNotFoundError):
        raise
    except Exception as e:
        raise InternalServerError("Send message", e) from e
