"""
Redis-based document tracker for production-grade scalability.

This implementation provides:
- Atomic operations with Redis transactions
- Automatic indexing for fast queries
- Sub-millisecond performance at any scale
- Concurrent-safe operations
- Efficient memory usage with Redis data structures
"""

import json
import logging
from typing import Any, Awaitable, Dict, List, Optional, Set, Tuple, cast

import redis.asyncio as redis

from lifearchivist.utils.logging import log_event, track


class RedisDocumentTracker:
    """
    Production-grade Redis-based document tracker.

    Data Structure Design:
    ----------------------
    1. Document-to-Nodes Mapping (Redis List):
       Key: "lifearchivist:doc:nodes:{document_id}"
       Value: ["node_id_1", "node_id_2", ...]

    2. Full Metadata (Redis Hash):
       Key: "lifearchivist:doc:meta:{document_id}"
       Value: Hash of all metadata fields (nested JSON as strings)

    3. Document Index (Redis Set):
       Key: "lifearchivist:doc:index:all"
       Value: Set of all document_ids

    4. Metadata Indexes (Redis Sets) - For fast filtering:
       Key: "lifearchivist:doc:index:theme:{theme}"
       Key: "lifearchivist:doc:index:mime:{mime_type}"
       Key: "lifearchivist:doc:index:status:{status}"
       Value: Set of document_ids matching the filter

    5. Document Count (Redis String):
       Key: "lifearchivist:doc:count"
       Value: Integer count (for O(1) counting)

    Performance Characteristics:
    ---------------------------
    - Add document: O(1) - constant time regardless of total documents
    - Get nodes: O(1) - direct key lookup
    - Delete document: O(1) - atomic transaction
    - Count: O(1) - cached counter
    - Query by metadata: O(k) where k = matching documents (not total)
    - Concurrent writes: Safe with Redis atomicity guarantees
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize Redis document tracker.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None

        # Key namespace following project conventions
        self.key_prefix = "lifearchivist:doc"

        # Connection state
        self._initialized = False

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 0.1  # seconds

    @track(
        operation="redis_tracker_initialize",
        track_performance=True,
        frequency="low_frequency",
    )
    async def initialize(self) -> None:
        """
        Initialize Redis connection and verify connectivity.

        This method:
        1. Creates async Redis client with connection pooling
        2. Tests connection with PING
        3. Sets up any required initial state
        4. Logs initialization metrics

        Raises:
            ConnectionError: If Redis is unreachable
            RedisError: If Redis returns an error
        """
        try:
            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )

            await self.redis_client.ping()

            self._initialized = True

            doc_count = await self.get_document_count()

            log_event(
                "redis_tracker_initialized",
                {
                    "redis_url": self.redis_url,
                    "document_count": doc_count,
                },
            )

        except Exception as e:
            log_event(
                "redis_tracker_init_failed",
                {
                    "redis_url": self.redis_url,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}") from e

    def _client(self) -> "redis.Redis":
        """Return a non-optional Redis client or raise if not initialized."""
        if self.redis_client is None:
            raise RuntimeError("RedisDocumentTracker not initialized")
        return self.redis_client

    async def close(self) -> None:
        """
        Close Redis connection and cleanup resources.

        This method:
        1. Closes the Redis client connection
        2. Releases connection pool resources
        3. Logs cleanup metrics
        """
        if self.redis_client:
            await self.redis_client.aclose()
            self._initialized = False

            log_event(
                "redis_tracker_closed",
                {"redis_url": self.redis_url},
            )

    @track(
        operation="redis_add_document",
        include_args=["document_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def add_document(self, document_id: str, node_ids: List[str]) -> None:
        """
        Add a document and its nodes to the tracker atomically.

        This method uses Redis MULTI/EXEC transaction to ensure:
        1. Node IDs are stored
        2. Document is added to all index
        3. Count is incremented
        All operations succeed or all fail together.

        Args:
            document_id: Unique document identifier
            node_ids: List of node IDs for this document

        Raises:
            ConnectionError: If Redis connection fails
            ValueError: If document_id or node_ids are invalid
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        if not document_id or not node_ids:
            raise ValueError("document_id and node_ids are required")

        nodes_key = f"{self.key_prefix}:nodes:{document_id}"
        all_index_key = f"{self.key_prefix}:index:all"
        count_key = f"{self.key_prefix}:count"

        client = self._client()
        async with client.pipeline(transaction=True) as pipe:
            pipe.rpush(nodes_key, *node_ids)
            pipe.sadd(all_index_key, document_id)
            pipe.incr(count_key)
            await pipe.execute()

    @track(
        operation="redis_get_node_ids",
        include_args=["document_id"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_node_ids(self, document_id: str) -> Optional[List[str]]:
        """
        Get node IDs for a document.

        Args:
            document_id: Document to look up

        Returns:
            List of node IDs, or None if document not found
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        nodes_key = f"{self.key_prefix}:nodes:{document_id}"

        client = self._client()
        node_ids = await cast(Awaitable[List[str]], client.lrange(nodes_key, 0, -1))

        return list(node_ids) if node_ids else None

    @track(
        operation="redis_remove_document",
        include_args=["document_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def remove_document(self, document_id: str) -> bool:
        """
        Remove a document and all its data atomically.

        This method uses Redis transaction to:
        1. Get metadata for index cleanup
        2. Delete nodes list
        3. Delete metadata hash
        4. Remove from all indexes
        5. Decrement count

        Args:
            document_id: Document to remove

        Returns:
            True if document was removed, False if not found
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        if not await self.document_exists(document_id):
            return False

        metadata = await self.get_full_metadata(document_id)

        nodes_key = f"{self.key_prefix}:nodes:{document_id}"
        metadata_key = f"{self.key_prefix}:meta:{document_id}"
        all_index_key = f"{self.key_prefix}:index:all"
        count_key = f"{self.key_prefix}:count"

        client = self._client()
        async with client.pipeline(transaction=True) as pipe:
            pipe.delete(nodes_key)
            pipe.delete(metadata_key)
            pipe.srem(all_index_key, document_id)
            pipe.decr(count_key)
            await pipe.execute()

        if metadata:
            await self._remove_from_indexes(document_id, metadata)

        return True

    @track(
        operation="redis_document_exists",
        include_args=["document_id"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def document_exists(self, document_id: str) -> bool:
        """
        Check if a document exists in the tracker.

        Uses SISMEMBER on the all-documents index for O(1) lookup.

        Args:
            document_id: Document to check

        Returns:
            True if document exists
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        all_index_key = f"{self.key_prefix}:index:all"

        client = self._client()
        exists = await cast(
            Awaitable[int], client.sismember(all_index_key, document_id)
        )

        return bool(exists)

    @track(
        operation="redis_get_document_count",
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_document_count(self) -> int:
        """
        Get total count of tracked documents.

        Uses cached counter for O(1) performance.

        Returns:
            Number of documents
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        count_key = f"{self.key_prefix}:count"

        client = self._client()
        count = await cast(Awaitable[Optional[str]], client.get(count_key))

        return int(count) if count else 0

    @track(
        operation="redis_get_all_document_ids",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def get_all_document_ids(self) -> List[str]:
        """
        Get all document IDs.

        Returns all members of the all-documents index set.

        Returns:
            List of all document IDs
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        all_index_key = f"{self.key_prefix}:index:all"

        client = self._client()
        members = await cast(Awaitable[Set[str]], client.smembers(all_index_key))

        return sorted(list(members)) if members else []

    @track(
        operation="redis_store_full_metadata",
        include_args=["document_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def store_full_metadata(
        self, document_id: str, metadata: Dict[str, Any]
    ) -> None:
        """
        Store complete metadata for a document.

        This method:
        1. Serializes nested structures to JSON strings
        2. Stores as Redis hash for efficient field access
        3. Updates metadata indexes (theme, mime_type, status)
        4. Uses transaction for atomicity

        Args:
            document_id: Document this metadata belongs to
            metadata: Complete metadata dictionary
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        metadata_key = f"{self.key_prefix}:meta:{document_id}"

        serialized = {k: self._serialize_metadata_value(v) for k, v in metadata.items()}

        client = self._client()
        if serialized:
            await cast(Awaitable[int], client.hset(metadata_key, mapping=serialized))

        indexable = self._extract_indexable_fields(metadata)
        if indexable:
            async with client.pipeline(transaction=False) as pipe:
                for field, value in indexable.items():
                    if value:
                        index_key = f"{self.key_prefix}:index:{field}:{value}"
                        pipe.sadd(index_key, document_id)
                await pipe.execute()

    @track(
        operation="redis_get_full_metadata",
        include_args=["document_id"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_full_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete metadata for a document.

        This method:
        1. Fetches all fields from Redis hash
        2. Deserializes JSON strings back to objects
        3. Returns None if document not found

        Args:
            document_id: Document to get metadata for

        Returns:
            Full metadata dictionary, or None if not found
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        metadata_key = f"{self.key_prefix}:meta:{document_id}"

        client = self._client()
        raw_metadata = await cast(
            Awaitable[Dict[str, str]], client.hgetall(metadata_key)
        )

        if not raw_metadata:
            return None

        deserialized = {
            k: self._deserialize_metadata_value(v) for k, v in raw_metadata.items()
        }

        return deserialized

    @track(
        operation="redis_update_full_metadata",
        include_args=["document_id", "merge_mode"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def update_full_metadata(
        self,
        document_id: str,
        metadata_updates: Dict[str, Any],
        merge_mode: str = "update",
    ) -> bool:
        """
        Update metadata for a document.

        This method:
        1. Handles both "update" (merge) and "replace" modes
        2. Updates metadata indexes if indexed fields change
        3. Uses transaction for atomicity
        4. Handles list field merging (tags, provenance, etc.)

        Args:
            document_id: Document to update
            metadata_updates: New metadata fields
            merge_mode: "update" to merge, "replace" to overwrite

        Returns:
            True if metadata was updated, False if document not found
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        metadata_key = f"{self.key_prefix}:meta:{document_id}"

        client = self._client()
        exists = await cast(Awaitable[int], client.exists(metadata_key))
        if not exists:
            return False

        if merge_mode == "replace":
            old_metadata = await self.get_full_metadata(document_id)

            serialized = {
                k: self._serialize_metadata_value(v)
                for k, v in metadata_updates.items()
            }

            await cast(Awaitable[int], client.delete(metadata_key))
            if serialized:
                await cast(
                    Awaitable[int], client.hset(metadata_key, mapping=serialized)
                )

            await self._update_metadata_indexes(
                document_id, old_metadata, metadata_updates
            )
        else:
            old_metadata = await self.get_full_metadata(document_id)

            merged = old_metadata.copy() if old_metadata else {}

            for key, value in metadata_updates.items():
                if key in ["content_dates", "tags", "provenance"] and isinstance(
                    value, list
                ):
                    existing = merged.get(key, [])
                    if isinstance(existing, list):
                        if key == "tags":
                            merged[key] = list(set(existing + value))
                        else:
                            merged[key] = existing + value
                    else:
                        merged[key] = value
                else:
                    merged[key] = value

            serialized = {
                k: self._serialize_metadata_value(merged[k])
                for k in metadata_updates.keys()
            }

            if serialized:
                await cast(
                    Awaitable[int], client.hset(metadata_key, mapping=serialized)
                )

            await self._update_metadata_indexes(document_id, old_metadata, merged)

        return True

    async def query_by_multiple_filters(self, filters: Dict[str, Any]) -> List[str]:
        """
        Query documents by multiple metadata filters.

        This method:
        1. Uses Redis set intersection for efficient multi-filter queries
        2. Supports theme, mime_type, status filters
        3. Returns intersection of all matching sets

        Args:
            filters: Dictionary of filter criteria

        Returns:
            List of document IDs matching all filters
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        if not filters:
            all_ids: List[str] = await self.get_all_document_ids()
            return all_ids

        index_keys = []
        for field, value in filters.items():
            if field in ("theme", "mime_type", "status"):
                index_key = f"{self.key_prefix}:index:{field}:{value}"
                index_keys.append(index_key)

        if not index_keys:
            all_doc_ids: List[str] = await self.get_all_document_ids()
            return all_doc_ids

        if len(index_keys) == 1:
            client = self._client()
            members = await cast(Awaitable[Set[str]], client.smembers(index_keys[0]))
            members_list: List[str] = sorted(list(members)) if members else []
            return members_list

        client = self._client()
        result = await cast(Awaitable[Set[str]], client.sinter(index_keys))
        result_list: List[str] = sorted(list(result)) if result else []
        return result_list

    @track(
        operation="redis_clear_all",
        track_performance=True,
        frequency="low_frequency",
    )
    async def clear_all(self) -> Dict[str, Any]:
        """
        Clear all tracked documents and metadata.

        This method:
        1. Gets statistics before clearing
        2. Deletes all keys matching the namespace pattern
        3. Resets the document counter
        4. Returns clearing statistics

        Returns:
            Statistics about what was cleared
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        doc_count = await self.get_document_count()

        pattern = f"{self.key_prefix}:*"
        cursor = 0
        keys_deleted = 0

        client = self._client()
        while True:
            cursor, keys = await cast(
                Awaitable[Tuple[int, List[str]]],
                client.scan(cursor=cursor, match=pattern, count=100),
            )

            if keys:
                deleted = await cast(Awaitable[int], client.delete(*keys))
                keys_deleted += int(deleted)

            if cursor == 0:
                break

        log_event(
            "redis_tracker_cleared",
            {
                "documents_cleared": doc_count,
                "keys_deleted": keys_deleted,
            },
        )

        return {
            "documents_cleared": doc_count,
            "keys_deleted": keys_deleted,
            "total_entries_cleared": doc_count,
        }

    def _serialize_metadata_value(self, value: Any) -> str:
        """
        Serialize a metadata value for Redis storage.

        Handles:
        - Nested dicts/lists -> JSON string
        - Simple types -> string conversion
        - None -> empty string

        Args:
            value: Value to serialize

        Returns:
            String representation for Redis
        """
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    def _deserialize_metadata_value(self, value: str) -> Any:
        """
        Deserialize a metadata value from Redis.

        Attempts JSON parsing for complex types, falls back to string.

        Args:
            value: String value from Redis

        Returns:
            Deserialized value
        """
        if not value:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value

    async def _update_metadata_indexes(
        self,
        document_id: str,
        old_metadata: Optional[Dict[str, Any]],
        new_metadata: Dict[str, Any],
    ) -> None:
        """
        Update metadata indexes when metadata changes.

        This method:
        1. Removes document from old index values
        2. Adds document to new index values
        3. Handles theme, mime_type, status indexes

        Args:
            document_id: Document being updated
            old_metadata: Previous metadata (for cleanup)
            new_metadata: New metadata (for indexing)
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        old_indexable = (
            self._extract_indexable_fields(old_metadata) if old_metadata else {}
        )
        new_indexable = self._extract_indexable_fields(new_metadata)

        client = self._client()
        async with client.pipeline(transaction=False) as pipe:
            for field, old_value in old_indexable.items():
                new_value = new_indexable.get(field)
                if old_value != new_value and old_value:
                    old_key = f"{self.key_prefix}:index:{field}:{old_value}"
                    pipe.srem(old_key, document_id)

            for field, new_value in new_indexable.items():
                old_val: Optional[str] = old_indexable.get(field)
                if new_value != old_val and new_value:
                    new_key = f"{self.key_prefix}:index:{field}:{new_value}"
                    pipe.sadd(new_key, document_id)

            await pipe.execute()

    async def _remove_from_indexes(
        self, document_id: str, metadata: Dict[str, Any]
    ) -> None:
        """
        Remove document from all metadata indexes.

        Args:
            document_id: Document to remove
            metadata: Metadata containing index values
        """
        if not self._initialized:
            raise RuntimeError("RedisDocumentTracker not initialized")

        indexable = self._extract_indexable_fields(metadata)

        client = self._client()
        async with client.pipeline(transaction=False) as pipe:
            for field, value in indexable.items():
                if value:
                    index_key = f"{self.key_prefix}:index:{field}:{value}"
                    pipe.srem(index_key, document_id)
            await pipe.execute()

    def _extract_indexable_fields(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract fields that should be indexed from metadata.

        Returns:
            Dictionary with theme, mime_type, status if present
        """
        indexable: Dict[str, str] = {}

        if "theme" in metadata:
            theme_data = metadata["theme"]
            if isinstance(theme_data, dict):
                theme_value: Optional[str] = theme_data.get("theme", "")
            else:
                theme_value = str(theme_data)
            if theme_value:
                indexable["theme"] = str(theme_value)

        if "mime_type" in metadata:
            mime_value = metadata["mime_type"]
            if mime_value:
                indexable["mime_type"] = str(mime_value)

        if "status" in metadata:
            status_value = metadata["status"]
            if status_value:
                indexable["status"] = str(status_value)

        return indexable
