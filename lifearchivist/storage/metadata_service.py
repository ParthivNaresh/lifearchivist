"""
Metadata service for document metadata management.

This module provides a centralized interface for all metadata-related operations,
including updates, queries, and optimization of metadata storage.

All methods return Result types for explicit error handling and consistent
response formats across the API and UI layers.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from lifearchivist.storage.utils import MetadataFilterUtils, StorageConstants
from lifearchivist.utils.logging import log_event, track
from lifearchivist.utils.result import (
    Result,
    Success,
    internal_error,
    not_found_error,
)


class MetadataService(ABC):
    """Abstract base class for metadata services."""

    @abstractmethod
    async def update_document_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str = "update",
    ) -> Result[Dict[str, Any], str]:
        """
        Update metadata for a document.

        Args:
            document_id: The document to update
            metadata_updates: New metadata fields
            merge_mode: "update" to merge, "replace" to overwrite

        Returns:
            Result with update info or error details
        """
        pass

    @abstractmethod
    async def query_documents_by_metadata(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        offset: int = 0,
    ) -> Result[List[Dict[str, Any]], str]:
        """
        Query documents based on metadata filters.

        Args:
            filters: Dictionary of metadata field filters
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Result with list of documents or error
        """
        pass

    @abstractmethod
    async def get_full_document_metadata(
        self,
        document_id: str,
    ) -> Result[Dict[str, Any], str]:
        """
        Retrieve the full metadata for a document.

        Args:
            document_id: The document to retrieve metadata for

        Returns:
            Result with metadata dictionary or error
        """
        pass

    @abstractmethod
    async def get_document_analysis(
        self,
        document_id: str,
    ) -> Result[Dict[str, Any], str]:
        """
        Get comprehensive analysis of a document including metadata.

        Args:
            document_id: The document to analyze

        Returns:
            Result with document metrics and statistics or error
        """
        pass


class LlamaIndexMetadataService(MetadataService):
    """
    Metadata service implementation for LlamaIndex.

    This service handles all metadata operations including storage optimization,
    updates, queries, and retrieval of document metadata.
    """

    def __init__(self, index=None, doc_tracker=None, qdrant_client=None):
        """
        Initialize the metadata service.

        Args:
            index: LlamaIndex VectorStoreIndex instance
            doc_tracker: Document tracker for metadata storage
            qdrant_client: Qdrant client for direct queries (optional)
        """
        self.index = index
        self.doc_tracker = doc_tracker
        self.qdrant_client = qdrant_client

    @track(
        operation="update_document_metadata",
        include_args=["document_id", "merge_mode"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def update_document_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str = "update",
    ) -> Result[Dict[str, Any], str]:
        """
        Update metadata for a document in Redis (full) and Qdrant (minimal).

        This method updates metadata in the two authoritative stores:
        - Redis: Full metadata for retrieval
        - Qdrant: Minimal metadata for filtering (if fields are filterable)

        Note: We no longer update docstore as it's not used for queries.
        """
        try:
            # Check if document exists
            if not self.doc_tracker or not await self.doc_tracker.document_exists(
                document_id
            ):
                return not_found_error(
                    f"Document '{document_id}' not found",
                    context={"document_id": document_id},
                )

            node_ids = await self.doc_tracker.get_node_ids(document_id)
            if not node_ids:
                return not_found_error(
                    f"No nodes found for document '{document_id}'",
                    context={"document_id": document_id},
                )

            log_event(
                "metadata_update_started",
                {
                    "document_id": document_id,
                    "node_count": len(node_ids),
                    "merge_mode": merge_mode,
                    "update_fields": list(metadata_updates.keys()),
                },
            )

            # Update the full metadata in Redis (source of truth)
            await self.doc_tracker.update_full_metadata(
                document_id, metadata_updates, merge_mode
            )

            # Update minimal metadata in Qdrant if updating filterable fields
            updated_nodes = 0
            if self.qdrant_client:
                updated_nodes = await self._update_qdrant_metadata(
                    node_ids, document_id, metadata_updates, merge_mode
                )

            log_event(
                "metadata_update_completed",
                {
                    "document_id": document_id,
                    "redis_updated": True,
                    "qdrant_nodes_updated": updated_nodes,
                    "total_nodes": len(node_ids),
                },
            )

            return Success(
                {
                    "document_id": document_id,
                    "updated_nodes": updated_nodes,
                    "total_nodes": len(node_ids),
                    "merge_mode": merge_mode,
                    "updated_fields": list(metadata_updates.keys()),
                }
            )

        except Exception as e:
            log_event(
                "metadata_update_error",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to update metadata: {str(e)}",
                context={"document_id": document_id, "error_type": type(e).__name__},
            )

    async def _update_qdrant_metadata(
        self,
        node_ids: List[str],
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str,
    ) -> int:
        """
        Update minimal metadata in Qdrant for filterable fields.

        Only updates fields that are stored in Qdrant's minimal metadata:
        - document_id, title, mime_type, status
        - theme, primary_subtheme
        - uploaded_date, file_hash_short

        Returns the number of successfully updated nodes.
        """
        # Define which fields are stored in Qdrant minimal metadata
        QDRANT_FIELDS = {
            "document_id",
            "title",
            "mime_type",
            "status",
            "theme",
            "primary_subtheme",
            "uploaded_date",
            "file_hash_short",
        }

        # Check if any updated fields are in Qdrant
        updated_fields = set(metadata_updates.keys())
        qdrant_updates = updated_fields.intersection(QDRANT_FIELDS)

        if not qdrant_updates:
            # No filterable fields to update in Qdrant
            log_event(
                "qdrant_metadata_update_skipped",
                {
                    "document_id": document_id,
                    "reason": "no_filterable_fields",
                    "updated_fields": list(updated_fields),
                },
                level=logging.DEBUG,
            )
            return 0

        updated_nodes = 0

        try:

            # Prepare payload updates
            payload_updates = {}
            for field in qdrant_updates:
                payload_updates[field] = metadata_updates[field]

            # Update all nodes for this document in batch
            from qdrant_client.models import FieldCondition, Filter, MatchValue

            self.qdrant_client.set_payload(
                collection_name="lifearchivist",
                payload=payload_updates,
                points=Filter(
                    must=[
                        FieldCondition(
                            key="document_id",
                            match=MatchValue(value=document_id),
                        )
                    ]
                ),
            )

            updated_nodes = len(node_ids)

            log_event(
                "qdrant_metadata_updated",
                {
                    "document_id": document_id,
                    "nodes_updated": updated_nodes,
                    "fields_updated": list(qdrant_updates),
                },
            )

        except Exception as e:
            log_event(
                "qdrant_metadata_update_failed",
                {
                    "document_id": document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.WARNING,
            )
            # Don't fail the whole operation if Qdrant update fails
            # Redis is the source of truth

        return updated_nodes

    @track(
        operation="query_documents_by_metadata",
        include_args=["limit", "offset"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def query_documents_by_metadata(
        self,
        filters: Dict[str, Any],
        limit: int = 100,
        offset: int = 0,
    ) -> Result[List[Dict[str, Any]], str]:
        """
        Query documents based on metadata filters.

        This method efficiently queries documents using the tracker's query
        capabilities (Redis indexes for RedisDocumentTracker, or iteration
        for JSONDocumentTracker).
        """
        try:
            if not self.index or not self.doc_tracker:
                return Success([])

            log_event(
                "metadata_query_started",
                {
                    "filter_keys": list(filters.keys()) if filters else [],
                    "has_filters": bool(filters),
                    "limit": limit,
                    "offset": offset,
                },
            )

            # Get docstore for text previews
            docstore = self.index.storage_context.docstore

            # Use tracker's query capability if available (Redis), otherwise iterate
            matching_doc_ids = await self._get_matching_document_ids(filters)

            log_event(
                "metadata_query_candidates",
                {
                    "candidates_found": len(matching_doc_ids),
                    "will_paginate": len(matching_doc_ids) > limit,
                },
            )

            # Build full document info for matching documents
            matching_documents = []
            for document_id in matching_doc_ids:
                try:
                    doc_info = await self._build_document_info(document_id, docstore)
                    if doc_info:
                        matching_documents.append(doc_info)
                except Exception as e:
                    log_event(
                        "document_info_build_failed",
                        {"document_id": document_id, "error": str(e)},
                        level=logging.DEBUG,
                    )
                    continue

            # Apply pagination
            paginated_results = matching_documents[offset : offset + limit]

            # Get total document count for logging
            total_docs = await self.doc_tracker.get_document_count()

            log_event(
                "metadata_query_completed",
                {
                    "total_documents": total_docs,
                    "documents_matched": len(matching_documents),
                    "results_returned": len(paginated_results),
                },
            )

            return Success(paginated_results)

        except Exception as e:
            log_event(
                "metadata_query_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to query documents: {str(e)}",
                context={"error_type": type(e).__name__},
            )

    async def _get_matching_document_ids(self, filters: Dict[str, Any]) -> List[str]:
        """
        Get document IDs matching filters using tracker's query capabilities.

        For RedisDocumentTracker: Uses indexed queries (O(k) where k = matches)
        For JSONDocumentTracker: Falls back to iteration (O(n) where n = total docs)
        """
        # Check if tracker has query_by_multiple_filters (Redis implementation)
        if hasattr(self.doc_tracker, "query_by_multiple_filters"):
            # Use Redis indexed queries - much faster!
            return await self.doc_tracker.query_by_multiple_filters(filters)

        # Fallback for JSONDocumentTracker - iterate through all documents
        # This is the old O(n) approach, but necessary for JSON tracker
        matching_ids = []
        all_doc_ids = await self.doc_tracker.get_all_document_ids()

        for document_id in all_doc_ids:
            # Get metadata and check filters
            metadata = await self.doc_tracker.get_full_metadata(document_id)
            if metadata and MetadataFilterUtils.matches_filters(metadata, filters):
                matching_ids.append(document_id)

        return matching_ids

    async def _build_document_info(
        self,
        document_id: str,
        docstore,
    ) -> Optional[Dict[str, Any]]:
        """
        Build complete document info for API response.

        Args:
            document_id: Document to build info for
            docstore: Docstore for text preview (deprecated, uses Qdrant now)

        Returns:
            Document info dictionary or None if document can't be loaded
        """
        # Get node IDs
        node_ids = await self.doc_tracker.get_node_ids(document_id)
        if not node_ids:
            return None

        # Get full metadata
        full_metadata_result = await self.get_full_document_metadata(document_id)
        if full_metadata_result.is_failure():
            return None

        full_metadata = full_metadata_result.unwrap()

        # Generate text preview from first node using Qdrant
        text_preview = await self._get_text_preview_from_qdrant(node_ids[0])

        return {
            "document_id": document_id,
            "metadata": full_metadata,
            "text_preview": text_preview,
            "node_count": len(node_ids),
        }

    # Filter matching now uses shared utility
    # Removed _metadata_matches_filter method - using MetadataFilterUtils.matches_filters instead

    async def _get_text_preview_from_qdrant(
        self, node_id: str, max_length: int = 200
    ) -> str:
        """
        Get a text preview from a node using Qdrant directly.

        This replaces the old docstore-based method.
        """
        try:
            if not self.qdrant_client:
                return ""

            from lifearchivist.storage.utils import QdrantNodeUtils

            # Retrieve node from Qdrant
            points = self.qdrant_client.retrieve(
                collection_name="lifearchivist",
                ids=[node_id],
                with_payload=True,
                with_vectors=False,
            )

            if not points or len(points) == 0:
                return ""

            # Extract text using utility
            node_payload = points[0].payload
            return QdrantNodeUtils.extract_text_preview(node_payload, max_length)

        except Exception as e:
            log_event(
                "text_preview_extraction_failed",
                {"node_id": node_id, "error": str(e)},
                level=logging.DEBUG,
            )
            return ""

    @track(
        operation="get_full_document_metadata",
        include_args=["document_id"],
        include_result=False,  # Don't log full metadata (could be large)
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_full_document_metadata(
        self,
        document_id: str,
    ) -> Result[Dict[str, Any], str]:
        """
        Retrieve the full metadata for a document from Redis.

        Redis is the single source of truth for full document metadata.
        """
        try:
            if not self.doc_tracker:
                return internal_error(
                    "Document tracker not initialized",
                    context={"document_id": document_id},
                )

            # Get full metadata from Redis (source of truth)
            full_metadata = await self.doc_tracker.get_full_metadata(document_id)

            if full_metadata:
                return Success(full_metadata)

            # If not found, check if document exists at all
            if not await self.doc_tracker.document_exists(document_id):
                return not_found_error(
                    f"Document '{document_id}' not found",
                    context={"document_id": document_id},
                )

            # Document exists but has no metadata (shouldn't happen)
            log_event(
                "metadata_missing_for_existing_document",
                {"document_id": document_id},
                level=logging.WARNING,
            )

            return not_found_error(
                f"Metadata not found for document '{document_id}'",
                context={"document_id": document_id, "reason": "metadata_missing"},
            )

        except Exception as e:
            log_event(
                "get_full_metadata_error",
                {
                    "document_id": document_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to retrieve metadata: {str(e)}",
                context={"document_id": document_id, "error_type": type(e).__name__},
            )

    @track(
        operation="get_document_analysis",
        include_args=["document_id"],
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
    async def get_document_analysis(
        self,
        document_id: str,
    ) -> Result[Dict[str, Any], str]:
        """
        Get comprehensive analysis of a document.

        This method provides detailed metrics and statistics about a document,
        including metadata, processing information, and storage details.
        """
        try:
            if not self.index:
                return internal_error(
                    "Index not initialized", context={"document_id": document_id}
                )

            # Check if document exists
            if not self.doc_tracker or not await self.doc_tracker.document_exists(
                document_id
            ):
                return not_found_error(
                    f"Document '{document_id}' not found in index",
                    context={"document_id": document_id},
                )

            node_ids = await self.doc_tracker.get_node_ids(document_id)
            if not node_ids:
                return not_found_error(
                    f"No nodes found for document '{document_id}'",
                    context={"document_id": document_id},
                )

            # Get docstore
            docstore = self.index.storage_context.docstore

            # Get FULL metadata for this document
            metadata_result = await self.get_full_document_metadata(document_id)
            if metadata_result.is_failure():
                return metadata_result

            full_metadata = metadata_result.value

            # Collect metrics
            analysis = await self._collect_document_metrics(docstore, node_ids)

            log_event(
                "document_analysis_completed",
                {
                    "document_id": document_id,
                    "node_count": analysis["num_chunks"],
                    "total_chars": analysis["total_chars"],
                    "total_words": analysis["total_words"],
                },
            )

            # Return the analysis with FULL metadata
            return Success(
                {
                    "document_id": document_id,
                    "status": full_metadata.get("status", "indexed"),
                    "metadata": full_metadata,
                    "processing_info": analysis["processing_info"],
                    "storage_info": self._get_storage_info(),
                    "chunks_preview": analysis["chunks_preview"],
                }
            )

        except Exception as e:
            log_event(
                "document_analysis_failed",
                {
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return internal_error(
                f"Failed to analyze document: {str(e)}",
                context={"document_id": document_id, "error_type": type(e).__name__},
            )

    async def _collect_document_metrics(
        self,
        docstore,
        node_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Collect metrics for document analysis using Qdrant.

        Args:
            docstore: Deprecated parameter, kept for backward compatibility
            node_ids: List of node IDs to analyze
        """
        total_chars = 0
        total_words = 0
        chunk_sizes = []
        word_counts = []
        chunks_preview = []

        if not self.qdrant_client:
            # Fallback to empty metrics if Qdrant not available
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

        from lifearchivist.storage.utils import QdrantNodeUtils

        # Retrieve all nodes from Qdrant in batch
        try:
            points = self.qdrant_client.retrieve(
                collection_name="lifearchivist",
                ids=node_ids,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as e:
            log_event(
                "qdrant_batch_retrieval_error",
                {"node_count": len(node_ids), "error": str(e)},
                level=logging.ERROR,
            )
            # Return empty metrics on error
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

        # Process each point
        for point in points:
            try:
                # Extract text from Qdrant payload
                text = QdrantNodeUtils.extract_text_from_node(point.payload)
                if not text:
                    continue

                text_length = len(text)
                word_count = len(text.split())

                total_chars += text_length
                total_words += word_count
                chunk_sizes.append(text_length)
                word_counts.append(word_count)

                # Add to preview (first 3 chunks)
                if len(chunks_preview) < 3:
                    chunk_preview = {
                        "node_id": str(point.id),
                        "text": text[:200] + "..." if len(text) > 200 else text,
                        "text_length": text_length,
                        "word_count": word_count,
                    }
                    chunks_preview.append(chunk_preview)

            except Exception as e:
                log_event(
                    "node_analysis_error",
                    {"node_id": str(point.id), "error": str(e)},
                    level=logging.DEBUG,
                )
                continue

        # Calculate statistics
        num_chunks = len(chunk_sizes)
        avg_chunk_size = sum(chunk_sizes) / num_chunks if num_chunks > 0 else 0
        avg_word_count = sum(word_counts) / num_chunks if num_chunks > 0 else 0
        min_chunk_size = min(chunk_sizes) if chunk_sizes else 0
        max_chunk_size = max(chunk_sizes) if chunk_sizes else 0

        return {
            "total_chars": total_chars,
            "total_words": total_words,
            "num_chunks": num_chunks,
            "chunks_preview": chunks_preview,
            "processing_info": {
                "total_chars": total_chars,
                "total_words": total_words,
                "num_chunks": num_chunks,
                "avg_chunk_size": round(avg_chunk_size, 2),
                "min_chunk_size": min_chunk_size,
                "max_chunk_size": max_chunk_size,
                "avg_word_count": round(avg_word_count, 2),
            },
        }

    def _get_storage_info(self) -> Dict[str, Any]:
        """Get storage information for document analysis."""
        return {
            "docstore_type": "SimpleDocumentStore",
            "vector_store_type": "QdrantVectorStore",
            "text_splitter": "SentenceSplitter",
            "chunk_size": StorageConstants.DEFAULT_CHUNK_SIZE,
            "chunk_overlap": StorageConstants.DEFAULT_CHUNK_OVERLAP,
        }

    def create_minimal_chunk_metadata(
        self,
        full_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create minimal metadata for chunks to avoid bloat.

        This method optimizes metadata storage by including only essential
        fields needed for search and retrieval, significantly reducing
        storage overhead.
        """
        minimal = {
            "document_id": full_metadata.get("document_id"),
            "title": full_metadata.get("title", ""),
            "mime_type": full_metadata.get("mime_type", ""),
            "status": full_metadata.get("status", "ready"),
        }

        # Add theme information if present (for filtering)
        if "theme" in full_metadata:
            theme_data = full_metadata["theme"]
            if isinstance(theme_data, dict):
                minimal["theme"] = theme_data.get("theme", "Unclassified")
                minimal["primary_subtheme"] = theme_data.get("primary_subtheme", "")
            else:
                minimal["theme"] = theme_data

        # Add essential dates (keep them short)
        if "uploaded_at" in full_metadata:
            uploaded = full_metadata["uploaded_at"]
            if isinstance(uploaded, str) and len(uploaded) > 10:
                minimal["uploaded_date"] = uploaded[:10]

        # Add file hash (first 8 chars only for dedup checking)
        if "file_hash" in full_metadata:
            minimal["file_hash_short"] = full_metadata["file_hash"][:8]

        # Log the size reduction
        self._log_metadata_optimization(full_metadata, minimal)

        return minimal

    def _log_metadata_optimization(
        self,
        full_metadata: Dict[str, Any],
        minimal_metadata: Dict[str, Any],
    ) -> None:
        """Log metadata optimization metrics."""
        full_size = len(json.dumps(full_metadata))
        minimal_size = len(json.dumps(minimal_metadata))

        log_event(
            "metadata_size_reduction",
            {
                "document_id": full_metadata.get("document_id"),
                "full_metadata_size": full_size,
                "minimal_metadata_size": minimal_size,
                "reduction_percent": (
                    round((1 - minimal_size / full_size) * 100, 1)
                    if full_size > 0
                    else 0
                ),
                "fields_kept": list(minimal_metadata.keys()),
            },
            level=logging.DEBUG,
        )
