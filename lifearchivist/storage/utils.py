"""
Shared utilities for storage services.

This module provides common functionality used across multiple storage services,
following DRY principles and ensuring consistency.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from lifearchivist.utils.logging import log_event


class MetadataFilterUtils:
    """Utility class for metadata filtering operations."""

    @staticmethod
    def matches_filters(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Check if metadata matches the provided filters.

        Supports various filter types:
        - Exact match: {"key": "value"}
        - List membership: {"key": ["value1", "value2"]}
        - Range queries: {"key": {"$gte": 10, "$lte": 20}}
        - Operators: $gt, $lt, $gte, $lte, $ne, $in, $nin

        Args:
            metadata: Document metadata to check
            filters: Filter criteria to apply

        Returns:
            True if metadata matches all filters, False otherwise
        """
        if not filters:
            return True

        for key, value in filters.items():
            if key not in metadata:
                return False

            meta_val = metadata[key]

            # Handle different filter types
            if isinstance(value, list):
                # Check if metadata value is in filter list
                if meta_val not in value:
                    return False

            elif isinstance(value, dict):
                # Handle MongoDB-style operators
                if not MetadataFilterUtils._check_operators(meta_val, value):
                    return False

            else:
                # Exact match
                if meta_val != value:
                    return False

        return True

    @staticmethod
    def _check_operators(value: Any, operators: Dict[str, Any]) -> bool:
        """
        Check if a value matches operator-based filters.

        Args:
            value: The value to check
            operators: Dictionary of operators and their values

        Returns:
            True if value matches all operators
        """
        for op, op_value in operators.items():
            if op == "$gte" and value < op_value:
                return False
            elif op == "$lte" and value > op_value:
                return False
            elif op == "$gt" and value <= op_value:
                return False
            elif op == "$lt" and value >= op_value:
                return False
            elif op == "$ne" and value == op_value:
                return False
            elif op == "$in" and value not in op_value:
                return False
            elif op == "$nin" and value in op_value:
                return False
            elif op == "$exists":
                # Special case: check if field exists (already handled by parent)
                pass
            else:
                # Unknown operator, log warning but don't fail
                import logging

                from lifearchivist.utils.logging import log_event

                log_event(
                    "unknown_filter_operator",
                    {"operator": op, "value": op_value},
                    level=logging.WARNING,
                )

        return True


class QdrantNodeUtils:
    """Utility class for extracting data from Qdrant nodes."""

    @staticmethod
    def extract_text_from_node(node_payload: Dict[str, Any]) -> Optional[str]:
        """
        Extract text content from a Qdrant node payload.

        Qdrant stores LlamaIndex nodes with text in the _node_content field
        as a JSON string. This method extracts and parses it.

        Args:
            node_payload: The payload dict from a Qdrant point

        Returns:
            The text content, or None if not found
        """
        try:
            # Check if _node_content exists
            node_content_str = node_payload.get("_node_content")
            if not node_content_str:
                return None

            # Parse the JSON string
            node_data = json.loads(node_content_str)

            # Extract text field
            text = node_data.get("text", "")
            return text if text else None

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            log_event(
                "qdrant_text_extraction_failed",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "has_node_content": "_node_content" in node_payload,
                },
                level=logging.WARNING,
            )
            return None

    @staticmethod
    def extract_text_preview(
        node_payload: Dict[str, Any], max_length: int = 200
    ) -> str:
        """
        Extract a text preview from a Qdrant node payload.

        Args:
            node_payload: The payload dict from a Qdrant point
            max_length: Maximum length of preview

        Returns:
            Text preview (truncated if needed), or empty string
        """
        text = QdrantNodeUtils.extract_text_from_node(node_payload)
        if not text:
            return ""

        if len(text) > max_length:
            return text[:max_length] + "..."
        return text


class ChunkUtils:
    """Utility class for chunk operations."""

    @staticmethod
    def combine_chunks_to_context(
        chunks: List[Dict[str, Any]],
        separator: str = "\n\n---\n\n",
        include_metadata: bool = False,
    ) -> str:
        """
        Combine retrieved chunks into a single context string.

        Args:
            chunks: List of chunk dictionaries with 'text' field
            separator: String to separate chunks
            include_metadata: Whether to include chunk metadata in context

        Returns:
            Combined context string
        """
        if not chunks:
            return ""

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            text = chunk.get("text", "")
            if not text:
                continue

            if include_metadata:
                # Add chunk header with metadata
                doc_id = chunk.get("document_id", "unknown")
                score = chunk.get("score", 0.0)
                header = f"[Chunk {i} | Doc: {doc_id} | Score: {score:.3f}]"
                context_parts.append(f"{header}\n{text}")
            else:
                # Simple numbered chunks
                context_parts.append(f"[Chunk {i}]\n{text}")

        return separator.join(context_parts)


class ConfidenceCalculator:
    """Utility class for calculating confidence scores."""

    @staticmethod
    def calculate_confidence(
        answer: str,
        sources: List[Dict[str, Any]],
        context: str,
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculate a confidence score for a Q&A response.

        Args:
            answer: The generated answer
            sources: List of source documents
            context: The context used for generation
            weights: Optional custom weights for factors

        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not answer or not sources:
            return 0.0

        # Default weights
        if weights is None:
            weights = {
                "source_count": 0.25,
                "source_score": 0.35,
                "answer_length": 0.20,
                "context_length": 0.20,
            }

        confidence = 0.0

        # Factor 1: Number of sources (more sources = higher confidence)
        source_factor = min(len(sources) / 5.0, 1.0)  # Max out at 5 sources
        confidence += source_factor * weights.get("source_count", 0.25)

        # Factor 2: Average relevance score
        if sources:
            avg_score = sum(s.get("score", 0) for s in sources) / len(sources)
            confidence += avg_score * weights.get("source_score", 0.35)

        # Factor 3: Answer completeness (longer answers tend to be more complete)
        answer_factor = min(len(answer) / 500.0, 1.0)  # Max out at 500 chars
        confidence += answer_factor * weights.get("answer_length", 0.20)

        # Factor 4: Context utilization (did we have enough context?)
        context_factor = min(len(context) / 2000.0, 1.0)  # Max out at 2000 chars
        confidence += context_factor * weights.get("context_length", 0.20)

        # Check for error indicators
        error_phrases = [
            "error",
            "failed",
            "unable",
            "cannot",
            "don't have",
            "not found",
            "insufficient",
        ]

        answer_lower = answer.lower()
        if any(phrase in answer_lower for phrase in error_phrases):
            confidence *= 0.5  # Reduce confidence by half if error phrases detected

        return round(min(max(confidence, 0.0), 1.0), 3)


class StorageConstants:
    """Constants used across storage services."""

    # Chunk configuration
    DEFAULT_CHUNK_SIZE = 2600
    DEFAULT_CHUNK_OVERLAP = 200
    DEFAULT_CHUNK_SEPARATOR = "\n\n"

    # Search configuration
    DEFAULT_SIMILARITY_TOP_K = 5
    DEFAULT_SIMILARITY_THRESHOLD = 0.7
    DEFAULT_SEMANTIC_WEIGHT = 0.5

    # Preview configuration
    DEFAULT_TEXT_PREVIEW_LENGTH = 200
    DEFAULT_CONTEXT_PREVIEW_LENGTH = 1000

    # Confidence thresholds
    LOW_CONFIDENCE_THRESHOLD = 0.3
    HIGH_CONFIDENCE_THRESHOLD = 0.7

    # Vector store configuration
    VECTOR_DIMENSION = 384  # all-MiniLM-L6-v2
    COLLECTION_NAME = "lifearchivist"

    # Response modes
    RESPONSE_MODES = ["tree_summarize", "compact", "refine", "simple_summarize"]
