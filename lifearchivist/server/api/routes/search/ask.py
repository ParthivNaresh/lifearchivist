"""
Ask question endpoint.
"""

from typing import List, Tuple

from fastapi import APIRouter, status

from lifearchivist.llm import LLMMessage

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ServiceUnavailableError,
    ValidationError,
)
from .request_models import AskQuestionRequest
from .response_models import AskQuestionResponse
from .utils import (
    build_context_from_sources,
    calculate_average_score,
    create_citations_from_sources,
    create_rag_messages,
)

router = APIRouter()


def _create_no_sources_response() -> AskQuestionResponse:
    """Create response when no sources are found."""
    return AskQuestionResponse(
        answer="I couldn't find any relevant information in your documents to answer this question.",
        confidence=0.0,
        citations=[],
        method="search_only",
        context_length=0,
        statistics={
            "sources_found": 0,
            "avg_score": 0.0,
        },
    )


async def _generate_answer(
    llm_provider_manager, messages: List[LLMMessage]
) -> Tuple[str, int]:
    """Generate answer using LLM and return accumulated text and tokens used."""
    accumulated_text = ""
    tokens_used = 0

    async for chunk in llm_provider_manager.generate_stream(
        messages=messages,
        model=None,
        provider_id=None,
        temperature=0.7,
        max_tokens=2000,
    ):
        accumulated_text += chunk.content
        if chunk.is_final and chunk.tokens_used:
            tokens_used = chunk.tokens_used

    return accumulated_text, tokens_used


@router.post(
    "/ask",
    response_model=AskQuestionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "example": {"detail": "Question must be at least 3 characters long"}
                }
            },
        },
        503: {
            "description": "Required service unavailable",
            "content": {
                "application/json": {
                    "example": {"detail": "LlamaIndex service not available"}
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {"detail": "Q&A failed: <error message>"}
                }
            },
        },
    },
)
async def ask_question(request: AskQuestionRequest) -> AskQuestionResponse:
    """
    Ask a question using RAG (Retrieval-Augmented Generation).

    Retrieves relevant context from documents and generates an answer using LLM.
    Returns answer with citations and confidence score.

    ## Request Body

    - **question**: Question to ask (min 3 characters)
    - **context_limit**: Max context documents (1-20, default: 5)
    - **filters**: Optional document filters

    ## Response Fields

    - **answer**: Generated answer text
    - **confidence**: Confidence score (0.0-1.0)
    - **citations**: Array of source citations
    - **method**: Generation method used
    - **context_length**: Number of context documents
    - **statistics**: Query statistics

    ## Example Request

    ```json
    {
        "question": "What is artificial intelligence?",
        "context_limit": 5,
        "filters": {
            "document_id": {"$in": ["doc_123", "doc_456"]}
        }
    }
    ```

    ## Example Response

    ```json
    {
        "answer": "Based on the documents, artificial intelligence (AI) is...",
        "confidence": 0.85,
        "citations": [
            {
                "doc_id": "doc_123",
                "title": "AI Overview.pdf",
                "snippet": "AI is a branch of computer science...",
                "score": 0.92
            },
            {
                "doc_id": "doc_456",
                "title": "Machine Learning Basics.pdf",
                "snippet": "Machine learning is a subset of AI...",
                "score": 0.87
            }
        ],
        "method": "llamaindex_rag",
        "context_length": 2,
        "statistics": {
            "tokens_used": 150,
            "response_time_ms": 1500
        }
    }
    ```

    ## RAG Process

    1. **Semantic Search**: Find relevant document chunks
    2. **Context Building**: Assemble context from top results
    3. **LLM Generation**: Generate answer with context
    4. **Citation Extraction**: Link answer to sources
    5. **Confidence Scoring**: Calculate answer confidence

    ## Filters

    Optional filters to narrow search:
    - **document_id**: Filter by specific documents
    - **metadata fields**: Filter by document metadata
    - **date ranges**: Filter by date fields

    ## Confidence Score

    - **0.8-1.0**: High confidence (strong sources)
    - **0.5-0.8**: Medium confidence (moderate sources)
    - **0.0-0.5**: Low confidence (weak sources)

    ## Citations

    Each citation includes:
    - **doc_id**: Source document identifier
    - **title**: Document title
    - **snippet**: Relevant text excerpt (max 200 chars)
    - **score**: Relevance score (0.0-1.0)

    ## Use Cases

    - Ask questions about documents
    - Research assistance
    - Document Q&A
    - Knowledge retrieval
    - Information lookup

    ## Performance Notes

    - Response time depends on context_limit
    - Lower context_limit = faster response
    - Higher context_limit = more comprehensive
    - Typical response: 1-3 seconds

    ## Notes

    - Returns 400 if question too short
    - Returns 503 if services unavailable
    - Context limit enforced: 1-20
    - Citations ordered by relevance
    - Snippets truncated to 200 chars
    """
    server = get_server()

    if not server.llamaindex_service:
        raise ServiceUnavailableError("LlamaIndex service")

    if not server.llamaindex_service.search_service:
        raise ServiceUnavailableError("Search service")

    try:
        search_result = await server.llamaindex_service.search_service.semantic_search(
            query=request.question,
            top_k=request.context_limit,
            similarity_threshold=0.45,
            filters=request.filters,
        )

        if search_result.is_failure():
            raise InternalServerError("Search", Exception(search_result.error))

        sources = search_result.value

        if not sources:
            return _create_no_sources_response()

        context = build_context_from_sources(sources, request.context_limit)
        messages = create_rag_messages(context, request.question)

        if (
            not server.service_container
            or not server.service_container.llm_provider_manager
        ):
            raise ServiceUnavailableError("LLM provider manager")

        accumulated_text, tokens_used = await _generate_answer(
            server.service_container.llm_provider_manager, messages
        )

        from lifearchivist.storage.utils import ConfidenceCalculator

        confidence = ConfidenceCalculator.calculate_confidence(
            answer=accumulated_text,
            sources=sources,
            context=context,
        )

        citations = create_citations_from_sources(sources)

        return AskQuestionResponse(
            answer=accumulated_text,
            confidence=confidence,
            citations=citations,
            method="rag_direct",
            context_length=len(citations),
            statistics={
                "sources_found": len(sources),
                "tokens_used": tokens_used,
                "avg_score": calculate_average_score(sources),
            },
        )

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Q&A", e) from e
