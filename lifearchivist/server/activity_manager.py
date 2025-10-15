"""
Activity event management system for tracking system events.

This module provides a centralized, extensible system for tracking and
broadcasting activity events across the application. Events are stored
in Redis for persistence and broadcast via WebSocket for real-time updates.

Supported event types:
- Folder watch events (file detected, ingested, failed, duplicate)
- Manual upload events
- Document deletion events
- Vault reconciliation events
- Q&A query events (future)
- Search events (future)
- Enrichment events (future)
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis

from lifearchivist.utils.logging import log_event, track


class ActivityManager:
    """
    Manages system activity events with Redis persistence and WebSocket broadcasting.

    Architecture:
    ------------
    - Events stored in Redis list (FIFO queue with max 50 events)
    - Real-time broadcasting via WebSocket to all connected clients
    - Extensible event type system for future features
    - Atomic operations for thread safety

    Data Structure:
    --------------
    Redis List: "lifearchivist:activity:events"
    - Stores last 50 events as JSON strings
    - LPUSH for new events (newest first)
    - LTRIM to maintain max size
    - LRANGE for retrieval

    Event Format:
    ------------
    {
        "id": "timestamp_eventtype",
        "type": "event_type",
        "data": {...},
        "timestamp": "ISO8601 datetime"
    }
    """

    # Maximum number of events to store
    MAX_EVENTS = 200

    # Redis key for events list
    EVENTS_KEY = "lifearchivist:activity:events"

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize activity manager.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.session_manager = None  # Set by ApplicationServer
        self._initialized = False

    @track(
        operation="activity_manager_initialize",
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

            # Test connection
            await self.redis_client.ping()

            self._initialized = True

            # Get current event count
            event_count = await self.redis_client.llen(self.EVENTS_KEY)

            log_event(
                "activity_manager_initialized",
                {
                    "redis_url": self.redis_url,
                    "existing_events": event_count,
                    "max_events": self.MAX_EVENTS,
                },
            )

        except Exception as e:
            log_event(
                "activity_manager_init_failed",
                {"redis_url": self.redis_url, "error": str(e)},
                level=logging.ERROR,
            )
            raise ConnectionError(f"Failed to connect to Redis: {str(e)}") from e

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self.redis_client:
            await self.redis_client.aclose()
            self._initialized = False

            log_event("activity_manager_closed", {"redis_url": self.redis_url})

    @track(
        operation="activity_add_event",
        include_args=["event_type"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def add_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Add an activity event and broadcast to WebSocket clients.

        This method:
        1. Creates event with unique ID and timestamp
        2. Stores in Redis (LPUSH + LTRIM for FIFO)
        3. Broadcasts to all WebSocket clients
        4. Logs event creation

        Args:
            event_type: Type of event (e.g., "folder_watch_file_ingested")
            data: Event-specific data dictionary

        Raises:
            RuntimeError: If manager not initialized
        """
        if not self._initialized:
            raise RuntimeError("ActivityManager not initialized")

        # Create event with unique ID and timestamp
        timestamp = datetime.utcnow()
        event = {
            "id": f"{timestamp.timestamp()}_{event_type}",
            "type": event_type,
            "data": data,
            "timestamp": timestamp.isoformat() + "Z",
        }

        try:
            # Store in Redis using pipeline for atomicity
            async with self.redis_client.pipeline(transaction=True) as pipe:
                # Add to front of list (newest first)
                pipe.lpush(self.EVENTS_KEY, json.dumps(event))
                # Trim to max size (keep only last MAX_EVENTS)
                pipe.ltrim(self.EVENTS_KEY, 0, self.MAX_EVENTS - 1)
                await pipe.execute()

            # Broadcast to WebSocket clients
            if self.session_manager:
                await self.session_manager.broadcast(
                    {"type": "activity_event", "event": event}
                )

            log_event(
                "activity_event_added",
                {
                    "event_type": event_type,
                    "event_id": event["id"],
                    "has_websocket": self.session_manager is not None,
                },
                level=logging.DEBUG,
            )

        except Exception as e:
            log_event(
                "activity_event_add_failed",
                {
                    "event_type": event_type,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            # Don't raise - activity events are non-critical

    @track(
        operation="activity_get_recent_events",
        include_args=["limit"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent activity events from Redis.

        Args:
            limit: Maximum number of events to return (default: 50)

        Returns:
            List of event dictionaries, newest first

        Raises:
            RuntimeError: If manager not initialized
        """
        if not self._initialized:
            raise RuntimeError("ActivityManager not initialized")

        try:
            # Get events from Redis (0 to limit-1, newest first)
            event_strings = await self.redis_client.lrange(
                self.EVENTS_KEY, 0, limit - 1
            )

            # Parse JSON strings to dictionaries
            events = []
            for event_str in event_strings:
                try:
                    event = json.loads(event_str)
                    events.append(event)
                except json.JSONDecodeError as e:
                    log_event(
                        "activity_event_parse_failed",
                        {"error": str(e), "event_str": event_str[:100]},
                        level=logging.WARNING,
                    )
                    continue

            log_event(
                "activity_events_retrieved",
                {
                    "requested": limit,
                    "returned": len(events),
                },
                level=logging.DEBUG,
            )

            return events

        except Exception as e:
            log_event(
                "activity_get_events_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return []  # Return empty list on error

    @track(
        operation="activity_clear_all",
        track_performance=True,
        frequency="low_frequency",
    )
    async def clear_all(self) -> int:
        """
        Clear all activity events from Redis.

        Returns:
            Number of events cleared

        Raises:
            RuntimeError: If manager not initialized
        """
        if not self._initialized:
            raise RuntimeError("ActivityManager not initialized")

        try:
            # Get count before clearing
            count = await self.redis_client.llen(self.EVENTS_KEY)

            # Delete the list
            await self.redis_client.delete(self.EVENTS_KEY)

            log_event(
                "activity_events_cleared",
                {"events_cleared": count},
            )

            return count

        except Exception as e:
            log_event(
                "activity_clear_failed",
                {"error": str(e), "error_type": type(e).__name__},
                level=logging.ERROR,
            )
            return 0

    async def get_event_count(self) -> int:
        """
        Get total count of stored events.

        Returns:
            Number of events in Redis

        Raises:
            RuntimeError: If manager not initialized
        """
        if not self._initialized:
            raise RuntimeError("ActivityManager not initialized")

        try:
            count = await self.redis_client.llen(self.EVENTS_KEY)
            return count
        except Exception as e:
            log_event(
                "activity_count_failed",
                {"error": str(e)},
                level=logging.WARNING,
            )
            return 0

    # Convenience methods for common event types

    async def add_folder_watch_event(
        self, event_subtype: str, file_name: str, **kwargs
    ) -> None:
        """
        Add a folder watch event.

        Args:
            event_subtype: Subtype (detected, ingested, failed, duplicate_skipped)
            file_name: Name of the file
            **kwargs: Additional event data
        """
        event_type = f"folder_watch_{event_subtype}"
        data = {"file_name": file_name, **kwargs}
        await self.add_event(event_type, data)

    async def add_upload_event(
        self, file_count: int, source: str = "manual", **kwargs
    ) -> None:
        """
        Add a file upload event.

        Args:
            file_count: Number of files uploaded
            source: Upload source (manual, folder_watch, etc.)
            **kwargs: Additional event data
        """
        data = {"file_count": file_count, "source": source, **kwargs}
        await self.add_event("files_uploaded", data)

    async def add_document_deleted_event(
        self, document_id: str, file_name: str, **kwargs
    ) -> None:
        """
        Add a document deletion event.

        Args:
            document_id: ID of deleted document
            file_name: Name of the file
            **kwargs: Additional event data
        """
        data = {"document_id": document_id, "file_name": file_name, **kwargs}
        await self.add_event("document_deleted", data)

    async def add_qa_query_event(
        self, question: str, answer_length: int, sources_count: int, **kwargs
    ) -> None:
        """
        Add a Q&A query event.

        Args:
            question: The question asked
            answer_length: Length of answer in characters
            sources_count: Number of source documents used
            **kwargs: Additional event data
        """
        data = {
            "question": question[:100],  # Truncate for privacy/storage
            "answer_length": answer_length,
            "sources_count": sources_count,
            **kwargs,
        }
        await self.add_event("qa_query", data)

    async def add_search_event(
        self, query: str, mode: str, results_count: int, **kwargs
    ) -> None:
        """
        Add a search event.

        Args:
            query: Search query
            mode: Search mode (semantic, keyword, hybrid)
            results_count: Number of results returned
            **kwargs: Additional event data
        """
        data = {
            "query": query[:100],  # Truncate for storage
            "mode": mode,
            "results_count": results_count,
            **kwargs,
        }
        await self.add_event("search_performed", data)

    async def add_reconciliation_event(
        self, checked: int, cleaned: int, errors: int, **kwargs
    ) -> None:
        """
        Add a vault reconciliation event.

        Args:
            checked: Number of documents checked
            cleaned: Number of orphaned entries cleaned
            errors: Number of errors encountered
            **kwargs: Additional event data
        """
        data = {"checked": checked, "cleaned": cleaned, "errors": errors, **kwargs}
        await self.add_event("vault_reconciliation", data)
