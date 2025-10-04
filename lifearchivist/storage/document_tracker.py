"""
Document tracking system for managing document-to-node mappings and metadata.

This module provides an abstraction layer for tracking documents in the LlamaIndex system,
allowing for different persistence backends while maintaining a consistent interface.
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from lifearchivist.utils.logging import log_event


class DocumentTracker(ABC):
    """
    Abstract base class for document tracking.

    Manages the relationship between document IDs and their associated nodes,
    as well as full document metadata storage.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the tracker and any required resources."""
        pass

    @abstractmethod
    async def add_document(self, document_id: str, node_ids: List[str]) -> None:
        """
        Track a new document and its associated nodes.

        Args:
            document_id: Unique identifier for the document
            node_ids: List of node IDs created from this document
        """
        pass

    @abstractmethod
    async def get_node_ids(self, document_id: str) -> Optional[List[str]]:
        """
        Get the list of node IDs for a document.

        Args:
            document_id: The document to look up

        Returns:
            List of node IDs, or None if document not found
        """
        pass

    @abstractmethod
    async def remove_document(self, document_id: str) -> bool:
        """
        Remove a document from tracking.

        Args:
            document_id: The document to remove

        Returns:
            True if document was removed, False if not found
        """
        pass

    @abstractmethod
    async def document_exists(self, document_id: str) -> bool:
        """
        Check if a document is being tracked.

        Args:
            document_id: The document to check

        Returns:
            True if document exists in tracker
        """
        pass

    @abstractmethod
    async def get_document_count(self) -> int:
        """
        Get the total number of tracked documents.

        Returns:
            Count of documents (excluding metadata entries)
        """
        pass

    @abstractmethod
    async def get_all_document_ids(self) -> List[str]:
        """
        Get all tracked document IDs.

        Returns:
            List of all document IDs (excluding metadata entries)
        """
        pass

    @abstractmethod
    async def store_full_metadata(
        self, document_id: str, metadata: Dict[str, Any]
    ) -> None:
        """
        Store complete metadata for a document.

        This is separate from node tracking and stores the full document metadata
        that may be too large to duplicate across all nodes.

        Args:
            document_id: The document this metadata belongs to
            metadata: Complete metadata dictionary
        """
        pass

    @abstractmethod
    async def get_full_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete metadata for a document.

        Args:
            document_id: The document to get metadata for

        Returns:
            Full metadata dictionary, or None if not found
        """
        pass

    @abstractmethod
    async def clear_all(self) -> Dict[str, Any]:
        """
        Clear all tracked documents and metadata.

        Returns:
            Statistics about what was cleared
        """
        pass


class JSONDocumentTracker(DocumentTracker):
    """
    JSON file-based implementation of document tracking.

    This implementation matches the current behavior of LlamaIndexQdrantService,
    storing document-to-node mappings and full metadata in a JSON file.

    File structure:
    {
        "document_id": ["node_id1", "node_id2", ...],  # Node mappings
        "document_id_full_metadata": {...},            # Full metadata
        ...
    }
    """

    def __init__(self, storage_path: Path):
        """
        Initialize the JSON document tracker.

        Args:
            storage_path: Path to the JSON file for persistence
        """
        self.storage_path = Path(storage_path)
        # In-memory cache of the document tracker data
        self.data: Dict[str, Union[List[str], Dict[str, Any]]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Load existing data from JSON file or create new file."""
        if self._initialized:
            return

        # Ensure parent directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing data if file exists
        if self.storage_path.exists():
            try:
                async with self._lock:
                    with open(self.storage_path, "r") as f:
                        self.data = json.load(f)

                # Count documents for logging
                doc_count = sum(
                    1 for key in self.data.keys() if not key.endswith("_full_metadata")
                )

                log_event(
                    "document_tracker_loaded",
                    {
                        "path": str(self.storage_path),
                        "document_count": doc_count,
                        "total_entries": len(self.data),
                    },
                    level=logging.DEBUG,
                )
            except (json.JSONDecodeError, IOError, OSError) as e:
                # Log error but start with empty data
                log_event(
                    "document_tracker_load_failed",
                    {
                        "path": str(self.storage_path),
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )
                self.data = {}
        else:
            # Start with empty tracker
            self.data = {}
            await self._save()

            log_event(
                "document_tracker_created",
                {
                    "path": str(self.storage_path),
                },
                level=logging.DEBUG,
            )

        self._initialized = True

    async def _save(self) -> None:
        """
        Save the current data to JSON file.

        Uses atomic write to prevent corruption.
        """
        async with self._lock:
            # Use temporary file for atomic write
            temp_path = self.storage_path.with_suffix(".tmp")

            try:
                # Write to temporary file
                with open(temp_path, "w") as f:
                    json.dump(self.data, f, indent=2)

                # Atomic rename to replace original file
                temp_path.replace(self.storage_path)

            except (IOError, OSError) as e:
                # Clean up temp file if it exists
                if temp_path.exists():
                    temp_path.unlink()

                log_event(
                    "document_tracker_save_failed",
                    {
                        "path": str(self.storage_path),
                        "error": str(e),
                    },
                    level=logging.ERROR,
                )
                raise

    async def add_document(self, document_id: str, node_ids: List[str]) -> None:
        """Track a new document and its nodes."""
        if not self._initialized:
            await self.initialize()

        async with self._lock:
            # Store the node mappings
            self.data[document_id] = node_ids

        # Save to disk
        await self._save()

        log_event(
            "document_tracked",
            {
                "document_id": document_id,
                "node_count": len(node_ids),
            },
            level=logging.DEBUG,
        )

    async def get_node_ids(self, document_id: str) -> Optional[List[str]]:
        """Get node IDs for a document."""
        if not self._initialized:
            await self.initialize()

        # Get the data for this document
        data = self.data.get(document_id)

        # Ensure it's a list of node IDs, not metadata
        if isinstance(data, list):
            return data

        return None

    async def remove_document(self, document_id: str) -> bool:
        """Remove a document and its metadata from tracking."""
        if not self._initialized:
            await self.initialize()

        removed = False

        async with self._lock:
            # Remove node mappings
            if document_id in self.data:
                del self.data[document_id]
                removed = True

            # Remove full metadata if it exists
            metadata_key = f"{document_id}_full_metadata"
            if metadata_key in self.data:
                del self.data[metadata_key]

        if removed:
            # Save changes to disk
            await self._save()

            log_event(
                "document_untracked",
                {
                    "document_id": document_id,
                },
                level=logging.DEBUG,
            )

        return removed

    async def document_exists(self, document_id: str) -> bool:
        """Check if a document is tracked."""
        if not self._initialized:
            await self.initialize()

        # Check for node mappings (not metadata entries)
        return document_id in self.data and isinstance(self.data[document_id], list)

    async def get_document_count(self) -> int:
        """Get count of tracked documents."""
        if not self._initialized:
            await self.initialize()

        # Count only actual documents, not metadata entries
        count = 0
        for key in self.data.keys():
            if not key.endswith("_full_metadata"):
                count += 1

        return count

    async def get_all_document_ids(self) -> List[str]:
        """Get all document IDs."""
        if not self._initialized:
            await self.initialize()

        # Return only document IDs, not metadata keys
        doc_ids = []
        for key in self.data.keys():
            if not key.endswith("_full_metadata"):
                doc_ids.append(key)

        return doc_ids

    async def store_full_metadata(
        self, document_id: str, metadata: Dict[str, Any]
    ) -> None:
        """Store complete metadata for a document."""
        if not self._initialized:
            await self.initialize()

        # Use special key format for full metadata
        metadata_key = f"{document_id}_full_metadata"

        async with self._lock:
            self.data[metadata_key] = metadata

        # Save to disk
        await self._save()

        log_event(
            "document_metadata_stored",
            {
                "document_id": document_id,
                "metadata_size": len(json.dumps(metadata)),
            },
            level=logging.DEBUG,
        )

    async def get_full_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve complete metadata for a document."""
        if not self._initialized:
            await self.initialize()

        # Look for the metadata entry
        metadata_key = f"{document_id}_full_metadata"
        metadata = self.data.get(metadata_key)

        # Type check to ensure it's metadata, not node list
        if isinstance(metadata, dict):
            return metadata

        return None

    async def clear_all(self) -> Dict[str, Any]:
        """Clear all tracked documents and metadata."""
        if not self._initialized:
            await self.initialize()

        # Get counts before clearing
        doc_count = await self.get_document_count()
        total_entries = len(self.data)

        async with self._lock:
            self.data = {}

        # Save empty state to disk
        await self._save()

        log_event(
            "document_tracker_cleared",
            {
                "documents_cleared": doc_count,
                "total_entries_cleared": total_entries,
            },
        )

        return {
            "documents_cleared": doc_count,
            "total_entries_cleared": total_entries,
        }

    async def update_full_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str = "update",
    ) -> bool:
        """
        Update metadata for a document.

        Args:
            document_id: The document to update
            metadata_updates: New metadata fields
            merge_mode: "update" to merge, "replace" to overwrite

        Returns:
            True if metadata was updated
        """
        if not self._initialized:
            await self.initialize()

        metadata_key = f"{document_id}_full_metadata"

        async with self._lock:
            if merge_mode == "replace":
                # Replace entire metadata
                self.data[metadata_key] = {
                    "document_id": document_id,
                    **metadata_updates,
                }
            else:
                # Merge with existing metadata
                existing = self.data.get(metadata_key, {})
                if not isinstance(existing, dict):
                    existing = {}

                # Handle special list fields that should be merged
                for key, value in metadata_updates.items():
                    if key in ["content_dates", "tags", "provenance"] and isinstance(
                        value, list
                    ):
                        existing_val = existing.get(key, [])
                        if isinstance(existing_val, list):
                            # Merge lists without duplicates
                            merged = list(set(existing_val + value))
                            existing[key] = merged
                        else:
                            existing[key] = value
                    else:
                        # Regular update
                        existing[key] = value

                self.data[metadata_key] = existing

        # Save changes
        await self._save()

        return True

    # Dictionary-like interface for backward compatibility
    def __contains__(self, key: str) -> bool:
        """Support 'in' operator for checking document existence."""
        # This is synchronous for backward compatibility
        # Check if it's a document (not metadata)
        return key in self.data and isinstance(self.data.get(key), list)

    def __getitem__(self, key: str):
        """Support dictionary-style access."""
        return self.data.get(key)

    def __setitem__(self, key: str, value):
        """Support dictionary-style assignment."""
        self.data[key] = value

    def __delitem__(self, key: str):
        """Support dictionary-style deletion."""
        if key in self.data:
            del self.data[key]

    def __len__(self) -> int:
        """Return the number of tracked documents."""
        # Count only documents, not metadata entries
        return sum(1 for key in self.data.keys() if not key.endswith("_full_metadata"))

    def get(self, key: str, default=None):
        """Dictionary-style get with default."""
        return self.data.get(key, default)

    def keys(self):
        """Return all keys (for iteration)."""
        return self.data.keys()

    def items(self):
        """Return all items (for iteration)."""
        return self.data.items()
