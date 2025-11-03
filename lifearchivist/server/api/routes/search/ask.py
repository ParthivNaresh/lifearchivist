"""
Ask question endpoint.
"""

from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..shared.dependencies import get_server

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
        return JSONResponse(
            content={
                "success": False,
                "error": "Question is required",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if len(question) < 3:
        return JSONResponse(
            content={
                "success": False,
                "error": "Question must be at least 3 characters long",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if isinstance(context_limit, str):
        try:
            context_limit = int(context_limit)
        except ValueError:
            return JSONResponse(
                content={
                    "success": False,
                    "error": "context_limit must be a number",
                    "error_type": "ValidationError",
                },
                status_code=400,
            )

    if context_limit < 1 or context_limit > 20:
        return JSONResponse(
            content={
                "success": False,
                "error": "context_limit must be between 1 and 20",
                "error_type": "ValidationError",
            },
            status_code=400,
        )

    if not server.llamaindex_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Q&A service not available",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

    query_service = server.llamaindex_service.query_service
    if not query_service:
        return JSONResponse(
            content={
                "success": False,
                "error": "Query service not initialized",
                "error_type": "ServiceUnavailable",
            },
            status_code=503,
        )

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

        return {
            "success": True,
            "answer": answer,
            "confidence": confidence,
            "citations": citations,
            "method": query_response.get("method", "llamaindex_rag"),
            "context_length": len(citations),
            "statistics": query_response.get("statistics", {}),
        }

    except Exception as e:
        return JSONResponse(
            content={
                "success": False,
                "error": f"Q&A failed: {str(e)}",
                "error_type": type(e).__name__,
            },
            status_code=500,
        )
