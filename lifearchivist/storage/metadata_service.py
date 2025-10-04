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

    def __init__(self, index=None, doc_tracker=None):
        """
        Initialize the metadata service.

        Args:
            index: LlamaIndex VectorStoreIndex instance
            doc_tracker: Document tracker for metadata storage
        """
        self.index = index
        self.doc_tracker = doc_tracker

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
        Update metadata for a document in both vector store and docstore.

        This method updates metadata across all storage layers to maintain
        consistency. It handles both merge and replace modes for flexible
        metadata management.
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

            # Update metadata in docstore nodes
            if self.index and hasattr(self.index, "storage_context"):
                docstore = self.index.storage_context.docstore
                updated_nodes = await self._update_docstore_metadata(
                    docstore, node_ids, document_id, metadata_updates, merge_mode
                )
            else:
                updated_nodes = 0

            # Update the full metadata snapshot
            await self.doc_tracker.update_full_metadata(
                document_id, metadata_updates, merge_mode
            )

            log_event(
                "metadata_update_completed",
                {
                    "document_id": document_id,
                    "updated_nodes": updated_nodes,
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

    async def _update_docstore_metadata(
        self,
        docstore,
        node_ids: List[str],
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str,
    ) -> int:
        """
        Update metadata in docstore nodes.

        Returns the number of successfully updated nodes.
        """
        updated_nodes = 0

        for node_id in node_ids:
            try:
                # Get the node from docstore
                nodes = docstore.get_document(node_id, raise_error=False)
                if not nodes:
                    continue

                # Handle single node or list
                if not isinstance(nodes, list):
                    nodes = [nodes]

                for node in nodes:
                    if not hasattr(node, "metadata"):
                        continue

                    # Update metadata based on merge mode
                    if merge_mode == "replace":
                        node.metadata = {
                            **metadata_updates,
                            "document_id": document_id,
                        }
                    else:
                        # Merge with existing metadata
                        current_metadata = node.metadata or {}

                        # Handle special list fields
                        for key, value in metadata_updates.items():
                            if key in [
                                "content_dates",
                                "tags",
                                "provenance",
                            ] and isinstance(value, list):
                                existing = current_metadata.get(key, [])
                                if isinstance(existing, list):
                                    # Merge lists without duplicates
                                    merged = list(set(existing + value))
                                    current_metadata[key] = merged
                                else:
                                    current_metadata[key] = value
                            else:
                                current_metadata[key] = value

                        node.metadata = current_metadata

                    # Update the node in docstore
                    docstore.add_documents([node], allow_update=True)
                    updated_nodes += 1

            except Exception as e:
                log_event(
                    "node_metadata_update_failed",
                    {"node_id": node_id, "error": str(e)},
                    level=logging.DEBUG,
                )
                continue

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
            docstore: Docstore for text preview

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

        # Generate text preview from first node
        text_preview = self._get_text_preview(docstore, node_ids[0])

        return {
            "document_id": document_id,
            "metadata": full_metadata,
            "text_preview": text_preview,
            "node_count": len(node_ids),
        }

    # Filter matching now uses shared utility
    # Removed _metadata_matches_filter method - using MetadataFilterUtils.matches_filters instead

    def _get_text_preview(self, docstore, node_id: str, max_length: int = 200) -> str:
        """Get a text preview from a node."""
        try:
            nodes = docstore.get_document(node_id, raise_error=False)
            if not nodes:
                return ""

            if not isinstance(nodes, list):
                nodes = [nodes]

            first_node = nodes[0] if nodes else None
            if first_node and hasattr(first_node, "text"):
                text = first_node.text
                if len(text) > max_length:
                    return text[:max_length] + "..."
                return text

            return ""
        except Exception:
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
        Retrieve the full metadata for a document.

        This method first tries to get metadata from the dedicated metadata
        storage, then falls back to extracting from the first chunk if needed
        for backward compatibility.
        """
        try:
            # First try to get from stored full metadata
            if self.doc_tracker:
                full_metadata = await self.doc_tracker.get_full_metadata(document_id)
                if full_metadata:
                    return Success(full_metadata)

                # Fallback: get from first chunk if full metadata not found
                node_ids = await self.doc_tracker.get_node_ids(document_id)
                if not node_ids:
                    return not_found_error(
                        f"No nodes found for document '{document_id}'",
                        context={"document_id": document_id},
                    )

                if self.index and hasattr(self.index, "storage_context"):
                    docstore = self.index.storage_context.docstore
                    first_node_id = node_ids[0]
                    nodes = docstore.get_document(first_node_id, raise_error=False)

                    if nodes:
                        if not isinstance(nodes, list):
                            nodes = [nodes]
                        first_node = nodes[0] if nodes else None
                        if first_node and hasattr(first_node, "metadata"):
                            return Success(first_node.metadata or {})

            return not_found_error(
                f"Metadata not found for document '{document_id}'",
                context={"document_id": document_id},
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
        """Collect metrics for document analysis."""
        total_chars = 0
        total_words = 0
        chunk_sizes = []
        word_counts = []
        chunks_preview = []

        for _, node_id in enumerate(node_ids):
            try:
                nodes = docstore.get_document(node_id, raise_error=False)
                if not nodes:
                    continue

                if not isinstance(nodes, list):
                    nodes = [nodes]

                for node in nodes:
                    if not hasattr(node, "text"):
                        continue

                    text = node.text
                    text_length = len(text)
                    word_count = len(text.split())

                    total_chars += text_length
                    total_words += word_count
                    chunk_sizes.append(text_length)
                    word_counts.append(word_count)

                    # Add to preview (first 3 chunks)
                    if len(chunks_preview) < 3:
                        chunk_preview = {
                            "node_id": node_id,
                            "text": text[:200] + "..." if len(text) > 200 else text,
                            "text_length": text_length,
                            "word_count": word_count,
                        }
                        chunks_preview.append(chunk_preview)

            except Exception as e:
                log_event(
                    "node_analysis_error",
                    {"node_id": node_id, "error": str(e)},
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
