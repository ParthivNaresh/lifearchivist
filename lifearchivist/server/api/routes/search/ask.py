"""
Ask question endpoint.
"""

from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server
from ..shared.responses import (
    internal_error_response,
    success_response,
    validation_error_response,
)
from .utils import validate_llamaindex_service, validate_query_service

router = APIRouter()


@router.post("/ask")
async def ask_question(request: Dict[str, Any]):
    """
    Ask a question using RAG Q&A.

    Uses the query service to retrieve relevant context and generate answers.
    """
    server = get_server()

    question = request.get("question", "").strip()
    context_limit = request.get("context_limit", 5)
    filters = request.get("filters")

    if not question:
        return validation_error_response("Question is required")

    if len(question) < 3:
        return validation_error_response("Question must be at least 3 characters long")

    if isinstance(context_limit, str):
        try:
            context_limit = int(context_limit)
        except ValueError:
            return validation_error_response("context_limit must be a number")

    if context_limit < 1 or context_limit > 20:
        return validation_error_response("context_limit must be between 1 and 20")

    llamaindex_service, error_response = validate_llamaindex_service(server)
    if error_response:
        return error_response

    query_service, error_response = validate_query_service(llamaindex_service)
    if error_response:
        return error_response

    assert llamaindex_service is not None
    assert query_service is not None

    try:
        result = await query_service.query(
            question=question,
            similarity_top_k=context_limit,
            response_mode="tree_summarize",
            filters=filters,
        )

        if result.is_failure():
            return JSONResponse(
                content=result.to_dict(),
                status_code=result.status_code,
            )

        query_response = result.value
        answer = query_response.get("answer", "")
        sources = query_response.get("sources", [])
        confidence = query_response.get("confidence_score", 0.0)

        citations = []
        for source in sources:
            snippet = source.get("text", "")[:200] if source.get("text") else ""
            citations.append(
                {
                    "doc_id": source.get("document_id", ""),
                    "title": source.get("metadata", {}).get(
                        "title", "Unknown Document"
                    ),
                    "snippet": snippet,
                    "score": source.get("score", 0.0),
                }
            )

        return success_response(
            {
                "answer": answer,
                "confidence": confidence,
                "citations": citations,
                "method": query_response.get("method", "llamaindex_rag"),
                "context_length": len(citations),
                "statistics": query_response.get("statistics", {}),
            }
        )

    except Exception as e:
        return internal_error_response("Q&A", e)
