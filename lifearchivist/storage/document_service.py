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

from lifearchivist.utils.result import (
    Result,
    Success,
    internal_error,
    not_found_error,
    storage_error,
    validation_error,
)

from ..utils.logx import log_event, track
from .constants import NOT_INITIALIZED_TRACKER


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
        doc_tracker=None,
        metadata_service=None,
        qdrant_client=None,
        settings=None,
        bm25_service=None,
    ):
        """
        Initialize the document service.

        Args:
            doc_tracker: Document tracker for node management
            metadata_service: Metadata service for metadata operations
            qdrant_client: Qdrant client for vector operations
            settings: Application settings
            bm25_service: BM25 index service for keyword search
        """
        self.doc_tracker = doc_tracker
        self.metadata_service = metadata_service
        self.qdrant_client = qdrant_client
        self.settings = settings
        self.bm25_service = bm25_service

    def _validate_document_prerequisites(
        self, document_id: str, content: str
    ) -> Optional[Result[Dict[str, Any], str]]:
        """
        Validate document prerequisites before adding.

        Args:
            document_id: Document identifier
            content: Document content

        Returns:
            Error Result if validation fails, None if valid
        """
        if not self.qdrant_client:
            log_event(
                "document_add_failed",
                {"document_id": document_id, "reason": "no_qdrant_client"},
                level=logging.ERROR,
            )
            return internal_error(
                "Qdrant client not initialized",
                context={"document_id": document_id, "service": "document_service"},
            )

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

        return None

    async def _prepare_document_metadata(
        self, document_id: str, metadata: Optional[Dict[str, Any]]
    ) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Prepare full and chunk metadata for document.

        Args:
            document_id: Document identifier
            metadata: Optional metadata dictionary

        Returns:
            Tuple of (full_metadata, chunk_metadata)
        """
        full_metadata = metadata or {}
        full_metadata["document_id"] = document_id

        chunk_metadata = (
            self.metadata_service.create_minimal_chunk_metadata(full_metadata)
            if self.metadata_service
            else self._create_minimal_chunk_metadata_fallback(full_metadata)
        )

        if self.doc_tracker is not None:
            try:
                await self.doc_tracker.store_full_metadata(document_id, full_metadata)
            except Exception as e:
                log_event(
                    "metadata_storage_failed",
                    {"document_id": document_id, "error": str(e)},
                    level=logging.WARNING,
                )

        return full_metadata, chunk_metadata

    async def _index_document_to_bm25(self, document_id: str, content: str) -> None:
        """
        Add document to BM25 index for keyword search.

        Args:
            document_id: Document identifier
            content: Document content
        """
        if not self.bm25_service:
            return

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
        validation_error_result = self._validate_document_prerequisites(
            document_id, content
        )
        if validation_error_result:
            return validation_error_result

        try:
            full_metadata, chunk_metadata = await self._prepare_document_metadata(
                document_id, metadata
            )

            document = Document(
                text=content,
                metadata=chunk_metadata,
                id_=document_id,
            )

            insert_result = await self._insert_document_into_index(
                document, document_id, content
            )

            if insert_result.is_failure():
                error_msg = (
                    str(insert_result.error)
                    if hasattr(insert_result, "error")
                    else "Document insertion failed"
                )
                return internal_error(
                    error_msg,
                    context={
                        "document_id": document_id,
                        "operation": "insert_document",
                    },
                )

            nodes_created: List[str] = insert_result.unwrap()
            word_count = len(content.split())

            await self._index_document_to_bm25(document_id, content)

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

        This method bypasses LlamaIndex's VectorStoreIndex to avoid creating
        in-memory SimpleDocumentStore and SimpleIndexStore. Instead, it:
        1. Chunks text using LlamaIndex's SentenceSplitter
        2. Generates embeddings using LlamaIndex's HuggingFaceEmbedding
        3. Stores directly in Qdrant with proper payload structure
        4. Tracks node IDs in Redis

        Returns:
            Success with list of created node IDs, or Failure with error details
        """
        try:
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

            if not content or not content.strip():
                return validation_error(
                    "Document content is empty or whitespace only",
                    context={"document_id": document_id},
                )

            from llama_index.core import Settings
            from qdrant_client.models import PointStruct

            chunks = Settings.node_parser.get_nodes_from_documents([document])

            if not chunks:
                return internal_error(
                    "No chunks created from document",
                    context={"document_id": document_id},
                )

            texts_to_embed = [chunk.get_content() for chunk in chunks]
            embeddings = Settings.embed_model.get_text_embedding_batch(texts_to_embed)

            for chunk, embedding in zip(chunks, embeddings, strict=False):
                chunk.embedding = embedding

            points = []
            for chunk in chunks:
                payload = {
                    "document_id": document_id,
                    **document.metadata,
                    "_node_content": chunk.json(),
                    "_node_type": chunk.class_name(),
                    "doc_id": document_id,
                    "ref_doc_id": document_id,
                }

                embedding = chunk.embedding if chunk.embedding is not None else []

                point = PointStruct(
                    id=chunk.node_id,
                    vector=embedding,
                    payload=payload,
                )
                points.append(point)

            BATCH_SIZE = 100
            for i in range(0, len(points), BATCH_SIZE):
                batch = points[i : i + BATCH_SIZE]
                self.qdrant_client.upsert(
                    collection_name="lifearchivist",
                    points=batch,
                    wait=True,
                )

            node_ids = [chunk.node_id for chunk in chunks]

            log_event(
                "document_insert_success",
                {
                    "document_id": document_id,
                    "content_length": len(content),
                    "chunks_created": len(node_ids),
                    "method": "direct_qdrant",
                },
                level=logging.DEBUG,
            )

            if self.doc_tracker is not None:
                await self.doc_tracker.add_document(document_id, node_ids)
                log_event(
                    "tracker_updated",
                    {
                        "document_id": document_id,
                        "node_count": len(node_ids),
                    },
                    level=logging.DEBUG,
                )
            else:
                log_event(
                    "tracker_update_skipped",
                    {"document_id": document_id, "reason": "no_tracker"},
                    level=logging.WARNING,
                )

            return Success(node_ids)

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

    def _find_document_nodes(self, document_id: str) -> List[str]:
        """
        Find all nodes belonging to a document after insertion using Qdrant.

        This replaces the old O(N) docstore iteration with an O(k) Qdrant query,
        where k = number of nodes for this document (typically 1-10).

        Returns list of node IDs.
        """
        doc_nodes: List[str] = []

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
                NOT_INITIALIZED_TRACKER,
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
                    self._delete_from_vector_store(document_id)
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

    def _delete_from_vector_store(self, document_id: str) -> None:
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
                NOT_INITIALIZED_TRACKER,
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
                    self._recreate_vector_collection()
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

    def _recreate_vector_collection(self) -> None:
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
        # Validate qdrant_client availability
        if not self.qdrant_client:
            log_event(
                "chunks_retrieval_skipped",
                {"document_id": document_id, "reason": "no_qdrant_client"},
                level=logging.DEBUG,
            )
            return internal_error(
                "Qdrant client not initialized",
                context={"document_id": document_id, "service": "document_service"},
            )

        # Validate tracker availability
        if not self.doc_tracker:
            return internal_error(
                NOT_INITIALIZED_TRACKER,
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
            enriched_chunks = self._retrieve_and_enrich_chunks(
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

    def _retrieve_and_enrich_chunks(
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
        from lifearchivist.storage.utils import ChunkInfoBuilder

        metadata = ChunkInfoBuilder.extract_metadata_from_payload(point.payload)
        start_char, end_char, relationships = ChunkInfoBuilder.parse_node_content(
            point.payload
        )

        return ChunkInfoBuilder.build_chunk_info(
            str(point.id),
            text,
            chunk_index,
            metadata,
            start_char,
            end_char,
            relationships,
        )

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

        return await self.doc_tracker.document_exists(document_id)  # type: ignore[no-any-return]

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

        return await self.doc_tracker.get_node_ids(document_id)  # type: ignore[no-any-return]
