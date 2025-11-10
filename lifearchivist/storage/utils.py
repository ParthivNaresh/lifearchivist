"""
Shared utilities for storage services.

This module provides common functionality used across multiple storage services,
following DRY principles and ensuring consistency.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lifearchivist.utils.logging import log_event
from lifearchivist.utils.result import Failure


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

            if not MetadataFilterUtils._check_filter_value(metadata[key], value):
                return False

        return True

    @staticmethod
    def _check_filter_value(meta_val: Any, filter_val: Any) -> bool:
        """
        Check if a metadata value matches a filter value.

        Args:
            meta_val: Metadata value to check
            filter_val: Filter value to match against

        Returns:
            True if value matches filter
        """
        if isinstance(filter_val, list):
            return bool(meta_val in filter_val)

        if isinstance(filter_val, dict):
            return MetadataFilterUtils._check_operators(meta_val, filter_val)

        return bool(meta_val == filter_val)

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
        operator_checks = {
            "$gte": lambda v, ov: v >= ov,
            "$lte": lambda v, ov: v <= ov,
            "$gt": lambda v, ov: v > ov,
            "$lt": lambda v, ov: v < ov,
            "$ne": lambda v, ov: v != ov,
            "$in": lambda v, ov: v in ov,
            "$nin": lambda v, ov: v not in ov,
        }

        for op, op_value in operators.items():
            if op == "$exists":
                continue

            if op in operator_checks:
                if not operator_checks[op](value, op_value):
                    return False
            else:
                MetadataFilterUtils._log_unknown_operator(op, op_value)

        return True

    @staticmethod
    def _log_unknown_operator(op: str, op_value: Any) -> None:
        """
        Log warning for unknown operator.

        Args:
            op: Operator name
            op_value: Operator value
        """
        import logging

        from lifearchivist.utils.logging import log_event

        log_event(
            "unknown_filter_operator",
            {"operator": op, "value": op_value},
            level=logging.WARNING,
        )


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


class FolderWatchUtils:
    """Utility class for folder watch operations."""

    @staticmethod
    def validate_folder_path(path: Path) -> None:
        """
        Validate folder path for watching.

        Args:
            path: Path to validate

        Raises:
            ValueError: If path is invalid
        """
        if not path.exists():
            raise ValueError(f"Folder does not exist: {path}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

    @staticmethod
    async def cleanup_failed_add(
        folder_id: str,
        watched_folders: Dict[str, Any],
        store: Any,
        watching_started: bool,
        redis_persisted: bool,
        stop_watching_func: Any,
    ) -> None:
        """
        Cleanup after failed folder add operation.

        Args:
            folder_id: Folder ID to cleanup
            watched_folders: Dictionary of watched folders
            store: Redis store instance
            watching_started: Whether watching was started
            redis_persisted: Whether Redis persistence succeeded
            stop_watching_func: Function to stop watching
        """
        import logging

        logger = logging.getLogger(__name__)

        if watching_started:
            try:
                stop_watching_func(folder_id)
            except Exception as stop_err:
                logger.error(f"Error stopping watcher during cleanup: {stop_err}")

        if redis_persisted:
            try:
                await store.remove_folder(folder_id)
            except Exception as redis_err:
                logger.error(f"Error removing from Redis during cleanup: {redis_err}")

        if folder_id in watched_folders:
            del watched_folders[folder_id]


class BM25ResultEnricher:
    """Utility class for enriching BM25 search results."""

    @staticmethod
    async def get_document_metadata(
        doc_tracker: Any,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get document metadata from tracker.

        Args:
            doc_tracker: Document tracker instance
            document_id: Document ID

        Returns:
            Metadata dictionary or None
        """
        if not doc_tracker:
            return None

        try:
            result = await doc_tracker.get_full_metadata(document_id)
            return dict(result) if result is not None else None
        except Exception:
            return None

    @staticmethod
    async def get_text_preview(
        doc_tracker: Any,
        index: Any,
        document_id: str,
        text_getter: Any,
    ) -> str:
        """
        Get text preview from first node.

        Args:
            doc_tracker: Document tracker instance
            index: Index instance
            document_id: Document ID
            text_getter: Function to get text from node

        Returns:
            Text preview string
        """
        if not doc_tracker or not index:
            return ""

        try:
            node_ids = await doc_tracker.get_node_ids(document_id)
            if node_ids:
                result = text_getter(node_ids[0])
                return str(result) if result is not None else ""
        except Exception:
            pass

        return ""

    @staticmethod
    def create_enriched_result(
        document_id: str,
        score: float,
        metadata: Dict[str, Any],
        text_preview: str,
        node_id: Optional[str],
    ) -> Dict[str, Any]:
        """
        Create enriched BM25 result dictionary.

        Args:
            document_id: Document ID
            score: BM25 score
            metadata: Document metadata
            text_preview: Text preview
            node_id: Node ID

        Returns:
            Enriched result dictionary
        """
        truncated_text = (
            text_preview[:500] + "..." if len(text_preview) > 500 else text_preview
        )

        return {
            "document_id": document_id,
            "text": truncated_text,
            "score": score,
            "metadata": metadata,
            "node_id": node_id,
            "search_type": "keyword",
        }


class SearchResultProcessor:
    """Utility class for processing search results."""

    @staticmethod
    def filter_by_threshold(
        nodes: List[Any],
        similarity_threshold: float,
    ) -> tuple[List[Any], int]:
        """
        Filter nodes by similarity threshold.

        Args:
            nodes: List of nodes to filter
            similarity_threshold: Minimum similarity score

        Returns:
            Tuple of (filtered_nodes, nodes_below_threshold_count)
        """
        filtered_nodes = []
        nodes_below_threshold = 0

        for node in nodes:
            score = float(node.score) if node.score else 0.0
            if score >= similarity_threshold:
                filtered_nodes.append(node)
            else:
                nodes_below_threshold += 1

        return filtered_nodes, nodes_below_threshold

    @staticmethod
    def extract_node_data(
        node: Any,
    ) -> tuple[float, Dict[str, Any], str, Optional[str]]:
        """
        Extract data from a node.

        Args:
            node: Node to extract data from

        Returns:
            Tuple of (score, metadata, text, node_id)
        """
        score = float(node.score) if node.score else 0.0
        metadata = node.node.metadata if hasattr(node.node, "metadata") else {}
        text = node.node.text if hasattr(node.node, "text") else ""
        node_id = node.node.id_ if hasattr(node.node, "id_") else None

        return score, metadata, text, node_id

    @staticmethod
    def create_search_result(
        document_id: str,
        text: str,
        score: float,
        metadata: Dict[str, Any],
        node_id: Optional[str],
        search_type: str,
    ) -> Dict[str, Any]:
        """
        Create a standardized search result dictionary.

        Args:
            document_id: Document ID
            text: Text content
            score: Similarity score
            metadata: Document metadata
            node_id: Node ID
            search_type: Type of search performed

        Returns:
            Search result dictionary
        """
        truncated_text = text[:500] + "..." if len(text) > 500 else text

        return {
            "document_id": document_id,
            "text": truncated_text,
            "score": score,
            "metadata": metadata,
            "node_id": node_id,
            "search_type": search_type,
        }

    @staticmethod
    def calculate_avg_score(results: List[Dict[str, Any]]) -> float:
        """
        Calculate average score from results.

        Args:
            results: List of search results

        Returns:
            Average score
        """
        if not results:
            return 0.0
        return float(sum(r["score"] for r in results) / len(results))


class MetadataUpdateHandler:
    """Utility class for handling metadata updates."""

    @staticmethod
    def merge_list_fields(
        existing_value: Any,
        new_value: Any,
        field_name: str,
    ) -> Any:
        """
        Merge list fields with appropriate logic.

        Args:
            existing_value: Existing field value
            new_value: New field value
            field_name: Name of the field

        Returns:
            Merged value
        """
        if not isinstance(new_value, list):
            return new_value

        if not isinstance(existing_value, list):
            return new_value

        if field_name == "tags":
            return list(set(existing_value + new_value))
        else:
            return existing_value + new_value

    @staticmethod
    def merge_metadata_fields(
        old_metadata: Optional[Dict[str, Any]],
        metadata_updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge metadata updates with existing metadata.

        Args:
            old_metadata: Existing metadata
            metadata_updates: New metadata fields

        Returns:
            Merged metadata dictionary
        """
        merged = old_metadata.copy() if old_metadata else {}

        list_fields = {"content_dates", "tags", "provenance"}

        for key, value in metadata_updates.items():
            if key in list_fields and isinstance(value, list):
                existing = merged.get(key, [])
                merged[key] = MetadataUpdateHandler.merge_list_fields(
                    existing, value, key
                )
            else:
                merged[key] = value

        return merged

    @staticmethod
    def serialize_updates(
        metadata: Dict[str, Any],
        update_keys: List[str],
        serializer: Any,
    ) -> Dict[str, str]:
        """
        Serialize metadata updates for Redis storage.

        Args:
            metadata: Full metadata dictionary
            update_keys: Keys to serialize
            serializer: Serialization function

        Returns:
            Dictionary of serialized values
        """
        return {k: serializer(metadata[k]) for k in update_keys if k in metadata}


class ContextBuilder:
    """Utility class for building query context."""

    @staticmethod
    async def retrieve_from_search_service(
        search_service: Any,
        question: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> Tuple[
        Optional[List[Dict[str, Any]]],
        Optional[Failure[str]],
    ]:
        """
        Retrieve chunks using search service.

        Args:
            search_service: Search service instance
            question: Query question
            top_k: Number of results
            filters: Optional metadata filters

        Returns:
            Tuple of (source_chunks, error_result) where error_result is a Failure if retrieval failed
        """
        from lifearchivist.utils.logging import log_event

        log_event(
            "context_retrieval_method",
            {"method": "search_service"},
            level=logging.DEBUG,
        )

        search_result = await search_service.semantic_search(
            query=question,
            top_k=top_k,
            similarity_threshold=0.45,
            filters=filters,
        )

        if search_result.is_failure():
            log_event(
                "context_search_failed",
                {"error": str(search_result.error)},
                level=logging.WARNING,
            )
            return None, search_result

        search_results = search_result.value
        source_chunks = []

        for result in search_results:
            source_chunks.append(
                {
                    "text": result.get("text", ""),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("metadata", {}),
                    "node_id": result.get("node_id"),
                    "document_id": result.get("document_id", "unknown"),
                }
            )

        return source_chunks, None

    @staticmethod
    def retrieve_from_query_engine(
        query_engine: Any,
        question: str,
        filters: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks using query engine retriever.

        Args:
            query_engine: Query engine instance
            question: Query question
            filters: Optional metadata filters

        Returns:
            List of source chunks
        """
        from llama_index.core import QueryBundle

        from lifearchivist.utils.logging import log_event

        log_event(
            "context_retrieval_method",
            {"method": "query_engine_retriever"},
            level=logging.DEBUG,
        )

        retriever = query_engine.retriever
        nodes = retriever.retrieve(QueryBundle(query_str=question))

        source_chunks = []
        for node in nodes:
            if not hasattr(node, "node"):
                continue

            text = node.node.text if hasattr(node.node, "text") else ""
            metadata = node.node.metadata if hasattr(node.node, "metadata") else {}

            if filters and not MetadataFilterUtils.matches_filters(metadata, filters):
                continue

            source_chunks.append(
                {
                    "text": text,
                    "score": float(node.score) if node.score else 0.0,
                    "metadata": metadata,
                    "node_id": node.node.id_ if hasattr(node.node, "id_") else None,
                    "document_id": metadata.get("document_id", "unknown"),
                }
            )

        return source_chunks

    @staticmethod
    async def enrich_chunks_metadata(
        source_chunks: List[Dict[str, Any]],
        metadata_service: Any,
    ) -> List[Dict[str, Any]]:
        """
        Enrich source chunks with full metadata.

        Args:
            source_chunks: List of source chunks
            metadata_service: Metadata service instance

        Returns:
            Enriched source chunks
        """
        from lifearchivist.utils.logging import log_event

        if not metadata_service:
            return source_chunks

        enriched_chunks = []
        for chunk in source_chunks:
            enriched_chunk = chunk.copy()
            document_id = chunk.get("document_id")

            if document_id and document_id != "unknown":
                try:
                    meta_result = await metadata_service.get_full_document_metadata(
                        document_id
                    )

                    if not meta_result.is_failure():
                        full_metadata = meta_result.unwrap()
                        enriched_metadata = {
                            **full_metadata,
                            **chunk.get("metadata", {}),
                        }
                        enriched_chunk["metadata"] = enriched_metadata

                        if "theme" in enriched_metadata:
                            enriched_chunk["theme"] = enriched_metadata["theme"]

                except Exception as e:
                    log_event(
                        "metadata_enrichment_failed",
                        {"document_id": document_id, "error": str(e)},
                        level=logging.DEBUG,
                    )

            enriched_chunks.append(enriched_chunk)

        return enriched_chunks


class DocumentMetricsCollector:
    """Utility class for collecting document metrics."""

    @staticmethod
    def calculate_chunk_statistics(
        chunk_sizes: List[int],
        word_counts: List[int],
    ) -> Dict[str, Any]:
        """
        Calculate statistics from chunk sizes and word counts.

        Args:
            chunk_sizes: List of chunk sizes in characters
            word_counts: List of word counts per chunk

        Returns:
            Dictionary of calculated statistics
        """
        num_chunks = len(chunk_sizes)

        if num_chunks == 0:
            return {
                "total_chars": 0,
                "total_words": 0,
                "num_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
                "avg_word_count": 0,
            }

        total_chars = sum(chunk_sizes)
        total_words = sum(word_counts)
        avg_chunk_size = total_chars / num_chunks
        avg_word_count = total_words / num_chunks

        return {
            "total_chars": total_chars,
            "total_words": total_words,
            "num_chunks": num_chunks,
            "avg_chunk_size": round(avg_chunk_size, 2),
            "min_chunk_size": min(chunk_sizes),
            "max_chunk_size": max(chunk_sizes),
            "avg_word_count": round(avg_word_count, 2),
        }

    @staticmethod
    def create_empty_metrics() -> Dict[str, Any]:
        """
        Create empty metrics structure.

        Returns:
            Dictionary with zero values for all metrics
        """
        return {
            "total_chars": 0,
            "total_words": 0,
            "num_chunks": 0,
            "chunks_preview": [],
            "processing_info": {
                "total_chars": 0,
                "total_words": 0,
                "num_chunks": 0,
                "avg_chunk_size": 0,
                "min_chunk_size": 0,
                "max_chunk_size": 0,
                "avg_word_count": 0,
            },
        }


class ChunkInfoBuilder:
    """Utility class for building chunk information dictionaries."""

    @staticmethod
    def extract_metadata_from_payload(
        payload: Dict[str, Any],
        keys: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Extract metadata from Qdrant payload.

        Args:
            payload: Qdrant point payload
            keys: List of keys to extract (None = default keys)

        Returns:
            Dictionary of extracted metadata
        """
        if keys is None:
            keys = [
                "document_id",
                "title",
                "mime_type",
                "status",
                "theme",
                "uploaded_date",
                "file_hash_short",
            ]

        metadata = {}
        for key in keys:
            if key in payload:
                metadata[key] = payload[key]

        return metadata

    @staticmethod
    def parse_node_content(
        payload: Dict[str, Any],
    ) -> tuple[Optional[int], Optional[int], Dict[str, Any]]:
        """
        Parse _node_content from Qdrant payload.

        Args:
            payload: Qdrant point payload

        Returns:
            Tuple of (start_char, end_char, relationships)
        """
        start_char = None
        end_char = None
        relationships = {}

        try:
            import json

            if "_node_content" in payload:
                node_data = json.loads(payload["_node_content"])

                start_char = node_data.get("start_char_idx")
                end_char = node_data.get("end_char_idx")

                if "relationships" in node_data:
                    for rel_type, rel_info in node_data["relationships"].items():
                        if isinstance(rel_info, dict):
                            relationships[rel_type] = {
                                "node_id": rel_info.get("node_id"),
                            }
        except Exception as e:
            log_event(
                "node_content_parse_error",
                {"error": str(e)},
                level=logging.DEBUG,
            )

        return start_char, end_char, relationships

    @staticmethod
    def build_chunk_info(
        point_id: str,
        text: str,
        chunk_index: int,
        metadata: Dict[str, Any],
        start_char: Optional[int] = None,
        end_char: Optional[int] = None,
        relationships: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build enriched chunk information dictionary.

        Args:
            point_id: Qdrant point ID
            text: Chunk text content
            chunk_index: Index of chunk in document
            metadata: Chunk metadata
            start_char: Start character index
            end_char: End character index
            relationships: Node relationships

        Returns:
            Enriched chunk information dictionary
        """
        chunk_info = {
            "chunk_index": chunk_index,
            "node_id": point_id,
            "text": text,
            "text_length": len(text),
            "word_count": len(text.split()),
            "metadata": metadata,
            "relationships": relationships or {},
        }

        if start_char is not None:
            chunk_info["start_char"] = start_char
        if end_char is not None:
            chunk_info["end_char"] = end_char

        return chunk_info
