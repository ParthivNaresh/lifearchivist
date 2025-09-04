"""
Search and query endpoints.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

from lifearchivist.models import SearchRequest
from lifearchivist.utils.logging import log_context, log_event
from lifearchivist.utils.logging.structured import MetricsCollector

from ..dependencies import get_server

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
async def search_documents_post(request: SearchRequest):
    """Search documents via POST request."""
    with log_context(
        operation="api_search_post",
        query=request.query[:50] if request.query else "",
        mode=request.mode,
        limit=request.limit,
    ):
        metrics = MetricsCollector("api_search_post")
        metrics.start()

        server = get_server()

        metrics.add_metric("query_length", len(request.query or ""))
        metrics.add_metric("mode", request.mode)
        metrics.add_metric("limit", request.limit)
        metrics.add_metric("offset", request.offset)
        metrics.add_metric("has_filters", bool(request.filters))

        log_event(
            "api_search_post_started",
            {
                "query_preview": (request.query or "")[:100],
                "mode": request.mode,
                "limit": request.limit,
                "offset": request.offset,
                "filters": request.filters or {},
            },
        )

        try:
            result = await server.execute_tool("index.search", request.dict())

            if result.get("success"):
                search_result = result["result"]
                results_count = len(search_result.get("results", []))
                query_time_ms = search_result.get("query_time_ms", 0)

                metrics.add_metric("results_found", results_count)
                metrics.add_metric("query_time_ms", query_time_ms)
                metrics.set_success(True)
                metrics.report("api_search_post_completed")

                log_event(
                    "api_search_post_successful",
                    {
                        "results_count": results_count,
                        "query_time_ms": query_time_ms,
                        "query_preview": (request.query or "")[:50],
                        "mode": request.mode,
                    },
                )

                return search_result
            else:
                error = result.get("error", "Search tool returned None")
                metrics.set_error(RuntimeError(error))
                metrics.report("api_search_post_failed")

                log_event(
                    "api_search_post_tool_failed",
                    {
                        "error": error,
                        "query_preview": (request.query or "")[:50],
                        "mode": request.mode,
                    },
                )
                raise HTTPException(status_code=500, detail=error)

        except HTTPException:
            raise
        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_search_post_failed")

            log_event(
                "api_search_post_exception",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "query_preview": (request.query or "")[:50],
                    "mode": request.mode,
                },
            )
            raise HTTPException(status_code=500, detail=str(e)) from None


@router.get("/search")
async def search_documents_get(
    q: str = "",
    mode: str = "keyword",
    limit: int = 20,
    offset: int = 0,
    include_content: bool = False,
    mime_type: Optional[str] = None,
    status: Optional[str] = None,
    tags: Optional[str] = None,
):
    """Search documents using GET with query parameters and optional tag filtering."""
    with log_context(
        operation="api_search_get",
        query=q[:50],
        mode=mode,
        limit=limit,
        offset=offset,
    ):
        metrics = MetricsCollector("api_search_get")
        metrics.start()

        server = get_server()

        metrics.add_metric("query_length", len(q))
        metrics.add_metric("mode", mode)
        metrics.add_metric("limit", limit)
        metrics.add_metric("offset", offset)
        metrics.add_metric("include_content", include_content)

        # Validate parameters
        valid_modes = ["keyword", "semantic", "hybrid"]
        if mode not in valid_modes:
            log_event(
                "api_search_get_invalid_mode",
                {"mode": mode, "valid_modes": valid_modes, "query_preview": q[:50]},
            )
            metrics.set_error(ValueError("Invalid search mode"))
            metrics.report("api_search_get_failed")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode '{mode}'. Must be one of: {', '.join(valid_modes)}",
            )

        if limit < 1 or limit > 100:
            log_event(
                "api_search_get_invalid_limit",
                {"limit": limit, "query_preview": q[:50]},
            )
            metrics.set_error(ValueError("Invalid limit parameter"))
            metrics.report("api_search_get_failed")
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 100"
            )

        if offset < 0:
            log_event(
                "api_search_get_invalid_offset",
                {"offset": offset, "query_preview": q[:50]},
            )
            metrics.set_error(ValueError("Invalid offset parameter"))
            metrics.report("api_search_get_failed")
            raise HTTPException(status_code=400, detail="Offset must be non-negative")

        try:
            # Prepare filters
            filters: Dict[str, Any] = {}
            if mime_type:
                filters["mime_type"] = mime_type
            if status:
                filters["status"] = status
            if tags:
                # Parse comma-separated tags
                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
                if tag_list:
                    filters["tags"] = tag_list

            metrics.add_metric("filters_count", len(filters))

            log_event(
                "api_search_get_started",
                {
                    "query_preview": q[:100],
                    "mode": mode,
                    "limit": limit,
                    "offset": offset,
                    "include_content": include_content,
                    "filters": filters,
                },
            )

            # Execute search using the search tool
            result = await server.execute_tool(
                "index.search",
                {
                    "query": q,
                    "mode": mode,
                    "filters": filters,
                    "limit": limit,
                    "offset": offset,
                    "include_content": include_content,
                },
            )

            if result.get("success"):
                search_result = result["result"]
                results_count = len(search_result.get("results", []))
                query_time_ms = search_result.get("query_time_ms", 0)

                metrics.add_metric("results_found", results_count)
                metrics.add_metric("query_time_ms", query_time_ms)
                metrics.set_success(True)
                metrics.report("api_search_get_completed")

                log_event(
                    "api_search_get_successful",
                    {
                        "results_count": results_count,
                        "query_time_ms": query_time_ms,
                        "query_preview": q[:50],
                        "mode": mode,
                        "filters": filters,
                    },
                )

                return search_result
            else:
                error = result.get("error", "Search failed")
                metrics.set_error(RuntimeError(error))
                metrics.report("api_search_get_failed")

                log_event(
                    "api_search_get_tool_failed",
                    {
                        "error": error,
                        "query_preview": q[:50],
                        "mode": mode,
                        "filters": filters,
                    },
                )
                raise HTTPException(status_code=500, detail=error)

        except HTTPException:
            raise
        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_search_get_failed")

            log_event(
                "api_search_get_exception",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "query_preview": q[:50],
                    "mode": mode,
                },
            )
            raise HTTPException(status_code=500, detail=str(e)) from None


@router.post("/ask")
async def ask_question(request: Dict[str, Any]):
    """Ask a question using RAG Q&A."""
    with log_context(
        operation="api_ask_question",
        question_length=len(request.get("question", "")),
        context_limit=request.get("context_limit", 5),
    ):
        metrics = MetricsCollector("api_ask_question")
        metrics.start()

        server = get_server()

        question = request.get("question", "").strip()
        context_limit = request.get("context_limit", 5)

        metrics.add_metric("question_length", len(question))
        metrics.add_metric("raw_context_limit", context_limit)

        # Validate question
        if not question:
            log_event(
                "api_ask_question_empty_question",
                {"request_keys": list(request.keys())},
            )
            metrics.set_error(ValueError("Empty question"))
            metrics.report("api_ask_question_failed")
            raise HTTPException(status_code=400, detail="Question is required")

        if len(question) < 3:
            log_event(
                "api_ask_question_too_short",
                {"question_length": len(question), "question_preview": question[:50]},
            )
            metrics.set_error(ValueError("Question too short"))
            metrics.report("api_ask_question_failed")
            raise HTTPException(
                status_code=400, detail="Question must be at least 3 characters long"
            )

        # Convert and validate context_limit
        if isinstance(context_limit, str):
            try:
                context_limit = int(context_limit)
            except ValueError:
                log_event(
                    "api_ask_question_invalid_context_limit",
                    {
                        "context_limit_str": context_limit,
                        "question_preview": question[:50],
                    },
                )
                metrics.set_error(ValueError("Invalid context_limit format"))
                metrics.report("api_ask_question_failed")
                raise HTTPException(
                    status_code=400, detail="context_limit must be a number"
                ) from None

        if context_limit < 1 or context_limit > 20:
            log_event(
                "api_ask_question_context_limit_out_of_range",
                {"context_limit": context_limit, "question_preview": question[:50]},
            )
            metrics.set_error(ValueError("context_limit out of range"))
            metrics.report("api_ask_question_failed")
            raise HTTPException(
                status_code=400, detail="context_limit must be between 1 and 20"
            )

        metrics.add_metric("validated_context_limit", context_limit)

        log_event(
            "api_ask_question_started",
            {
                "question_preview": question[:100],
                "question_length": len(question),
                "context_limit": context_limit,
            },
        )

        try:
            # Use the llamaindex.query tool directly instead of query_agent
            result = await server.execute_tool(
                "llamaindex.query",
                {
                    "question": question,
                    "similarity_top_k": context_limit,
                    "response_mode": "tree_summarize",
                },
            )

            if result.get("success"):
                # Transform the result to match the expected format for the UI
                tool_result = result["result"]
                answer = tool_result.get("answer", "")
                confidence = tool_result.get("confidence", 0.0)
                sources = tool_result.get("sources", [])

                # Create citations with proper validation
                citations = []
                for source in sources:
                    snippet = source.get("text", "")[:200] if source.get("text") else ""
                    citations.append(
                        {
                            "doc_id": source.get("document_id", ""),
                            "title": source.get("title", "Unknown Document"),
                            "snippet": snippet,
                            "score": source.get("score", 0.0),
                        }
                    )

                final_response = {
                    "answer": answer,
                    "confidence": confidence,
                    "citations": citations,
                    "method": tool_result.get("method", "llamaindex_tool"),
                    "context_length": len(citations),
                }

                metrics.add_metric("answer_length", len(answer))
                metrics.add_metric("confidence", confidence)
                metrics.add_metric("citations_count", len(citations))
                metrics.set_success(True)
                metrics.report("api_ask_question_completed")

                log_event(
                    "api_ask_question_successful",
                    {
                        "question_preview": question[:50],
                        "answer_length": len(answer),
                        "confidence": confidence,
                        "citations_count": len(citations),
                        "method": tool_result.get("method"),
                    },
                )

                return final_response
            else:
                error = result.get("error", "Q&A tool failed")
                metrics.set_error(RuntimeError(error))
                metrics.report("api_ask_question_failed")

                log_event(
                    "api_ask_question_tool_failed",
                    {
                        "error": error,
                        "question_preview": question[:50],
                        "context_limit": context_limit,
                    },
                )
                raise HTTPException(status_code=500, detail=error)

        except HTTPException:
            raise
        except Exception as e:
            metrics.set_error(e)
            metrics.report("api_ask_question_failed")

            log_event(
                "api_ask_question_exception",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "question_preview": question[:50],
                    "context_limit": context_limit,
                },
            )
            raise HTTPException(status_code=500, detail=str(e)) from None
