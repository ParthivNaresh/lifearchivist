"""
LlamaIndex query tool for Q&A functionality.
"""

from typing import Any, Dict

from lifearchivist.tools.base import BaseTool, ToolMetadata
from lifearchivist.utils.logging import track


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
        operation="llamaindex_query"
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

        try:
            # Use the LlamaIndex service query method
            result = await self.llamaindex_service.query(
                question=question,
                similarity_top_k=similarity_top_k,
                response_mode=response_mode,
            )

            # Transform the result to match expected output schema
            transformed_result = self._transform_query_result(result, question)
            return transformed_result

        except Exception as e:
            return self._empty_response(f"Query failed: {str(e)}")

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
        if any(phrase in answer.lower() for phrase in error_phrases):
            confidence -= 0.3

        # Ensure confidence is between 0 and 1
        return max(0.0, min(1.0, confidence))

    def _empty_response(self, error_message: str) -> Dict[str, Any]:
        """Return empty response with error message."""
        return {
            "answer": f"I encountered an error: {error_message}",
            "confidence": 0.0,
            "sources": [],
            "method": "llamaindex_error",
            "metadata": {"error": error_message},
        }
