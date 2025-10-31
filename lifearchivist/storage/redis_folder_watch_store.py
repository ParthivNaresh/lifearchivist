"""
Redis-based persistence layer for folder watching configurations.

This implementation provides:
- Atomic operations with Redis transactions
- Fast O(1) lookups by folder ID
- Automatic indexing for path-based queries
- Concurrent-safe operations
- Efficient memory usage with Redis hashes and sets
- Persistence across server restarts
"""

import json
import logging
from datetime import datetime
from typing import Any, Awaitable, Dict, List, Optional, Set, cast
from uuid import uuid4

import redis.asyncio as redis

from lifearchivist.utils.logging import log_event, track

logger = logging.getLogger(__name__)


class RedisFolderWatchStore:
    """
    Production-grade Redis-based folder watch configuration store.

    Data Structure Design:
    ----------------------
    1. Folder Configuration (Redis Hash):
       Key: "lifearchivist:folder_watch:folders:{folder_id}"
       Fields:
         - id: UUID
         - path: Absolute folder path
         - enabled: "true" or "false"
         - created_at: ISO timestamp
         - last_activity: ISO timestamp
         - files_detected: Integer count
         - files_ingested: Integer count
         - files_skipped: Integer count (duplicates)
         - files_failed: Integer count
         - bytes_processed: Integer bytes
         - last_error: Error message (empty if none)
         - error_count: Consecutive error count

    2. Folder ID Index (Redis Set):
       Key: "lifearchivist:folder_watch:folder_ids"
       Value: Set of all folder_ids

    3. Path-to-ID Mapping (Redis Hash):
       Key: "lifearchivist:folder_watch:path_index"
       Fields: {path: folder_id}
       Purpose: Fast lookup to prevent duplicate paths

    4. Aggregate Statistics (Redis Hash):
       Key: "lifearchivist:folder_watch:stats"
       Fields:
         - total_folders: Count
         - total_pending: Count
         - total_processed: Count
         - last_updated: ISO timestamp

    Performance Characteristics:
    ---------------------------
    - Add folder: O(1) - constant time
    - Get folder: O(1) - direct hash lookup
    - List folders: O(n) where n = number of folders
    - Delete folder: O(1) - atomic transaction
    - Check path exists: O(1) - hash field lookup
    - Update stats: O(1) - atomic increment
    - Concurrent writes: Safe with Redis atomicity
    """

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize Redis folder watch store.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None

        # Key namespace following project conventions
        self.key_prefix = "lifearchivist:folder_watch"

        # Connection state
        self._initialized = False

    @track(
        operation="redis_folder_watch_store_initialize",
        track_performance=True,
        frequency="low_frequency",
    )
    async def initialize(self) -> None:
        """
        Initialize Redis connection and verify connectivity.

        Raises:
            ConnectionError: If Redis is unreachable
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

            folder_count = await self.get_folder_count()

            log_event(
                "redis_folder_watch_store_initialized",
                {
                    "redis_url": self.redis_url,
                    "folder_count": folder_count,
                },
            )

            logger.info(
                f"RedisFolderWatchStore initialized with {folder_count} folders"
            )

        except Exception as e:
            log_event(
                "redis_folder_watch_store_init_failed",
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
            raise RuntimeError("RedisFolderWatchStore not initialized")
        return self.redis_client

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self.redis_client:
            await self.redis_client.aclose()
            self._initialized = False

            log_event(
                "redis_folder_watch_store_closed",
                {"redis_url": self.redis_url},
            )

    @track(
        operation="redis_add_watched_folder",
        include_args=["path"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def add_folder(
        self,
        path: str,
        folder_id: Optional[str] = None,
        enabled: bool = True,
    ) -> str:
        """
        Add a new watched folder configuration.

        This method uses Redis transaction to atomically:
        1. Create folder configuration hash
        2. Add folder_id to index set
        3. Add path-to-id mapping
        4. Initialize statistics

        Args:
            path: Absolute path to folder
            folder_id: Optional UUID (generated if not provided)
            enabled: Whether folder watching is enabled

        Returns:
            folder_id of the created folder

        Raises:
            ValueError: If path already exists
            RuntimeError: If store not initialized
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        # Check if path already exists
        existing_id = await self.get_folder_id_by_path(path)
        if existing_id:
            raise ValueError(f"Folder path already being watched: {path}")

        # Generate folder_id if not provided
        if not folder_id:
            folder_id = str(uuid4())

        now = datetime.utcnow().isoformat()

        folder_key = f"{self.key_prefix}:folders:{folder_id}"
        ids_key = f"{self.key_prefix}:folder_ids"
        path_index_key = f"{self.key_prefix}:path_index"

        # Initial folder configuration
        folder_data = {
            "id": folder_id,
            "path": path,
            "enabled": str(enabled).lower(),
            "created_at": now,
            "last_activity": now,
            "files_detected": "0",
            "files_ingested": "0",
            "files_skipped": "0",
            "files_failed": "0",
            "bytes_processed": "0",
            "last_error": "",
            "error_count": "0",
        }

        client = self._client()
        async with client.pipeline(transaction=True) as pipe:
            # Store folder configuration
            pipe.hset(folder_key, mapping=folder_data)
            # Add to folder IDs index
            pipe.sadd(ids_key, folder_id)
            # Add path-to-id mapping
            pipe.hset(path_index_key, path, folder_id)
            await pipe.execute()

        log_event(
            "folder_watch_added",
            {
                "folder_id": folder_id,
                "path": path,
                "enabled": enabled,
            },
        )

        logger.info(f"Added watched folder: {path} (ID: {folder_id})")

        return folder_id

    @track(
        operation="redis_get_watched_folder",
        include_args=["folder_id"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_folder(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """
        Get folder configuration by ID.

        Args:
            folder_id: Folder UUID

        Returns:
            Folder configuration dict, or None if not found
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        folder_key = f"{self.key_prefix}:folders:{folder_id}"

        client = self._client()
        raw_data = await cast(Awaitable[Dict[str, str]], client.hgetall(folder_key))

        if not raw_data:
            return None

        # Deserialize data types
        return self._deserialize_folder_data(raw_data)

    @track(
        operation="redis_list_watched_folders",
        track_performance=True,
        frequency="medium_frequency",
    )
    async def list_folders(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all watched folders.

        Args:
            enabled_only: If True, only return enabled folders

        Returns:
            List of folder configuration dicts
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        ids_key = f"{self.key_prefix}:folder_ids"

        client = self._client()
        folder_ids = await cast(Awaitable[Set[str]], client.smembers(ids_key))

        if not folder_ids:
            return []

        # Fetch all folder configurations
        folders = []
        for folder_id in folder_ids:
            folder = await self.get_folder(folder_id)
            if folder:
                if enabled_only and not folder.get("enabled", False):
                    continue
                folders.append(folder)

        # Sort by created_at descending (newest first)
        folders.sort(key=lambda f: f.get("created_at", ""), reverse=True)

        return folders

    @track(
        operation="redis_update_watched_folder",
        include_args=["folder_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def update_folder(self, folder_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update folder configuration fields.

        Args:
            folder_id: Folder UUID
            updates: Dictionary of fields to update

        Returns:
            True if folder was updated, False if not found
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        folder_key = f"{self.key_prefix}:folders:{folder_id}"

        client = self._client()
        exists = await cast(Awaitable[int], client.exists(folder_key))
        if not exists:
            return False

        # Serialize updates
        serialized = {k: self._serialize_value(v) for k, v in updates.items()}

        if serialized:
            await cast(Awaitable[int], client.hset(folder_key, mapping=serialized))

        logger.debug(f"Updated folder {folder_id}: {list(updates.keys())}")

        return True

    @track(
        operation="redis_remove_watched_folder",
        include_args=["folder_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def remove_folder(self, folder_id: str) -> bool:
        """
        Remove a watched folder configuration atomically.

        This method uses Redis transaction to:
        1. Get folder path for path index cleanup
        2. Delete folder configuration hash
        3. Remove from folder IDs index
        4. Remove from path index

        Args:
            folder_id: Folder UUID to remove

        Returns:
            True if folder was removed, False if not found
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        # Get folder data for cleanup
        folder = await self.get_folder(folder_id)
        if not folder:
            return False

        folder_key = f"{self.key_prefix}:folders:{folder_id}"
        ids_key = f"{self.key_prefix}:folder_ids"
        path_index_key = f"{self.key_prefix}:path_index"

        client = self._client()
        async with client.pipeline(transaction=True) as pipe:
            # Delete folder configuration
            pipe.delete(folder_key)
            # Remove from folder IDs index
            pipe.srem(ids_key, folder_id)
            # Remove from path index
            pipe.hdel(path_index_key, folder["path"])
            await pipe.execute()

        log_event(
            "folder_watch_removed",
            {
                "folder_id": folder_id,
                "path": folder["path"],
            },
        )

        logger.info(f"Removed watched folder: {folder['path']} (ID: {folder_id})")

        return True

    @track(
        operation="redis_increment_folder_stat",
        include_args=["folder_id", "stat_name"],
        track_performance=True,
        frequency="high_frequency",
    )
    async def increment_stat(
        self, folder_id: str, stat_name: str, amount: int = 1
    ) -> int:
        """
        Atomically increment a folder statistic.

        Args:
            folder_id: Folder UUID
            stat_name: Stat field name (e.g., "files_ingested")
            amount: Amount to increment by

        Returns:
            New value after increment

        Raises:
            ValueError: If folder not found
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        folder_key = f"{self.key_prefix}:folders:{folder_id}"

        client = self._client()
        exists = await cast(Awaitable[int], client.exists(folder_key))
        if not exists:
            raise ValueError(f"Folder not found: {folder_id}")

        new_value = await cast(
            Awaitable[int], client.hincrby(folder_key, stat_name, amount)
        )

        # Update last_activity timestamp
        now = datetime.utcnow().isoformat()
        await cast(Awaitable[int], client.hset(folder_key, "last_activity", now))

        return new_value

    async def get_folder_id_by_path(self, path: str) -> Optional[str]:
        """
        Get folder ID by path (O(1) lookup).

        Args:
            path: Folder path

        Returns:
            folder_id if found, None otherwise
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        path_index_key = f"{self.key_prefix}:path_index"

        client = self._client()
        folder_id = await cast(
            Awaitable[Optional[str]], client.hget(path_index_key, path)
        )

        return folder_id

    async def folder_exists(self, folder_id: str) -> bool:
        """
        Check if a folder exists.

        Args:
            folder_id: Folder UUID

        Returns:
            True if folder exists
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        ids_key = f"{self.key_prefix}:folder_ids"

        client = self._client()
        exists = await cast(Awaitable[int], client.sismember(ids_key, folder_id))

        return bool(exists)

    async def get_folder_count(self) -> int:
        """
        Get total count of watched folders.

        Returns:
            Number of folders
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        ids_key = f"{self.key_prefix}:folder_ids"

        client = self._client()
        count = await cast(Awaitable[int], client.scard(ids_key))

        return count

    async def set_folder_error(self, folder_id: str, error_message: str) -> None:
        """
        Record an error for a folder and increment error count.

        Args:
            folder_id: Folder UUID
            error_message: Error description
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        folder_key = f"{self.key_prefix}:folders:{folder_id}"

        client = self._client()
        async with client.pipeline(transaction=True) as pipe:
            pipe.hset(folder_key, "last_error", error_message)
            pipe.hincrby(folder_key, "error_count", 1)
            pipe.hset(folder_key, "last_activity", datetime.utcnow().isoformat())
            await pipe.execute()

    async def clear_folder_error(self, folder_id: str) -> None:
        """
        Clear error state for a folder.

        Args:
            folder_id: Folder UUID
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        folder_key = f"{self.key_prefix}:folders:{folder_id}"

        client = self._client()
        async with client.pipeline(transaction=True) as pipe:
            pipe.hset(folder_key, "last_error", "")
            pipe.hset(folder_key, "error_count", "0")
            await pipe.execute()

    @track(
        operation="redis_clear_all_folders",
        track_performance=True,
        frequency="low_frequency",
    )
    async def clear_all(self) -> Dict[str, Any]:
        """
        Clear all watched folder configurations.

        Returns:
            Statistics about what was cleared
        """
        if not self._initialized:
            raise RuntimeError("RedisFolderWatchStore not initialized")

        folder_count = await self.get_folder_count()

        pattern = f"{self.key_prefix}:*"
        cursor = 0
        keys_deleted = 0

        client = self._client()
        while True:
            cursor, keys = await cast(
                Awaitable[tuple[int, List[str]]],
                client.scan(cursor=cursor, match=pattern, count=100),
            )

            if keys:
                deleted = await cast(Awaitable[int], client.delete(*keys))
                keys_deleted += int(deleted)

            if cursor == 0:
                break

        log_event(
            "folder_watch_store_cleared",
            {
                "folders_cleared": folder_count,
                "keys_deleted": keys_deleted,
            },
        )

        logger.info(f"Cleared all folder watch data: {folder_count} folders")

        return {
            "folders_cleared": folder_count,
            "keys_deleted": keys_deleted,
        }

    def _serialize_value(self, value: Any) -> str:
        """
        Serialize a value for Redis storage.

        Args:
            value: Value to serialize

        Returns:
            String representation
        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return str(value)

    def _deserialize_folder_data(self, raw_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Deserialize folder data from Redis.

        Args:
            raw_data: Raw string data from Redis

        Returns:
            Typed folder configuration
        """
        return {
            "id": raw_data.get("id", ""),
            "path": raw_data.get("path", ""),
            "enabled": raw_data.get("enabled", "false") == "true",
            "created_at": raw_data.get("created_at", ""),
            "last_activity": raw_data.get("last_activity", ""),
            "files_detected": int(raw_data.get("files_detected", "0")),
            "files_ingested": int(raw_data.get("files_ingested", "0")),
            "files_skipped": int(raw_data.get("files_skipped", "0")),
            "files_failed": int(raw_data.get("files_failed", "0")),
            "bytes_processed": int(raw_data.get("bytes_processed", "0")),
            "last_error": raw_data.get("last_error", ""),
            "error_count": int(raw_data.get("error_count", "0")),
        }
