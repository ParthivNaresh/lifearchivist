"""
Search service for document retrieval operations.

This module provides a clean interface for all search-related functionality,
including semantic, keyword, and hybrid search capabilities.

All methods return Result types for explicit error handling.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from lifearchivist.storage.utils import MetadataFilterUtils
from lifearchivist.utils.result import (
    FailurePayload,
    Result,
    Success,
    fail,
)

from ..utils.logx import log_event, track


class SearchService(ABC):
    """Abstract base class for search services with Result types."""

    @abstractmethod
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Perform semantic search using vector similarity.

        Args:
            query: Search query text
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            filters: Optional metadata filters

        Returns:
            Success with list of search results, or Failure with error
        """
        pass

    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Perform keyword-based search.

        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            Success with list of search results, or Failure with error
        """
        pass

    @abstractmethod
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Perform hybrid search combining semantic and keyword search.

        Args:
            query: Search query text
            top_k: Number of results to return
            semantic_weight: Weight for semantic search (0-1)
            filters: Optional metadata filters

        Returns:
            Success with list of combined results, or Failure with error
        """
        pass

    @abstractmethod
    async def retrieve_similar(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Retrieve similar documents using vector search.

        Args:
            query: Search query text
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            Success with list of similar documents, or Failure with error
        """
        pass


class LlamaIndexSearchService(SearchService):
    """
    Search service implementation using LlamaIndex and Qdrant.

    This service handles all search operations including semantic,
    keyword, and hybrid search using the LlamaIndex framework.
    """

    def __init__(
        self,
        bm25_service=None,
        doc_tracker=None,
        qdrant_client=None,
    ):
        """
        Initialize the search service.

        Args:
            bm25_service: BM25IndexService for keyword search
            doc_tracker: Document tracker for metadata enrichment
            qdrant_client: QdrantClient for direct vector operations
        """
        self.bm25_service = bm25_service
        self.doc_tracker = doc_tracker
        self.qdrant_client = qdrant_client

    @track(operation="semantic_search")
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Perform semantic search using vector similarity.

        Uses embeddings to find semantically similar documents.

        Returns:
            Success with list of search results, or Failure with error
        """
        from llama_index.core import Settings

        if not self.qdrant_client:
            log_event(
                "semantic_search_skipped",
                {"reason": "no_qdrant_client"},
                level=logging.DEBUG,
            )
            return fail(
                FailurePayload(
                    message="Qdrant client not available",
                    error_type="ServiceUnavailable",
                    status_code=503,
                    recoverable=True,
                    details={"service": "semantic_search"},
                )
            )

        try:
            log_event(
                "semantic_search_started",
                {
                    "query_length": len(query),
                    "query_preview": query[:50],
                    "top_k": top_k,
                    "similarity_threshold": similarity_threshold,
                    "has_filters": bool(filters),
                    "method": "direct_qdrant",
                },
            )

            query_embedding = Settings.embed_model.get_query_embedding(query)

            search_results = self.qdrant_client.search(
                collection_name="lifearchivist",
                query_vector=query_embedding,
                limit=top_k * 2,
                with_payload=True,
                with_vectors=False,
            )

            results = []
            nodes_below_threshold = 0

            for point in search_results:
                score = float(point.score)

                if score < similarity_threshold:
                    nodes_below_threshold += 1
                    continue

                payload = point.payload or {}

                from lifearchivist.storage.utils import QdrantNodeUtils

                text = QdrantNodeUtils.extract_text_from_node(payload)
                document_id = payload.get("document_id", "unknown")
                node_id = point.id

                if filters and not MetadataFilterUtils.matches_filters(
                    payload, filters
                ):
                    continue

                result = {
                    "document_id": document_id,
                    "text": text,
                    "score": score,
                    "metadata": payload,
                    "node_id": str(node_id),
                    "search_type": "semantic",
                }
                results.append(result)

                if len(results) >= top_k:
                    break

            avg_score = (
                sum(r["score"] for r in results) / len(results) if results else 0
            )

            log_event(
                "semantic_search_completed",
                {
                    "points_retrieved": len(search_results),
                    "points_above_threshold": len(results),
                    "points_below_threshold": nodes_below_threshold,
                    "threshold": similarity_threshold,
                    "avg_score": avg_score,
                    "method": "direct_qdrant",
                },
            )

            return Success(results)

        except Exception as e:
            log_event(
                "semantic_search_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Semantic search failed: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={
                        "query": query[:50],
                        "error_type": type(e).__name__,
                    },
                )
            )

    @track(operation="keyword_search")
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Perform keyword-based search using BM25.

        Uses BM25 ranking algorithm for keyword-based document retrieval.

        Returns:
            Success with list of search results, or Failure with error
        """
        if not self.bm25_service:
            log_event(
                "keyword_search_no_bm25",
                {"reason": "BM25 service not available"},
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message="BM25 search service not available",
                    error_type="ServiceUnavailable",
                    status_code=503,
                    recoverable=True,
                    details={"service": "keyword_search"},
                )
            )

        log_event(
            "keyword_search_started",
            {
                "query": query[:50],
                "top_k": top_k,
                "has_filters": bool(filters),
            },
        )

        try:
            # Get BM25 results (document_id, score pairs)
            bm25_results = await self.bm25_service.search(
                query=query,
                top_k=top_k * 3,  # Get more for filtering
                min_score=0.0,
            )

            if not bm25_results:
                log_event(
                    "keyword_search_no_results",
                    {"query": query[:50]},
                    level=logging.DEBUG,
                )
                return Success([])

            # Enrich results with metadata and text
            enriched_results: List[Dict[str, Any]] = await self._enrich_bm25_results(
                bm25_results, filters
            )

            # Apply pagination
            final_results: List[Dict[str, Any]] = enriched_results[:top_k]

            log_event(
                "keyword_search_completed",
                {
                    "bm25_results": len(bm25_results),
                    "after_filters": len(enriched_results),
                    "returned": len(final_results),
                },
            )

            return Success(final_results)

        except Exception as e:
            log_event(
                "keyword_search_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Keyword search failed: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={
                        "query": query[:50],
                        "error_type": type(e).__name__,
                    },
                )
            )

    async def _enrich_bm25_results(
        self,
        bm25_results: List[tuple],
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Enrich BM25 results with metadata and text from Qdrant.

        Args:
            bm25_results: List of (document_id, score) tuples from BM25
            filters: Optional metadata filters to apply

        Returns:
            List of enriched result dictionaries
        """
        from lifearchivist.storage.utils import BM25ResultEnricher

        enriched = []

        for document_id, score in bm25_results:
            try:
                metadata = await BM25ResultEnricher.get_document_metadata(
                    self.doc_tracker, document_id
                )
                if not metadata:
                    continue

                if filters and not MetadataFilterUtils.matches_filters(
                    metadata, filters
                ):
                    continue

                text_preview = await BM25ResultEnricher.get_text_preview(
                    self.doc_tracker, None, document_id, self._get_text_from_node
                )

                node_ids = (
                    await self.doc_tracker.get_node_ids(document_id)
                    if self.doc_tracker
                    else None
                )
                node_id = node_ids[0] if node_ids else None

                result = BM25ResultEnricher.create_enriched_result(
                    document_id, score, metadata, text_preview, node_id
                )
                enriched.append(result)

            except Exception as e:
                log_event(
                    "bm25_result_enrichment_failed",
                    {"document_id": document_id, "error": str(e)},
                    level=logging.DEBUG,
                )
                continue

        return enriched

    def _get_text_from_node(self, node_id: str) -> str:
        """
        Get text content from a node using Qdrant.

        Args:
            node_id: Node ID to retrieve

        Returns:
            Text content of the node
        """
        try:
            # Access Qdrant client through index
            if not self.qdrant_client:
                return ""

            qdrant_client = self.qdrant_client

            # Retrieve node from Qdrant
            from lifearchivist.storage.utils import QdrantNodeUtils

            points = qdrant_client.retrieve(
                collection_name="lifearchivist",
                ids=[node_id],
                with_payload=True,
                with_vectors=False,
            )

            if points and len(points) > 0:
                text = QdrantNodeUtils.extract_text_from_node(points[0].payload)
                return text if isinstance(text, str) and text is not None else ""

        except Exception as e:
            log_event(
                "node_text_retrieval_failed",
                {"node_id": node_id, "error": str(e)},
                level=logging.DEBUG,
            )

        return ""

    @track(operation="hybrid_search")
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Perform hybrid search combining semantic and keyword search.

        Combines results from both search methods using weighted scoring.

        Returns:
            Success with list of combined results, or Failure with error
        """
        if not 0 <= semantic_weight <= 1:
            return fail(
                FailurePayload(
                    message="semantic_weight must be between 0 and 1",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={"semantic_weight": semantic_weight},
                )
            )

        log_event(
            "hybrid_search_started",
            {
                "query": query[:50],
                "top_k": top_k,
                "semantic_weight": semantic_weight,
                "keyword_weight": 1 - semantic_weight,
                "has_filters": bool(filters),
            },
        )

        try:
            # Get results from both search methods (both return Result now)
            semantic_result = await self.semantic_search(
                query=query,
                top_k=top_k * 2,
                similarity_threshold=0.3,
                filters=filters,
            )

            # If semantic search failed, return the failure
            if semantic_result.is_failure():
                return semantic_result  # Failure[..., FailurePayload]

            keyword_result = await self.keyword_search(
                query=query,
                top_k=top_k * 2,
                filters=filters,
            )
            if keyword_result.is_failure():
                return keyword_result  # Failure[..., FailurePayload]

            # Unwrap successful results
            semantic_results: List[Dict[str, Any]] = semantic_result.unwrap()
            keyword_results: List[Dict[str, Any]] = keyword_result.unwrap()

            combined_results: List[Dict[str, Any]] = self._combine_search_results(
                semantic_results,
                keyword_results,
                semantic_weight,
            )

            combined_results.sort(key=lambda x: x["score"], reverse=True)
            final_results: List[Dict[str, Any]] = combined_results[:top_k]

            log_event(
                "hybrid_search_completed",
                {
                    "semantic_results": len(semantic_results),
                    "keyword_results": len(keyword_results),
                    "combined_results": len(combined_results),
                    "final_results": len(final_results),
                },
            )

            return Success(final_results)

        except Exception as e:
            log_event(
                "hybrid_search_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Hybrid search failed: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={
                        "query": query[:50],
                        "error_type": type(e).__name__,
                    },
                )
            )

    async def retrieve_similar(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Retrieve similar documents using vector search.

        This is essentially semantic search without additional filters.
        Maintained for backward compatibility.

        Returns:
            Success with list of similar documents, or Failure with error
        """
        return await self.semantic_search(
            query=query,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
            filters=None,
        )

    def _combine_search_results(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        semantic_weight: float,
    ) -> List[Dict[str, Any]]:
        """
        Combine results from semantic and keyword search.

        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            semantic_weight: Weight for semantic scores

        Returns:
            Combined results with weighted scores
        """
        keyword_weight = 1 - semantic_weight
        combined = {}

        # Process semantic results
        for result in semantic_results:
            doc_id = result["document_id"]
            combined[doc_id] = result.copy()
            combined[doc_id]["semantic_score"] = result["score"]
            combined[doc_id]["keyword_score"] = 0
            combined[doc_id]["score"] = result["score"] * semantic_weight
            combined[doc_id]["search_type"] = "hybrid"

        # Process keyword results
        for result in keyword_results:
            doc_id = result["document_id"]
            if doc_id in combined:
                # Document appears in both results
                combined[doc_id]["keyword_score"] = result["score"]
                combined[doc_id]["score"] = (
                    combined[doc_id]["semantic_score"] * semantic_weight
                    + result["score"] * keyword_weight
                )
            else:
                # Document only in keyword results
                combined[doc_id] = result.copy()
                combined[doc_id]["semantic_score"] = 0
                combined[doc_id]["keyword_score"] = result["score"]
                combined[doc_id]["score"] = result["score"] * keyword_weight
                combined[doc_id]["search_type"] = "hybrid"

        return list(combined.values())

    async def get_document_neighbors(
        self,
        document_text: str,
        document_id: str,
        top_k: int = 10,
    ) -> Result[List[Dict[str, Any]], FailurePayload]:
        """
        Get semantically similar documents for a given document.

        Args:
            document_text: Text content of the document
            document_id: ID of the document to exclude from results
            top_k: Number of similar documents to return

        Returns:
            Success with list of similar documents, or Failure with error
        """
        try:
            # Use the document's text as query (truncated to avoid token limits)
            query_text = document_text[:2000]  # Use first 2000 chars as query

            # Retrieve similar documents with lower threshold
            similar_result = await self.semantic_search(
                query=query_text,
                top_k=top_k + 10,  # Get extra to filter out self
                similarity_threshold=0.3,  # Lower threshold for neighbor search
            )

            # If search failed, return the failure
            if similar_result.is_failure():
                return similar_result  # already Result[..., FailurePayload]

            # Unwrap successful result
            similar_docs: List[Dict[str, Any]] = similar_result.unwrap()

            # Filter out the document itself and format results
            neighbors: List[Dict[str, Any]] = []
            for doc in similar_docs:
                if doc["document_id"] != document_id:
                    neighbors.append(doc)
                    if len(neighbors) >= top_k:
                        break

            log_event(
                "document_neighbors_retrieved",
                {
                    "document_id": document_id,
                    "neighbors_found": len(neighbors),
                    "top_k_requested": top_k,
                },
            )

            return Success(neighbors)

        except Exception as e:
            log_event(
                "document_neighbors_error",
                {
                    "document_id": document_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return fail(
                FailurePayload(
                    message=f"Failed to get document neighbors: {str(e)}",
                    error_type="InternalError",
                    status_code=500,
                    recoverable=False,
                    details={
                        "document_id": document_id,
                        "error_type": type(e).__name__,
                    },
                )
            )
