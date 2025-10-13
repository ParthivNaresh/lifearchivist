"""
Document service for core document CRUD operations.

This module provides a centralized interface for document management,
coordinating with metadata and search services for comprehensive
document lifecycle management.

All methods return Result types for explicit error handling and consistent
response formats across the API and UI layers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from llama_index.core import Document
from qdrant_client.models import Distance, VectorParams

from lifearchivist.utils.logging import log_event, track
from lifearchivist.utils.result import (
    Result,
    Success,
    internal_error,
    not_found_error,
    storage_error,
    validation_error,
)


class DocumentService(ABC):
    """
    Abstract base class for document services.

    All methods return Result types for explicit error handling and
    consistent response formats.
    """

    @abstractmethod
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Add a document to the index.

        Args:
            document_id: Unique identifier for the document
            content: Text content of the document
            metadata: Optional metadata dictionary

        Returns:
            Success with document info, or Failure with error details
        """
        pass

    @abstractmethod
    async def delete_document(
        self,
        document_id: str,
    ) -> Result[Dict[str, Any], str]:
        """
        Delete a document from the index.

        Args:
            document_id: The document to delete

        Returns:
            Success with deletion info, or Failure with error details
        """
        pass

    @abstractmethod
    async def get_document_count(self) -> Result[int, str]:
        """
        Get the total count of indexed documents.

        Returns:
            Success with document count, or Failure with error details
        """
        pass

    @abstractmethod
    async def clear_all_data(self) -> Result[Dict[str, Any], str]:
        """
        Clear all documents and reset the index.

        Returns:
            Success with clearing statistics, or Failure with error details
        """
        pass

    @abstractmethod
    async def get_document_chunks(
        self,
        document_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Result[Dict[str, Any], str]:
        """
        Get chunks for a specific document.

        Args:
            document_id: The document to get chunks for
            limit: Maximum number of chunks to return
            offset: Pagination offset

        Returns:
            Success with chunks data, or Failure with error details
        """
        pass


class LlamaIndexDocumentService(DocumentService):
    """
    Document service implementation for LlamaIndex.

    This service handles all document CRUD operations and coordinates
    with metadata and search services for comprehensive document management.
    """

    def __init__(
        self,
        index=None,
        doc_tracker=None,
        metadata_service=None,
        qdrant_client=None,
        settings=None,
        bm25_service=None,
    ):
        """
        Initialize the document service.

        Args:
            index: LlamaIndex VectorStoreIndex instance
            doc_tracker: Document tracker for node management
            metadata_service: Metadata service for metadata operations
            qdrant_client: Qdrant client for vector operations
            settings: Application settings
            bm25_service: BM25 index service for keyword search
        """
        self.index = index
        self.doc_tracker = doc_tracker
        self.metadata_service = metadata_service
        self.qdrant_client = qdrant_client
        self.settings = settings
        self.bm25_service = bm25_service

    @track(
        operation="document_addition",
        include_args=["document_id"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def add_document(
        self,
        document_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Result[Dict[str, Any], str]:
        """
        Add a document to the index.

        This method handles the complete document ingestion process:
        1. Validates input
        2. Stores full metadata separately
        3. Creates minimal chunk metadata
        4. Inserts document into index
        5. Tracks node associations
        6. Persists storage

        Args:
            document_id: Unique identifier for the document
            content: Text content of the document
            metadata: Optional metadata dictionary

        Returns:
            Success with document info including:
                - document_id: The document identifier
                - nodes_created: Number of chunks created
                - content_length: Length of content in characters
                - word_count: Number of words in content
                - status: Document status ("indexed")
            Or Failure with error details
        """
        # Validate index availability
        if not self.index:
            log_event(
                "document_add_failed",
                {"document_id": document_id, "reason": "no_index"},
                level=logging.ERROR,
            )
            return internal_error(
                "Index not initialized - cannot add documents",
                context={"document_id": document_id, "service": "document_service"},
            )

        # Validate content
        if not content or not content.strip():
            log_event(
                "document_add_failed",
                {"document_id": document_id, "reason": "empty_content"},
                level=logging.WARNING,
            )
            return validation_error(
                "Document content cannot be empty",
                context={"document_id": document_id},
            )

        try:
            # Store full metadata separately (for retrieval by API endpoints)
            full_metadata = metadata or {}
            full_metadata["document_id"] = document_id

            # Create minimal metadata for chunks using metadata service
            if self.metadata_service:
                chunk_metadata = self.metadata_service.create_minimal_chunk_metadata(
                    full_metadata
                )
            else:
                # Fallback if metadata service not available
                chunk_metadata = self._create_minimal_chunk_metadata_fallback(
                    full_metadata
                )

            # Store full metadata using the tracker
            if self.doc_tracker is not None:
                try:
                    await self.doc_tracker.store_full_metadata(
                        document_id, full_metadata
                    )
                except Exception as e:
                    log_event(
                        "metadata_storage_failed",
                        {"document_id": document_id, "error": str(e)},
                        level=logging.WARNING,
                    )
                    # Continue - this is not fatal

            # Create LlamaIndex document
            document = Document(
                text=content,
                metadata=chunk_metadata,  # Use minimal metadata for chunks
                id_=document_id,
            )

            # Insert into index - this creates nodes
            insert_result = await self._insert_document_into_index(
                document, document_id, content
            )

            # Check if insertion failed
            if insert_result.is_failure():
                return insert_result  # Propagate the failure

            nodes_created = insert_result.unwrap()

            # Calculate statistics
            word_count = len(content.split())

            # Add to BM25 index for keyword search
            if self.bm25_service:
                try:
                    await self.bm25_service.add_document(document_id, content)
                    log_event(
                        "bm25_document_indexed",
                        {"document_id": document_id},
                        level=logging.DEBUG,
                    )
                except Exception as e:
                    log_event(
                        "bm25_indexing_failed",
                        {
                            "document_id": document_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                        level=logging.WARNING,
                    )
                    # Don't fail the whole operation if BM25 indexing fails

            log_event(
                "document_added",
                {
                    "document_id": document_id,
                    "content_length": len(content),
                    "word_count": word_count,
                    "nodes_created": len(nodes_created),
                    "bm25_indexed": self.bm25_service is not None,
                },
            )

            return Success(
                {
                    "document_id": document_id,
                    "nodes_created": len(nodes_created),
                    "content_length": len(content),
                    "word_count": word_count,
                    "status": "indexed",
                },
                metadata={
                    "operation": "add_document",
                    "timestamp": full_metadata.get("uploaded_at"),
                },
            )

        except Exception as e:
            log_event(
                "document_add_error",
                {
                    "document_id": document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to add document: {str(e)}",
                context={
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "content_length": len(content) if content else 0,
                },
            )

    async def _insert_document_into_index(
        self,
        document: Document,
        document_id: str,
        content: str,
    ) -> Result[List[str], str]:
        """
        Insert document into index and track created nodes.

        Returns:
            Success with list of created node IDs, or Failure with error details
        """
        try:
            # Log before insert for debugging
            log_event(
                "document_insert_attempt",
                {
                    "document_id": document_id,
                    "content_length": len(content),
                    "content_preview": content[:100] if content else "empty",
                    "metadata_keys": list(document.metadata.keys()),
                },
                level=logging.DEBUG,
            )

            # Check if content is empty
            if not content or not content.strip():
                return validation_error(
                    "Document content is empty or whitespace only",
                    context={"document_id": document_id},
                )

            # Insert document into index
            self.index.insert(document)

            # Log successful insert
            log_event(
                "document_insert_success",
                {
                    "document_id": document_id,
                    "content_length": len(content),
                },
                level=logging.DEBUG,
            )

            # Track which nodes belong to this document
            doc_nodes = await self._find_document_nodes(document_id)

            if not doc_nodes:
                log_event(
                    "node_tracking_warning",
                    {
                        "document_id": document_id,
                        "reason": "no_nodes_found_after_insert",
                    },
                    level=logging.WARNING,
                )
                return internal_error(
                    "Document insert succeeded but no nodes were created",
                    context={
                        "document_id": document_id,
                        "reason": "no_nodes_found_after_insert",
                    },
                )

            # Update tracker with the node IDs
            log_event(
                "tracker_update_attempt",
                {
                    "document_id": document_id,
                    "node_count": len(doc_nodes),
                    "has_tracker": self.doc_tracker is not None,
                },
                level=logging.DEBUG,
            )

            if self.doc_tracker is not None:
                await self.doc_tracker.add_document(document_id, doc_nodes)
                log_event(
                    "tracker_updated",
                    {
                        "document_id": document_id,
                        "node_count": len(doc_nodes),
                    },
                    level=logging.DEBUG,
                )
            else:
                log_event(
                    "tracker_update_skipped",
                    {"document_id": document_id, "reason": "no_tracker"},
                    level=logging.WARNING,
                )

            return Success(doc_nodes)

        except Exception as e:
            log_event(
                "document_insert_failed",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to insert document into index: {str(e)}",
                context={
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                },
            )

    async def _find_document_nodes(self, document_id: str) -> List[str]:
        """
        Find all nodes belonging to a document after insertion using Qdrant.

        This replaces the old O(N) docstore iteration with an O(k) Qdrant query,
        where k = number of nodes for this document (typically 1-10).

        Returns list of node IDs.
        """
        doc_nodes = []

        if not self.qdrant_client:
            log_event(
                "find_nodes_no_qdrant",
                {"document_id": document_id},
                level=logging.WARNING,
            )
            return doc_nodes

        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            # Query Qdrant for all points with this document_id
            # This is O(k) where k = nodes for this document, not O(N) like docstore!
            scroll_result = self.qdrant_client.scroll(
                collection_name="lifearchivist",
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
                limit=1000,  # Max nodes per document (should be plenty)
                with_payload=False,  # We only need IDs, not payload
                with_vectors=False,  # We don't need vectors
            )

            # Extract node IDs from scroll result
            points, _ = scroll_result  # scroll returns (points, next_page_offset)
            doc_nodes = [str(point.id) for point in points]

            log_event(
                "find_nodes_result",
                {
                    "document_id": document_id,
                    "method": "qdrant_scroll",
                    "nodes_found": len(doc_nodes),
                },
                level=logging.DEBUG,
            )

        except Exception as e:
            log_event(
                "find_nodes_error",
                {
                    "document_id": document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            # Return empty list on error
            return []

        # Log if no nodes found
        if not doc_nodes:
            log_event(
                "find_document_nodes_empty",
                {
                    "document_id": document_id,
                    "warning": "No nodes found in Qdrant after insertion",
                },
                level=logging.WARNING,
            )

        return doc_nodes

    def _create_minimal_chunk_metadata_fallback(
        self,
        full_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Fallback method to create minimal chunk metadata.

        Used when metadata service is not available.
        """
        return {
            "document_id": full_metadata.get("document_id"),
            "title": full_metadata.get("title", ""),
            "mime_type": full_metadata.get("mime_type", ""),
            "status": full_metadata.get("status", "ready"),
        }

    @track(
        operation="document_deletion",
        include_args=["document_id"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def delete_document(self, document_id: str) -> Result[Dict[str, Any], str]:
        """
        Delete a document from the index.

        This method:
        1. Checks document existence
        2. Removes from vector store (Qdrant)
        3. Removes from document tracker
        4. Cleans up metadata

        Args:
            document_id: The document to delete

        Returns:
            Success with deletion info including:
                - document_id: The deleted document identifier
                - nodes_deleted: Number of chunks deleted
                - status: Deletion status ("deleted")
            Or Failure with error details
        """
        # Validate tracker availability
        if not self.doc_tracker:
            log_event(
                "document_delete_failed",
                {"document_id": document_id, "reason": "no_tracker"},
                level=logging.ERROR,
            )
            return internal_error(
                "Document tracker not initialized",
                context={"document_id": document_id, "service": "document_service"},
            )

        try:
            # Check if document exists
            if not await self.doc_tracker.document_exists(document_id):
                log_event(
                    "document_delete_skipped",
                    {"document_id": document_id, "reason": "not_found"},
                    level=logging.WARNING,
                )
                return not_found_error(
                    f"Document '{document_id}' not found",
                    context={"document_id": document_id},
                )

            # Get nodes for this document
            node_ids = await self.doc_tracker.get_node_ids(document_id)
            if not node_ids:
                log_event(
                    "document_delete_skipped",
                    {"document_id": document_id, "reason": "no_nodes"},
                    level=logging.WARNING,
                )
                return not_found_error(
                    f"No chunks found for document '{document_id}'",
                    context={"document_id": document_id},
                )

            nodes_count = len(node_ids)

            # Delete from Qdrant if client available
            if self.qdrant_client:
                try:
                    await self._delete_from_vector_store(document_id)
                except Exception as e:
                    log_event(
                        "vector_deletion_warning",
                        {"document_id": document_id, "error": str(e)},
                        level=logging.WARNING,
                    )
                    # Continue with deletion even if vector store fails

            # Remove from tracker
            try:
                await self.doc_tracker.remove_document(document_id)
            except Exception as e:
                return storage_error(
                    f"Failed to remove document from tracker: {str(e)}",
                    context={
                        "document_id": document_id,
                        "error_type": type(e).__name__,
                    },
                )

            # Remove from BM25 index
            if self.bm25_service:
                try:
                    await self.bm25_service.remove_document(document_id)
                    log_event(
                        "bm25_document_removed",
                        {"document_id": document_id},
                        level=logging.DEBUG,
                    )
                except Exception as e:
                    log_event(
                        "bm25_removal_failed",
                        {
                            "document_id": document_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                        level=logging.WARNING,
                    )
                    # Don't fail the whole operation if BM25 removal fails

            log_event(
                "document_deleted",
                {
                    "document_id": document_id,
                    "nodes_deleted": nodes_count,
                    "bm25_removed": self.bm25_service is not None,
                },
            )

            return Success(
                {
                    "document_id": document_id,
                    "nodes_deleted": nodes_count,
                    "status": "deleted",
                }
            )

        except Exception as e:
            log_event(
                "document_deletion_error",
                {
                    "document_id": document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to delete document: {str(e)}",
                context={
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                },
            )

    async def _delete_from_vector_store(self, document_id: str) -> None:
        """Delete document vectors from Qdrant."""
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            self.qdrant_client.delete(
                collection_name="lifearchivist",
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
            )
        except Exception as e:
            log_event(
                "vector_deletion_error",
                {"document_id": document_id, "error": str(e)},
                level=logging.WARNING,
            )
            # Continue with deletion even if vector store fails

    @track(
        operation="document_count",
        include_result=True,
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_document_count(self) -> Result[int, str]:
        """
        Get count of indexed documents.

        Returns:
            Success with document count, or Failure with error details
        """
        if not self.doc_tracker:
            return internal_error(
                "Document tracker not initialized",
                context={"service": "document_service"},
            )

        try:
            count = await self.doc_tracker.get_document_count()
            return Success(count)
        except Exception as e:
            log_event(
                "document_count_error",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to get document count: {str(e)}",
                context={"error_type": type(e).__name__},
            )

    @track(
        operation="clear_all_data",
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def clear_all_data(self) -> Result[Dict[str, Any], str]:
        """
        Clear all data and reset the system.

        This method:
        1. Gets current statistics
        2. Recreates vector store collection
        3. Clears document tracker
        4. Returns clearing statistics

        Returns:
            Success with clearing statistics including:
                - documents_cleared: Number of documents removed
                - storage_cleared: Whether storage was cleared
                - total_entries_cleared: Total entries removed from tracker
            Or Failure with error details
        """
        try:
            # Get counts before clearing
            doc_count = 0
            if self.doc_tracker is not None:
                doc_count = await self.doc_tracker.get_document_count()

            # Recreate Qdrant collection if client available
            if self.qdrant_client:
                try:
                    await self._recreate_vector_collection()
                except Exception as e:
                    return storage_error(
                        f"Failed to recreate vector collection: {str(e)}",
                        context={"error_type": type(e).__name__},
                    )

            # Clear tracker
            clear_stats = {}
            if self.doc_tracker is not None:
                try:
                    clear_stats = await self.doc_tracker.clear_all()
                except Exception as e:
                    return storage_error(
                        f"Failed to clear document tracker: {str(e)}",
                        context={"error_type": type(e).__name__},
                    )

            # Clear BM25 index
            if self.bm25_service:
                try:
                    await self.bm25_service.clear_index()
                    log_event(
                        "bm25_index_cleared",
                        level=logging.DEBUG,
                    )
                except Exception as e:
                    log_event(
                        "bm25_clear_failed",
                        {
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                        level=logging.WARNING,
                    )
                    # Don't fail the whole operation if BM25 clear fails

            log_event(
                "data_cleared",
                {
                    "documents_cleared": doc_count,
                    "bm25_cleared": self.bm25_service is not None,
                    **clear_stats,
                },
            )

            return Success(
                {
                    "documents_cleared": doc_count,
                    "storage_cleared": True,
                    **clear_stats,
                }
            )

        except Exception as e:
            log_event(
                "data_cleanup_error",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to clear all data: {str(e)}",
                context={"error_type": type(e).__name__},
            )

    async def _recreate_vector_collection(self) -> None:
        """Recreate the Qdrant collection."""
        try:
            # Delete existing collection
            self.qdrant_client.delete_collection("lifearchivist")

            # Create new collection
            self.qdrant_client.create_collection(
                collection_name="lifearchivist",
                vectors_config=VectorParams(
                    size=384,  # all-MiniLM-L6-v2 dimension
                    distance=Distance.COSINE,
                ),
            )

            log_event(
                "vector_collection_recreated",
                {"collection": "lifearchivist"},
            )
        except Exception as e:
            log_event(
                "vector_collection_recreation_error",
                {"error": str(e)},
                level=logging.ERROR,
            )
            raise

    @track(
        operation="document_chunks_retrieval",
        include_args=["document_id", "limit", "offset"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def get_document_chunks(
        self,
        document_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Result[Dict[str, Any], str]:
        """
        Get all chunks for a specific document with pagination.

        This method retrieves and enriches chunk information including:
        - Text content
        - Metadata
        - Relationships
        - Statistics

        Args:
            document_id: The document to get chunks for
            limit: Maximum number of chunks to return
            offset: Pagination offset

        Returns:
            Success with chunks data including:
                - document_id: The document identifier
                - chunks: List of enriched chunk dictionaries
                - total: Total number of chunks
                - limit: Requested limit
                - offset: Requested offset
                - has_more: Whether more chunks are available
            Or Failure with error details
        """
        # Validate index availability
        if not self.index:
            log_event(
                "chunks_retrieval_skipped",
                {"document_id": document_id, "reason": "no_index"},
                level=logging.DEBUG,
            )
            return internal_error(
                "Index not initialized",
                context={"document_id": document_id, "service": "document_service"},
            )

        # Validate tracker availability
        if not self.doc_tracker:
            return internal_error(
                "Document tracker not initialized",
                context={"document_id": document_id, "service": "document_service"},
            )

        try:
            # Check if document exists
            if not await self.doc_tracker.document_exists(document_id):
                log_event(
                    "chunks_not_found",
                    {"document_id": document_id},
                    level=logging.WARNING,
                )
                return not_found_error(
                    f"Document '{document_id}' not found",
                    context={"document_id": document_id},
                )

            # Get node IDs for document
            node_ids = await self.doc_tracker.get_node_ids(document_id)
            if not node_ids:
                return not_found_error(
                    f"No chunks found for document '{document_id}'",
                    context={"document_id": document_id},
                )

            total = len(node_ids)

            # Apply pagination to node IDs
            paginated_node_ids = node_ids[offset : offset + limit]

            # Retrieve and enrich chunks
            enriched_chunks = await self._retrieve_and_enrich_chunks(
                paginated_node_ids, offset
            )

            # Calculate statistics
            stats = self._calculate_chunk_statistics(enriched_chunks)

            log_event(
                "chunks_retrieved",
                {
                    "document_id": document_id,
                    "total_chunks": total,
                    "chunks_returned": len(enriched_chunks),
                    **stats,
                },
            )

            return Success(
                {
                    "document_id": document_id,
                    "chunks": enriched_chunks,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total,
                }
            )

        except Exception as e:
            log_event(
                "chunks_retrieval_failed",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to retrieve chunks: {str(e)}",
                context={
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                },
            )

    async def _retrieve_and_enrich_chunks(
        self,
        node_ids: List[str],
        offset: int,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve and enrich chunk information using Qdrant batch retrieval.

        This replaces N docstore queries with 1 Qdrant batch query.

        Returns list of enriched chunk dictionaries.
        """
        if not self.qdrant_client:
            log_event(
                "chunks_retrieval_no_qdrant",
                {"node_count": len(node_ids)},
                level=logging.WARNING,
            )
            return []

        enriched_chunks = []

        try:
            from lifearchivist.storage.utils import QdrantNodeUtils

            # Batch retrieve all nodes from Qdrant in one call
            # This is much faster than N individual docstore queries
            points = self.qdrant_client.retrieve(
                collection_name="lifearchivist",
                ids=node_ids,
                with_payload=True,
                with_vectors=False,
            )

            # Process each point
            for i, point in enumerate(points):
                try:
                    # Extract text from Qdrant payload
                    text = QdrantNodeUtils.extract_text_from_node(point.payload)
                    if not text:
                        log_event(
                            "chunk_text_missing",
                            {"node_id": str(point.id)},
                            level=logging.DEBUG,
                        )
                        continue

                    # Create enriched chunk info
                    chunk_info = self._create_chunk_info_from_qdrant(
                        point, text, offset + i
                    )
                    enriched_chunks.append(chunk_info)

                except Exception as e:
                    log_event(
                        "chunk_enrichment_error",
                        {"node_id": str(point.id), "error": str(e)},
                        level=logging.DEBUG,
                    )
                    continue

        except Exception as e:
            log_event(
                "chunks_batch_retrieval_error",
                {
                    "node_count": len(node_ids),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            return []

        return enriched_chunks

    def _create_chunk_info_from_qdrant(
        self,
        point,
        text: str,
        chunk_index: int,
    ) -> Dict[str, Any]:
        """
        Create enriched chunk information dictionary from Qdrant point.

        This replaces the old docstore-based method.
        """
        text_length = len(text)
        word_count = len(text.split())

        # Get metadata from Qdrant payload (minimal metadata)
        metadata = {}
        for key in [
            "document_id",
            "title",
            "mime_type",
            "status",
            "theme",
            "uploaded_date",
            "file_hash_short",
        ]:
            if key in point.payload:
                metadata[key] = point.payload[key]

        # Parse _node_content for additional info if available
        try:
            import json

            if "_node_content" in point.payload:
                node_data = json.loads(point.payload["_node_content"])

                # Extract start/end char indices if available
                start_char = node_data.get("start_char_idx")
                end_char = node_data.get("end_char_idx")

                # Extract relationships if available
                relationships = {}
                if "relationships" in node_data:
                    for rel_type, rel_info in node_data["relationships"].items():
                        if isinstance(rel_info, dict):
                            relationships[rel_type] = {
                                "node_id": rel_info.get("node_id"),
                            }
        except Exception as e:
            log_event(
                "node_content_parse_error",
                {"node_id": str(point.id), "error": str(e)},
                level=logging.DEBUG,
            )
            start_char = None
            end_char = None
            relationships = {}

        chunk_info = {
            "chunk_index": chunk_index,
            "node_id": str(point.id),
            "text": text,
            "text_length": text_length,
            "word_count": word_count,
            "metadata": metadata,
            "relationships": relationships if relationships else {},
        }

        # Add start/end char if available
        if start_char is not None:
            chunk_info["start_char"] = start_char
        if end_char is not None:
            chunk_info["end_char"] = end_char

        return chunk_info

    def _calculate_chunk_statistics(
        self,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate statistics for retrieved chunks."""
        if not chunks:
            return {
                "avg_chunk_length": 0,
                "avg_word_count": 0,
                "has_more": False,
            }

        total_text_length = sum(chunk["text_length"] for chunk in chunks)
        total_word_count = sum(chunk["word_count"] for chunk in chunks)

        return {
            "avg_chunk_length": total_text_length / len(chunks),
            "avg_word_count": total_word_count / len(chunks),
        }

    async def document_exists(self, document_id: str) -> bool:
        """
        Check if a document exists in the index.

        Args:
            document_id: The document to check

        Returns:
            True if document exists
        """
        if not self.doc_tracker:
            return False

        return await self.doc_tracker.document_exists(document_id)

    async def get_node_ids(self, document_id: str) -> List[str]:
        """
        Get all node IDs for a document.

        Args:
            document_id: The document to get nodes for

        Returns:
            List of node IDs
        """
        if not self.doc_tracker:
            return []

        return await self.doc_tracker.get_node_ids(document_id)
