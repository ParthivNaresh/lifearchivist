"""
LlamaIndex query tool for Q&A functionality.
"""

import logging
from typing import Any, Dict

from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.utils.logging import log_event, track


class LlamaIndexQueryTool(BaseTool):
    """Tool for querying LlamaIndex to get AI-generated answers."""

    def __init__(self, llamaindex_service=None):
        super().__init__()
        self.llamaindex_service = llamaindex_service

    def _get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="llamaindex.query",
            description="Query LlamaIndex to get AI-generated answers from document content",
            input_schema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Question to ask about the documents",
                    },
                    "similarity_top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Number of most similar documents to use as context",
                        "default": 5,
                    },
                    "response_mode": {
                        "type": "string",
                        "enum": [
                            "tree_summarize",
                            "compact",
                            "refine",
                            "simple_summarize",
                        ],
                        "description": "Response synthesis mode for answer generation",
                        "default": "tree_summarize",
                    },
                },
                "required": ["question"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "document_id": {"type": "string"},
                                "title": {"type": "string"},
                                "text": {"type": "string"},
                                "score": {"type": "number"},
                            },
                        },
                    },
                    "method": {"type": "string"},
                    "metadata": {"type": "object"},
                },
            },
            async_tool=True,
            idempotent=True,
        )

    @track(
        operation="llamaindex_query",
        include_args=["similarity_top_k", "response_mode"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute LlamaIndex query for Q&A."""
        question = kwargs.get("question", "").strip()
        similarity_top_k = kwargs.get("similarity_top_k", 5)
        response_mode = kwargs.get("response_mode", "tree_summarize")

        if not question:
            return self._empty_response("Question cannot be empty")

        if not self.llamaindex_service:
            return self._empty_response("LlamaIndex service not available")

        # Log query start with context (important for debugging Q&A issues)
        log_event(
            "query_started",
            {
                "question_length": len(question),
                "question_preview": (
                    question[:100] + "..." if len(question) > 100 else question
                ),
                "similarity_top_k": similarity_top_k,
                "response_mode": response_mode,
            },
        )

        try:
            # Use the LlamaIndex service query method
            result = await self.llamaindex_service.query(
                question=question,
                similarity_top_k=similarity_top_k,
                response_mode=response_mode,
            )

            # Check if we got a meaningful response
            answer = result.get("answer", "")
            sources = result.get("sources", [])

            if not answer or "error" in answer.lower():
                log_event(
                    "query_empty_response",
                    {
                        "question_preview": question[:50],
                        "sources_found": len(sources),
                        "answer_preview": answer[:100] if answer else "empty",
                    },
                    level=logging.WARNING,
                )

            # Transform the result to match expected output schema
            transformed_result = self._transform_query_result(result, question)

            # Log successful query with metrics
            log_event(
                "query_completed",
                {
                    "question_length": len(question),
                    "answer_length": len(transformed_result.get("answer", "")),
                    "confidence": transformed_result.get("confidence", 0.0),
                    "sources_count": len(transformed_result.get("sources", [])),
                    "method": transformed_result.get("method", "unknown"),
                },
            )

            return transformed_result

        except Exception as e:
            log_event(
                "query_failed",
                {
                    "question_preview": question[:50],
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return self._empty_response(f"Query failed: {str(e)}")

    @track(
        operation="result_transformation",
        track_performance=True,
        frequency="medium_frequency",
    )
    def _transform_query_result(
        self, result: Dict[str, Any], question: str
    ) -> Dict[str, Any]:
        """Transform LlamaIndex service result to match tool output schema."""
        answer = result.get("answer", "")
        sources = result.get("sources", [])
        method = result.get("method", "llamaindex_rag")
        metadata = result.get("metadata", {})

        # Calculate confidence based on answer quality and sources
        confidence = self._calculate_confidence(answer, sources, question)

        # Transform sources to match expected format
        transformed_sources = []
        for source in sources:
            transformed_source = {
                "document_id": source.get("document_id", ""),
                "title": source.get(
                    "title", source.get("metadata", {}).get("title", "Unknown Document")
                ),
                "text": source.get("text", "")[:500],  # Limit text length
                "score": source.get("score", 0.0),
            }
            transformed_sources.append(transformed_source)

        # Log low confidence results for debugging
        if confidence < 0.3:
            log_event(
                "low_confidence_result",
                {
                    "confidence": confidence,
                    "answer_length": len(answer),
                    "sources_count": len(sources),
                    "avg_source_score": (
                        sum(s.get("score", 0) for s in sources) / len(sources)
                        if sources
                        else 0
                    ),
                },
                level=logging.DEBUG,
            )

        return {
            "answer": answer,
            "confidence": confidence,
            "sources": transformed_sources,
            "method": method,
            "metadata": {
                **metadata,
                "question_length": len(question),
                "original_sources_count": len(sources),
            },
        }

    @track(
        operation="confidence_calculation",
        track_performance=False,  # Fast operation, no need to track
        frequency="high_frequency",  # Called frequently, sample it
    )
    def _calculate_confidence(self, answer: str, sources: list, question: str) -> float:
        """Calculate confidence score based on answer and source quality."""
        if not answer or answer.strip() in [
            "",
            "I don't know",
            "No information available",
        ]:
            return 0.0

        confidence = 0.5  # Base confidence

        # Boost confidence based on answer length (longer answers often more complete)
        if len(answer) > 100:
            confidence += 0.1
        if len(answer) > 300:
            confidence += 0.1

        # Boost confidence based on number of sources
        if len(sources) >= 3:
            confidence += 0.2
        elif len(sources) >= 1:
            confidence += 0.1

        # Boost confidence based on source scores
        if sources:
            avg_source_score = sum(s.get("score", 0) for s in sources) / len(sources)
            confidence += avg_source_score * 0.2

        # Reduce confidence for error-indicating phrases
        error_phrases = [
            "error",
            "failed",
            "unable",
            "cannot",
            "don't have",
            "not found",
            "insufficient",
        ]
        detected_error_phrases = [
            phrase for phrase in error_phrases if phrase in answer.lower()
        ]
        if detected_error_phrases:
            confidence -= 0.3
            # Log when error phrases affect confidence (useful for debugging)
            log_event(
                "confidence_reduced_error_phrases",
                {
                    "detected_phrases": detected_error_phrases,
                    "original_confidence": confidence + 0.3,
                    "adjusted_confidence": confidence,
                },
                level=logging.DEBUG,
            )

        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))

    def _empty_response(self, error_message: str) -> Dict[str, Any]:
        """Return empty response with error message."""
        # Log empty responses as they indicate issues
        log_event(
            "query_empty_response_generated",
            {
                "reason": error_message,
            },
            level=logging.DEBUG,
        )

        return {
            "answer": f"I encountered an error: {error_message}",
            "confidence": 0.0,
            "sources": [],
            "method": "llamaindex_error",
            "metadata": {"error": error_message},
        }
