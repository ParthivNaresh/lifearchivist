"""
Ask question endpoint.
"""

from fastapi import APIRouter, status

from ..shared.dependencies import get_server
from ..shared.exceptions import (
    InternalServerError,
    ServiceUnavailableError,
    ValidationError,
)
from .misc_models import Citation
from .request_models import AskQuestionRequest
from .response_models import AskQuestionResponse

router = APIRouter()


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

    if not server.llamaindex_service.query_service:
        raise ServiceUnavailableError("Query service")

    try:
        result = await server.llamaindex_service.query_service.query(
            question=request.question,
            similarity_top_k=request.context_limit,
            response_mode="tree_summarize",
            filters=request.filters,
        )

        if result.is_failure():
            raise InternalServerError("Q&A", Exception(result.error))

        query_response = result.value
        answer = query_response.get("answer", "")
        sources = query_response.get("sources", [])
        confidence = query_response.get("confidence_score", 0.0)

        citations = []
        for source in sources:
            snippet = source.get("text", "")[:200] if source.get("text") else ""
            citations.append(
                Citation(
                    doc_id=source.get("document_id", ""),
                    title=source.get("metadata", {}).get("title", "Unknown Document"),
                    snippet=snippet,
                    score=source.get("score", 0.0),
                )
            )

        return AskQuestionResponse(
            answer=answer,
            confidence=confidence,
            citations=citations,
            method=query_response.get("method", "llamaindex_rag"),
            context_length=len(citations),
            statistics=query_response.get("statistics", {}),
        )

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as e:
        raise InternalServerError("Q&A", e) from e
