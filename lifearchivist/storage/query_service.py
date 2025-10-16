"""
Query service for Q&A and RAG functionality.

This module provides a centralized interface for question-answering operations,
including context building, response generation, and source management.

All methods return Result types for explicit error handling.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from llama_index.core import QueryBundle
from llama_index.core.base.response.schema import Response
from llama_index.core.indices.base import BaseIndex
from llama_index.core.query_engine import BaseQueryEngine

from lifearchivist.storage.utils import (
    ChunkUtils,
    ConfidenceCalculator,
    MetadataFilterUtils,
)
from lifearchivist.utils.logging import log_event, track
from lifearchivist.utils.result import (
    Result,
    Success,
    internal_error,
    service_unavailable,
)


class QueryService(ABC):
    """Abstract base class for query services with Result types."""

    @abstractmethod
    async def query(
        self,
        question: str,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Execute a query and generate a response.

        Args:
            question: The user's question
            similarity_top_k: Number of similar chunks to retrieve
            response_mode: Response synthesis mode
            filters: Optional metadata filters for retrieval

        Returns:
            Success with response dict (answer, sources, metadata), or Failure with error
        """
        pass

    @abstractmethod
    async def build_context(
        self,
        question: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[Tuple[str, List[Dict[str, Any]]], str]:
        """
        Build context for a question by retrieving relevant documents.

        Args:
            question: The user's question
            top_k: Number of chunks to retrieve
            filters: Optional metadata filters

        Returns:
            Success with tuple of (combined_context, source_chunks), or Failure with error
        """
        pass

    @abstractmethod
    def format_response(
        self,
        answer: str,
        sources: List[Dict[str, Any]],
        context: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format the query response for API consumption.

        Args:
            answer: The generated answer
            sources: List of source documents
            context: The context used for generation
            metadata: Optional additional metadata

        Returns:
            Formatted response dictionary
        """
        pass


class LlamaIndexQueryService(QueryService):
    """
    Query service implementation using LlamaIndex.

    This service handles all Q&A and RAG operations including context building,
    response generation, and source management using the LlamaIndex framework.
    """

    def __init__(
        self,
        index: Optional[BaseIndex] = None,
        query_engine: Optional[BaseQueryEngine] = None,
        search_service=None,
        metadata_service=None,
    ):
        """
        Initialize the query service.

        Args:
            index: LlamaIndex index instance
            query_engine: Pre-configured query engine
            search_service: Search service for retrieval operations
            metadata_service: Metadata service for enrichment
        """
        self.index = index
        self.query_engine = query_engine
        self.search_service = search_service
        self.metadata_service = metadata_service

        # Setup or validate query engine
        self._setup_query_engine()

    def _setup_query_engine(self):
        """Setup or validate the query engine."""
        if not self.query_engine and self.index:
            # Create default query engine if not provided
            self.query_engine = self.index.as_query_engine(
                similarity_top_k=5,
                response_mode="tree_summarize",
            )
            log_event(
                "query_engine_created",
                {
                    "source": "query_service",
                    "similarity_top_k": 5,
                    "response_mode": "tree_summarize",
                },
            )
        elif self.query_engine:
            log_event(
                "query_engine_provided",
                {"source": "external"},
            )
        else:
            log_event(
                "query_engine_unavailable",
                {"reason": "no_index_or_engine"},
                level=logging.WARNING,
            )

    @track(
        operation="query_execution",
        include_args=["similarity_top_k", "response_mode"],
        include_result=True,
        track_performance=True,
        frequency="high_frequency",
    )
    async def query(
        self,
        question: str,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize",
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Execute a query and generate a response using RAG.

        This method orchestrates the entire Q&A pipeline:
        1. Builds context by retrieving relevant documents
        2. Generates an answer using the LLM
        3. Formats the response with sources and metadata

        Returns:
            Success with response dict (answer, sources, metadata), or Failure with error
        """
        if not self.query_engine:
            return service_unavailable(
                "Query engine not available", context={"service": "query"}
            )

        try:
            log_event(
                "query_started",
                {
                    "question_length": len(question),
                    "question_preview": question[:100],
                    "similarity_top_k": similarity_top_k,
                    "response_mode": response_mode,
                    "has_filters": bool(filters),
                },
            )

            # Update query engine parameters
            if hasattr(self.query_engine, "retriever"):
                self.query_engine.retriever.similarity_top_k = similarity_top_k

            # Build context (retrieve relevant chunks) - returns Result now
            context_result = await self.build_context(
                question=question,
                top_k=similarity_top_k,
                filters=filters,
            )

            # Handle Result type
            if context_result.is_failure():
                failure_result: Result[Dict[str, Any], str] = context_result
                return failure_result

            # Unwrap successful result
            context_tuple: Tuple[str, List[Dict[str, Any]]] = context_result.value
            context, source_chunks = context_tuple

            # Generate response using query engine
            response = await self._generate_response(
                question=question,
                context=context,
                response_mode=response_mode,
            )

            # Extract answer text
            answer = self._extract_answer(response)

            # Format sources for API response
            formatted_sources = self._format_sources(source_chunks)

            # Calculate confidence score using shared utility
            confidence_score = ConfidenceCalculator.calculate_confidence(
                answer=answer,
                sources=formatted_sources,
                context=context,
            )

            # Build final response
            result = self.format_response(
                answer=answer,
                sources=formatted_sources,
                context=context,
                metadata={
                    "confidence_score": confidence_score,
                    "response_mode": response_mode,
                    "num_sources": len(formatted_sources),
                    "context_length": len(context),
                },
            )

            log_event(
                "query_completed",
                {
                    "answer_length": len(answer),
                    "num_sources": len(formatted_sources),
                    "confidence_score": confidence_score,
                    "context_chars": len(context),
                },
            )

            return Success(result)

        except Exception as e:
            log_event(
                "query_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "question_preview": question[:100],
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Query failed: {str(e)}",
                context={
                    "question": question[:100],
                    "error_type": type(e).__name__,
                },
            )

    @track(
        operation="context_building",
        include_args=["top_k"],
        include_result=False,  # Don't log full context
        track_performance=True,
        frequency="high_frequency",
    )
    async def build_context(
        self,
        question: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Result[Tuple[str, List[Dict[str, Any]]], str]:
        """
        Build context for a question by retrieving relevant documents.

        Uses the search service for retrieval if available, otherwise
        falls back to the query engine's retriever.

        Returns:
            Success with tuple of (combined_context, source_chunks), or Failure with error
        """
        try:
            source_chunks = []

            # Use search service if available for more control
            if self.search_service:
                log_event(
                    "context_retrieval_method",
                    {"method": "search_service"},
                    level=logging.DEBUG,
                )

                # Perform semantic search with filters (returns Result now)
                search_result = await self.search_service.semantic_search(
                    query=question,
                    top_k=top_k,
                    similarity_threshold=0.3,  # Lower threshold for context building
                    filters=filters,
                )

                # Handle Result type
                if search_result.is_failure():
                    log_event(
                        "context_search_failed",
                        {"error": str(search_result.error)},
                        level=logging.WARNING,
                    )
                    failure_result: Result[Tuple[str, List[Dict[str, Any]]], str] = (
                        search_result
                    )
                    return failure_result

                # Unwrap successful result
                search_results: List[Dict[str, Any]] = search_result.value

                # Convert search results to source chunks format
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

            elif self.query_engine and hasattr(self.query_engine, "retriever"):
                log_event(
                    "context_retrieval_method",
                    {"method": "query_engine_retriever"},
                    level=logging.DEBUG,
                )

                # Use query engine's retriever
                retriever = self.query_engine.retriever
                nodes = retriever.retrieve(QueryBundle(query_str=question))

                # Convert nodes to source chunks format
                for node in nodes:
                    if hasattr(node, "node"):
                        text = node.node.text if hasattr(node.node, "text") else ""
                        metadata = (
                            node.node.metadata if hasattr(node.node, "metadata") else {}
                        )

                        # Apply filters if provided
                        if filters and not MetadataFilterUtils.matches_filters(
                            metadata, filters
                        ):
                            continue

                        source_chunks.append(
                            {
                                "text": text,
                                "score": float(node.score) if node.score else 0.0,
                                "metadata": metadata,
                                "node_id": (
                                    node.node.id_ if hasattr(node.node, "id_") else None
                                ),
                                "document_id": metadata.get("document_id", "unknown"),
                            }
                        )
            else:
                log_event(
                    "context_retrieval_failed",
                    {"reason": "no_retrieval_method"},
                    level=logging.WARNING,
                )
                return service_unavailable(
                    "No retrieval method available",
                    context={"service": "context_building"},
                )

            # Enrich metadata if metadata service available
            if self.metadata_service:
                source_chunks = await self._enrich_source_metadata(source_chunks)

            # Combine chunks into context using shared utility
            context = ChunkUtils.combine_chunks_to_context(source_chunks)

            log_event(
                "context_built",
                {
                    "num_chunks": len(source_chunks),
                    "context_length": len(context),
                    "avg_score": (
                        sum(c["score"] for c in source_chunks) / len(source_chunks)
                        if source_chunks
                        else 0
                    ),
                },
            )

            return Success((context, source_chunks))

        except Exception as e:
            log_event(
                "context_building_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Context building failed: {str(e)}",
                context={
                    "question": question[:100],
                    "error_type": type(e).__name__,
                },
            )

    def format_response(
        self,
        answer: str,
        sources: List[Dict[str, Any]],
        context: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Format the query response for API consumption.

        Creates a standardized response format with all necessary information
        for the frontend to display results effectively.
        """
        response = {
            "answer": answer,
            "sources": sources,
            "method": "llamaindex_rag",
            "context_used": context,
            "num_chunks_used": len(sources),
        }

        # Add metadata if provided
        if metadata:
            response.update(metadata)

        # Add summary statistics
        response["statistics"] = {
            "answer_length": len(answer),
            "context_length": len(context),
            "num_sources": len(sources),
            "unique_documents": len(set(s.get("document_id", "") for s in sources)),
            "avg_relevance_score": (
                sum(s.get("score", 0) for s in sources) / len(sources) if sources else 0
            ),
        }

        return response

    async def _generate_response(
        self,
        question: str,
        context: str,
        response_mode: str,
    ) -> Any:
        """
        Generate a response using the query engine.

        This method handles the actual LLM call through LlamaIndex.
        """
        try:
            # If we have context, we could potentially inject it
            # For now, let the query engine handle its own retrieval
            engine = self.query_engine
            if engine is None:
                raise RuntimeError("Query engine not available")
            response = engine.query(question)

            # Log the generation details
            log_event(
                "response_generated",
                {
                    "response_mode": response_mode,
                    "has_response": bool(response),
                    "response_length": len(str(getattr(response, "response", ""))),
                },
                level=logging.DEBUG,
            )

            return response

        except Exception as e:
            log_event(
                "response_generation_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            raise

    def _extract_answer(self, response: Response) -> str:
        """Extract the answer text from a LlamaIndex response."""
        content = getattr(response, "response", "")
        return str(content) if content is not None else ""

    def _format_sources(
        self, source_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Format source chunks for API response.

        Ensures consistent source format with previews and full text.
        """
        formatted_sources = []

        for chunk in source_chunks:
            text = chunk.get("text", "")
            formatted_source = {
                "text": text[:200] + "..." if len(text) > 200 else text,  # Preview
                "full_text": text,  # Complete text
                "score": chunk.get("score", 0.0),
                "node_id": chunk.get("node_id"),
                "document_id": chunk.get("document_id", "unknown"),
                "metadata": chunk.get("metadata", {}),
            }
            formatted_sources.append(formatted_source)

        return formatted_sources

    # Confidence calculation and context building now use shared utilities
    # Removed _combine_chunks_to_context and _calculate_confidence methods

    async def _enrich_source_metadata(
        self, source_chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Enrich source chunks with full metadata from metadata service.

        Adds additional metadata like themes, dates, etc.
        """
        if not self.metadata_service:
            return source_chunks

        enriched_chunks = []
        for chunk in source_chunks:
            enriched_chunk = chunk.copy()
            document_id = chunk.get("document_id")

            if document_id and document_id != "unknown":
                try:
                    # Get full metadata for the document
                    meta_result = (
                        await self.metadata_service.get_full_document_metadata(
                            document_id
                        )
                    )

                    if not meta_result.is_failure():
                        full_metadata = meta_result.unwrap()
                        # Merge with existing metadata (chunk metadata takes precedence)
                        enriched_metadata = {
                            **full_metadata,
                            **chunk.get("metadata", {}),
                        }
                        enriched_chunk["metadata"] = enriched_metadata

                        # Add theme info to top level for easier access
                        if "theme" in enriched_metadata:
                            enriched_chunk["theme"] = enriched_metadata["theme"]

                except Exception as e:
                    log_event(
                        "metadata_enrichment_failed",
                        {
                            "document_id": document_id,
                            "error": str(e),
                        },
                        level=logging.DEBUG,
                    )

            enriched_chunks.append(enriched_chunk)

        return enriched_chunks

    # Filter matching now uses shared utility
    # Removed _matches_filters method - using MetadataFilterUtils.matches_filters instead

    async def query_with_streaming(
        self,
        question: str,
        similarity_top_k: int = 5,
        response_mode: str = "tree_summarize",
        filters: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[Result[Dict[str, Any], str], None]:
        """
        Execute a query with streaming response.

        This is a placeholder for future streaming implementation.
        Yields Result objects containing response chunks as they're generated.

        Yields:
            Result objects with response data or errors
        """
        # TODO: Implement streaming response
        # This would require using streaming_query instead of query
        # and yielding response chunks as they come in

        log_event(
            "streaming_query_requested",
            {"status": "not_implemented"},
            level=logging.INFO,
        )

        # For now, just return the regular response
        result = await self.query(
            question=question,
            similarity_top_k=similarity_top_k,
            response_mode=response_mode,
            filters=filters,
        )

        yield result
