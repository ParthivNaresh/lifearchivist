"""
Search service for document retrieval operations.

This module provides a clean interface for all search-related functionality,
including semantic, keyword, and hybrid search capabilities.

All methods return Result types for explicit error handling.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever

from lifearchivist.storage.utils import MetadataFilterUtils
from lifearchivist.utils.logging import log_event, track
from lifearchivist.utils.result import (
    Result,
    Success,
    internal_error,
    service_unavailable,
)


class SearchService(ABC):
    """Abstract base class for search services with Result types."""

    @abstractmethod
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], str]:
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
    ) -> Result[List[Dict[str, Any]], str]:
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
    ) -> Result[List[Dict[str, Any]], str]:
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
    ) -> Result[List[Dict[str, Any]], str]:
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
        index: Optional[VectorStoreIndex] = None,
        bm25_service=None,
        doc_tracker=None,
    ):
        """
        Initialize the search service.

        Args:
            index: LlamaIndex VectorStoreIndex instance
            bm25_service: BM25IndexService for keyword search
            doc_tracker: Document tracker for metadata enrichment
        """
        self.index = index
        self.bm25_service = bm25_service
        self.doc_tracker = doc_tracker
        self._setup_retrievers()

    def _setup_retrievers(self):
        """Setup various retrievers for different search modes."""
        if self.index:
            # Default semantic retriever
            self.semantic_retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=10,
            )

    @track(
        operation="semantic_search",
        include_args=["top_k", "similarity_threshold"],
        include_result=True,
        track_performance=True,
        frequency="high_frequency",
    )
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], str]:
        """
        Perform semantic search using vector similarity.

        Uses embeddings to find semantically similar documents.

        Returns:
            Success with list of search results, or Failure with error
        """
        if not self.index:
            log_event(
                "semantic_search_skipped",
                {"reason": "no_index"},
                level=logging.DEBUG,
            )
            return service_unavailable(
                "Search index not available", context={"service": "semantic_search"}
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
                },
            )

            # Update retriever settings
            self.semantic_retriever.similarity_top_k = top_k

            # Retrieve nodes
            nodes = self.semantic_retriever.retrieve(query)

            # Filter by similarity threshold and format results
            results = []
            nodes_below_threshold = 0

            for node in nodes:
                # Qdrant returns scores as cosine similarity (0-1 range)
                score = float(node.score) if node.score else 0.0

                if score >= similarity_threshold:
                    # Extract metadata and text
                    metadata = (
                        node.node.metadata if hasattr(node.node, "metadata") else {}
                    )

                    # Apply metadata filters if provided
                    if filters and not MetadataFilterUtils.matches_filters(
                        metadata, filters
                    ):
                        continue

                    text = node.node.text if hasattr(node.node, "text") else ""

                    # Create result entry
                    result = {
                        "document_id": metadata.get("document_id", "unknown"),
                        "text": text[:500] + "..." if len(text) > 500 else text,
                        "score": score,
                        "metadata": metadata,
                        "node_id": node.node.id_ if hasattr(node.node, "id_") else None,
                        "search_type": "semantic",
                    }
                    results.append(result)
                else:
                    nodes_below_threshold += 1

            log_event(
                "semantic_search_completed",
                {
                    "nodes_retrieved": len(nodes),
                    "nodes_above_threshold": len(results),
                    "nodes_below_threshold": nodes_below_threshold,
                    "threshold": similarity_threshold,
                    "avg_score": (
                        sum(r["score"] for r in results) / len(results)
                        if results
                        else 0
                    ),
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
            return internal_error(
                f"Semantic search failed: {str(e)}",
                context={
                    "query": query[:50],
                    "error_type": type(e).__name__,
                },
            )

    @track(
        operation="keyword_search",
        include_args=["top_k"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], str]:
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
            return service_unavailable(
                "BM25 search service not available",
                context={"service": "keyword_search"},
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
            enriched_results = await self._enrich_bm25_results(bm25_results, filters)

            # Apply pagination
            final_results = enriched_results[:top_k]

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
            return internal_error(
                f"Keyword search failed: {str(e)}",
                context={
                    "query": query[:50],
                    "error_type": type(e).__name__,
                },
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
        enriched = []

        for document_id, score in bm25_results:
            try:
                # Get full metadata from doc_tracker
                if self.doc_tracker:
                    metadata = await self.doc_tracker.get_full_metadata(document_id)
                    if not metadata:
                        continue

                    # Apply filters if provided
                    if filters and not MetadataFilterUtils.matches_filters(
                        metadata, filters
                    ):
                        continue

                    # Get text preview from first node
                    node_ids = await self.doc_tracker.get_node_ids(document_id)
                    text_preview = ""
                    if node_ids and self.index:
                        # Get text from first chunk
                        text_preview = await self._get_text_from_node(node_ids[0])

                    enriched.append(
                        {
                            "document_id": document_id,
                            "text": (
                                text_preview[:500] + "..."
                                if len(text_preview) > 500
                                else text_preview
                            ),
                            "score": score,
                            "metadata": metadata,
                            "node_id": node_ids[0] if node_ids else None,
                            "search_type": "keyword",
                        }
                    )

            except Exception as e:
                log_event(
                    "bm25_result_enrichment_failed",
                    {
                        "document_id": document_id,
                        "error": str(e),
                    },
                    level=logging.DEBUG,
                )
                continue

        return enriched

    async def _get_text_from_node(self, node_id: str) -> str:
        """
        Get text content from a node using Qdrant.

        Args:
            node_id: Node ID to retrieve

        Returns:
            Text content of the node
        """
        try:
            # Access Qdrant client through index
            if not self.index or not hasattr(self.index, "_vector_store"):
                return ""

            vector_store = self.index._vector_store
            if not hasattr(vector_store, "_client"):
                return ""

            qdrant_client = vector_store._client

            # Retrieve node from Qdrant
            from lifearchivist.storage.utils import QdrantNodeUtils

            points = qdrant_client.retrieve(
                collection_name="lifearchivist",
                ids=[node_id],
                with_payload=True,
                with_vectors=False,
            )

            if points and len(points) > 0:
                return QdrantNodeUtils.extract_text_from_node(points[0].payload)

        except Exception as e:
            log_event(
                "node_text_retrieval_failed",
                {"node_id": node_id, "error": str(e)},
                level=logging.DEBUG,
            )

        return ""

    @track(
        operation="hybrid_search",
        include_args=["top_k", "semantic_weight"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[List[Dict[str, Any]], str]:
        """
        Perform hybrid search combining semantic and keyword search.

        Combines results from both search methods using weighted scoring.

        Returns:
            Success with list of combined results, or Failure with error
        """
        if not 0 <= semantic_weight <= 1:
            return internal_error(
                "semantic_weight must be between 0 and 1",
                context={"semantic_weight": semantic_weight},
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
                similarity_threshold=0.3,  # Lower threshold to get more candidates
                filters=filters,
            )

            # If semantic search failed, return the failure
            if semantic_result.is_failure():
                return semantic_result

            keyword_result = await self.keyword_search(
                query=query,
                top_k=top_k * 2,
                filters=filters,
            )

            # If keyword search failed, return the failure
            if keyword_result.is_failure():
                return keyword_result

            # Unwrap successful results
            semantic_results = semantic_result.value
            keyword_results = keyword_result.value

            # Combine and re-score results
            combined_results = self._combine_search_results(
                semantic_results,
                keyword_results,
                semantic_weight,
            )

            # Sort by combined score and take top_k
            combined_results.sort(key=lambda x: x["score"], reverse=True)
            final_results = combined_results[:top_k]

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
            return internal_error(
                f"Hybrid search failed: {str(e)}",
                context={
                    "query": query[:50],
                    "error_type": type(e).__name__,
                },
            )

    @track(
        operation="retrieve_similar",
        include_args=["top_k", "similarity_threshold"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def retrieve_similar(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
    ) -> Result[List[Dict[str, Any]], str]:
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

    # Filter matching now uses shared utility
    # Removed _matches_filters method - using MetadataFilterUtils.matches_filters instead

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
    ) -> Result[List[Dict[str, Any]], str]:
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
                return similar_result

            # Unwrap successful result
            similar_docs = similar_result.value

            # Filter out the document itself and format results
            neighbors = []
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
            return internal_error(
                f"Failed to get document neighbors: {str(e)}",
                context={
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                },
            )
