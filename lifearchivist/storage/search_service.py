"""
Search service for document retrieval operations.

This module provides a clean interface for all search-related functionality,
including semantic, keyword, and hybrid search capabilities.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever

from lifearchivist.storage.utils import MetadataFilterUtils
from lifearchivist.utils.logging import log_event, track


class SearchService(ABC):
    """Abstract base class for search services."""

    @abstractmethod
    async def semantic_search(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector similarity.

        Args:
            query: Search query text
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            filters: Optional metadata filters

        Returns:
            List of search results with scores and metadata
        """
        pass

    @abstractmethod
    async def keyword_search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search.

        Args:
            query: Search query text
            top_k: Number of results to return
            filters: Optional metadata filters

        Returns:
            List of search results with scores and metadata
        """
        pass

    @abstractmethod
    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword search.

        Args:
            query: Search query text
            top_k: Number of results to return
            semantic_weight: Weight for semantic search (0-1)
            filters: Optional metadata filters

        Returns:
            List of search results with combined scores
        """
        pass

    @abstractmethod
    async def retrieve_similar(
        self,
        query: str,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar documents using vector search.

        Args:
            query: Search query text
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar documents with scores
        """
        pass


class LlamaIndexSearchService(SearchService):
    """
    Search service implementation using LlamaIndex and Qdrant.

    This service handles all search operations including semantic,
    keyword, and hybrid search using the LlamaIndex framework.
    """

    def __init__(self, index: Optional[VectorStoreIndex] = None):
        """
        Initialize the search service.

        Args:
            index: LlamaIndex VectorStoreIndex instance
        """
        self.index = index
        self._setup_retrievers()

    def _setup_retrievers(self):
        """Setup various retrievers for different search modes."""
        if self.index:
            # Default semantic retriever
            self.semantic_retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=10,
            )

            # We'll add more retrievers as needed
            # For now, LlamaIndex primarily supports semantic search
            # Keyword search would require additional setup with BM25 or similar

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
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector similarity.

        Uses embeddings to find semantically similar documents.
        """
        if not self.index:
            log_event(
                "semantic_search_skipped",
                {"reason": "no_index"},
                level=logging.DEBUG,
            )
            return []

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

            return results

        except Exception as e:
            log_event(
                "semantic_search_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return []

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
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword-based search.

        Note: This is a simplified implementation. For production use,
        consider integrating BM25 or other keyword search algorithms.
        Currently falls back to semantic search with a note.
        """
        log_event(
            "keyword_search_started",
            {
                "query": query[:50],
                "top_k": top_k,
                "has_filters": bool(filters),
            },
        )

        # TODO: Implement proper keyword search with BM25 or similar
        # For now, we'll use semantic search as a fallback
        # In a real implementation, you'd want to:
        # 1. Tokenize the query
        # 2. Use inverted index or BM25 scoring
        # 3. Return results based on term frequency

        log_event(
            "keyword_search_fallback",
            {
                "reason": "Not implemented, using semantic search",
            },
            level=logging.WARNING,
        )

        # Use semantic search as fallback
        results = await self.semantic_search(
            query=query,
            top_k=top_k,
            similarity_threshold=0.5,  # Lower threshold for keyword-like matching
            filters=filters,
        )

        # Mark results as keyword search
        for result in results:
            result["search_type"] = "keyword_fallback"

        return results

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
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword search.

        Combines results from both search methods using weighted scoring.
        """
        if not 0 <= semantic_weight <= 1:
            raise ValueError("semantic_weight must be between 0 and 1")

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
            # Get results from both search methods
            # Use 2x top_k to have enough results after merging
            semantic_results = await self.semantic_search(
                query=query,
                top_k=top_k * 2,
                similarity_threshold=0.3,  # Lower threshold to get more candidates
                filters=filters,
            )

            keyword_results = await self.keyword_search(
                query=query,
                top_k=top_k * 2,
                filters=filters,
            )

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

            return final_results

        except Exception as e:
            log_event(
                "hybrid_search_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return []

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
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar documents using vector search.

        This is essentially semantic search without additional filters.
        Maintained for backward compatibility.
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
    ) -> List[Dict[str, Any]]:
        """
        Get semantically similar documents for a given document.

        Args:
            document_text: Text content of the document
            document_id: ID of the document to exclude from results
            top_k: Number of similar documents to return

        Returns:
            List of similar documents with scores
        """
        try:
            # Use the document's text as query (truncated to avoid token limits)
            query_text = document_text[:2000]  # Use first 2000 chars as query

            # Retrieve similar documents with lower threshold
            similar_docs = await self.semantic_search(
                query=query_text,
                top_k=top_k + 10,  # Get extra to filter out self
                similarity_threshold=0.3,  # Lower threshold for neighbor search
            )

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

            return neighbors

        except Exception as e:
            log_event(
                "document_neighbors_error",
                {
                    "document_id": document_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return []
