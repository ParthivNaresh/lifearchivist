"""
Progress tracking system for upload and processing operations.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol

import redis.asyncio as redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

from ..utils.logx import log_event


class SessionManagerProtocol(Protocol):
    """Protocol for session manager dependency."""

    async def send_to_session(
        self, session_id: str, message: Dict[str, Any]
    ) -> None: ...


class ProcessingStage(Enum):
    """Enumeration of processing stages with their display information."""

    UPLOAD = ("upload", "Uploading file...", 10)
    EXTRACT = ("extract", "Extracting content...", 25)
    EMBED = ("embed", "Generating embeddings...", 30)
    TAG = ("tag", "AI tagging and categorization...", 20)
    INDEX = ("index", "Building search index...", 10)
    COMPLETE = ("complete", "Processing complete!", 5)

    def __init__(self, stage_id: str, label: str, weight: int):
        self.stage_id = stage_id
        self.label = label
        self.weight = weight

    @classmethod
    def from_stage_id(cls, stage_id: str) -> Optional["ProcessingStage"]:
        """Safely get stage from stage_id."""
        for stage in cls:
            if stage.stage_id == stage_id:
                return stage
        return None


@dataclass
class ProgressUpdate:
    """Represents a progress update for a specific file upload."""

    file_id: str
    stage: ProcessingStage
    progress: float
    message: str
    timestamp: float
    eta_seconds: Optional[int] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data["stage"] = self.stage.stage_id
        return data


class ProgressManagerError(Exception):
    """Base exception for ProgressManager errors."""

    pass


class ProgressManager:
    """Manages progress tracking for upload operations using async Redis."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        session_manager: Optional[SessionManagerProtocol] = None,
        max_connections: int = 50,
        socket_timeout: float = 5.0,
        socket_connect_timeout: float = 5.0,
    ):
        self.redis_url = redis_url
        self.session_manager = session_manager
        self.progress_ttl = 3600
        self.key_prefix = "lifearchivist"
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.socket_connect_timeout = socket_connect_timeout
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize async Redis connection with connection pooling."""
        if self._initialized:
            return

        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                health_check_interval=30,
            )

            await self.redis_client.ping()
            self._initialized = True

            log_event(
                "progress_manager_redis_connected",
                {
                    "redis_url": self.redis_url,
                    "max_connections": self.max_connections,
                },
            )

        except (ConnectionError, TimeoutError) as e:
            log_event(
                "progress_manager_redis_connection_failed",
                {"error": str(e), "redis_url": self.redis_url},
                level=logging.ERROR,
            )
            raise ProgressManagerError(f"Failed to connect to Redis: {e}") from e

    async def close(self) -> None:
        """Close Redis connection and cleanup resources."""
        if self.redis_client:
            try:
                await self.redis_client.aclose()
                log_event("progress_manager_redis_closed")
            except Exception as e:
                log_event(
                    "progress_manager_close_error",
                    {"error": str(e)},
                    level=logging.WARNING,
                )
            finally:
                self.redis_client = None
                self._initialized = False

    def _ensure_initialized(self) -> redis.Redis:
        """Ensure Redis client is initialized."""
        if not self._initialized or not self.redis_client:
            raise ProgressManagerError(
                "ProgressManager not initialized. Call initialize() first."
            )
        return self.redis_client

    def _get_progress_key(self, file_id: str) -> str:
        """Generate Redis key for file progress."""
        return f"{self.key_prefix}:progress:{file_id}"

    def _get_session_key(self, file_id: str) -> str:
        """Generate Redis key for file-to-session mapping."""
        return f"{self.key_prefix}:session:{file_id}"

    async def start_progress(
        self, file_id: str, session_id: Optional[str] = None
    ) -> None:
        """Initialize progress tracking for a file upload."""
        client = self._ensure_initialized()

        try:
            if session_id:
                await client.setex(
                    self._get_session_key(file_id), self.progress_ttl, session_id
                )

            initial_update = ProgressUpdate(
                file_id=file_id,
                stage=ProcessingStage.UPLOAD,
                progress=0.0,
                message=ProcessingStage.UPLOAD.label,
                timestamp=time.time(),
            )

            await self._store_progress(initial_update)
            await self._broadcast_progress(initial_update)

        except RedisError as e:
            log_event(
                "progress_start_redis_error",
                {"file_id": file_id, "error": str(e)},
                level=logging.ERROR,
            )
            raise ProgressManagerError(f"Failed to start progress: {e}") from e

    async def update_progress(
        self,
        file_id: str,
        stage: ProcessingStage,
        progress: float,
        message: Optional[str] = None,
        eta_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update progress for a file upload."""
        try:
            cumulative_progress = self._calculate_cumulative_progress(stage, progress)

            update = ProgressUpdate(
                file_id=file_id,
                stage=stage,
                progress=cumulative_progress,
                message=message or stage.label,
                timestamp=time.time(),
                eta_seconds=eta_seconds,
                metadata=metadata,
            )

            await self._store_progress(update)
            await self._broadcast_progress(update)

        except RedisError as e:
            log_event(
                "progress_update_redis_error",
                {"file_id": file_id, "stage": stage.stage_id, "error": str(e)},
                level=logging.ERROR,
            )
            raise ProgressManagerError(f"Failed to update progress: {e}") from e

    async def complete_progress(
        self, file_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mark file processing as complete."""
        try:
            completion_update = ProgressUpdate(
                file_id=file_id,
                stage=ProcessingStage.COMPLETE,
                progress=100.0,
                message="File processed successfully!",
                timestamp=time.time(),
                metadata=metadata,
            )

            await self._store_progress(completion_update)
            await self._broadcast_progress(completion_update)

        except RedisError as e:
            log_event(
                "progress_complete_redis_error",
                {"file_id": file_id, "error": str(e)},
                level=logging.ERROR,
            )
            raise ProgressManagerError(f"Failed to complete progress: {e}") from e

    async def error_progress(
        self, file_id: str, error_message: str, stage: ProcessingStage
    ) -> None:
        """Mark file processing as failed."""
        try:
            error_update = ProgressUpdate(
                file_id=file_id,
                stage=stage,
                progress=0.0,
                message=f"Error: {error_message}",
                timestamp=time.time(),
                error=error_message,
            )

            await self._store_progress(error_update)
            await self._broadcast_progress(error_update)

        except RedisError as e:
            log_event(
                "progress_error_redis_error",
                {"file_id": file_id, "error": str(e)},
                level=logging.ERROR,
            )

    async def get_progress(self, file_id: str) -> Optional[ProgressUpdate]:
        """Get current progress for a file."""
        client = self._ensure_initialized()

        try:
            progress_data = await client.get(self._get_progress_key(file_id))
            if not progress_data:
                return None

            data = json.loads(progress_data)
            stage_id = data.get("stage")

            if not stage_id:
                log_event(
                    "progress_data_missing_stage",
                    {"file_id": file_id},
                    level=logging.WARNING,
                )
                return None

            stage = ProcessingStage.from_stage_id(stage_id)
            if not stage:
                log_event(
                    "progress_data_invalid_stage",
                    {"file_id": file_id, "stage_id": stage_id},
                    level=logging.WARNING,
                )
                return None

            data["stage"] = stage
            return ProgressUpdate(**data)

        except json.JSONDecodeError as e:
            log_event(
                "progress_data_json_decode_error",
                {"file_id": file_id, "error": str(e)},
                level=logging.ERROR,
            )
            return None
        except (RedisError, TypeError, KeyError) as e:
            log_event(
                "progress_get_error",
                {"file_id": file_id, "error": str(e)},
                level=logging.ERROR,
            )
            return None

    async def cleanup_progress(self, file_id: str) -> None:
        """Clean up progress data for a file."""
        client = self._ensure_initialized()

        try:
            await client.delete(
                self._get_progress_key(file_id), self._get_session_key(file_id)
            )
        except RedisError as e:
            log_event(
                "progress_cleanup_redis_error",
                {"file_id": file_id, "error": str(e)},
                level=logging.WARNING,
            )

    async def clear_all_progress(self) -> Dict[str, Any]:
        """Clear all progress tracking data from Redis using batched deletion."""
        client = self._ensure_initialized()

        cleared_metrics = {
            "progress_keys_deleted": 0,
            "session_keys_deleted": 0,
            "total_keys_deleted": 0,
            "errors": [],
        }

        try:
            progress_pattern = f"{self.key_prefix}:progress:*"
            session_pattern = f"{self.key_prefix}:session:*"

            progress_deleted = await self._delete_keys_by_pattern(
                client, progress_pattern
            )
            cleared_metrics["progress_keys_deleted"] = progress_deleted

            session_deleted = await self._delete_keys_by_pattern(
                client, session_pattern
            )
            cleared_metrics["session_keys_deleted"] = session_deleted

            cleared_metrics["total_keys_deleted"] = progress_deleted + session_deleted

            log_event(
                "progress_cleared_all",
                {
                    "progress_keys": progress_deleted,
                    "session_keys": session_deleted,
                    "total": cleared_metrics["total_keys_deleted"],
                },
            )

            return cleared_metrics

        except Exception as e:
            error_msg = f"Failed to clear progress data: {e}"
            log_event(
                "progress_clear_all_error",
                {"error": str(e)},
                level=logging.ERROR,
            )
            errors = cleared_metrics.get("errors")
            if isinstance(errors, list):
                errors.append(error_msg)
            return cleared_metrics

    async def _delete_keys_by_pattern(
        self, client: redis.Redis, pattern: str, batch_size: int = 100
    ) -> int:
        """Delete keys matching pattern in batches to avoid memory issues."""
        deleted_count = 0
        batch: List[str] = []

        try:
            async for key in client.scan_iter(match=pattern, count=batch_size):
                batch.append(key)

                if len(batch) >= batch_size:
                    deleted = await client.delete(*batch)
                    deleted_count += deleted
                    batch = []

            if batch:
                deleted = await client.delete(*batch)
                deleted_count += deleted

        except RedisError as e:
            log_event(
                "progress_delete_keys_error",
                {"pattern": pattern, "error": str(e)},
                level=logging.ERROR,
            )
            raise

        return deleted_count

    def _calculate_cumulative_progress(
        self, current_stage: ProcessingStage, stage_progress: float
    ) -> float:
        """Calculate cumulative progress across all stages."""
        stages = list(ProcessingStage)
        total_weight = sum(stage.weight for stage in stages[:-1])

        completed_weight = 0
        for stage in stages:
            if stage == current_stage:
                break
            completed_weight += stage.weight

        current_stage_contribution = (stage_progress / 100.0) * current_stage.weight

        total_progress = (
            (completed_weight + current_stage_contribution) / total_weight * 100
        )

        return min(100.0, max(0.0, total_progress))

    async def _store_progress(self, update: ProgressUpdate) -> None:
        """Store progress update in Redis."""
        client = self._ensure_initialized()

        key = self._get_progress_key(update.file_id)
        data = json.dumps(update.to_dict())
        await client.setex(key, self.progress_ttl, data)

    async def _broadcast_progress(self, update: ProgressUpdate) -> None:
        """Broadcast progress update via WebSocket."""
        if not self.session_manager:
            return

        try:
            client = self._ensure_initialized()
            session_id = await client.get(self._get_session_key(update.file_id))

            if session_id:
                message = {"type": "upload_progress", "data": update.to_dict()}
                await self.session_manager.send_to_session(session_id, message)

        except Exception as e:
            log_event(
                "progress_broadcast_error",
                {"file_id": update.file_id, "error": str(e)},
                level=logging.WARNING,
            )


class ProgressContext:
    """Context manager for tracking progress of an operation."""

    def __init__(
        self, progress_manager: ProgressManager, file_id: str, stage: ProcessingStage
    ):
        self.progress_manager = progress_manager
        self.file_id = file_id
        self.stage = stage
        self.start_time: Optional[float] = None

    async def __aenter__(self):
        self.start_time = time.time()
        await self.progress_manager.update_progress(
            self.file_id, self.stage, 0.0, f"Starting {self.stage.label.lower()}"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.progress_manager.error_progress(
                self.file_id, str(exc_val), self.stage
            )
        else:
            duration = time.time() - (self.start_time or 0.0)
            await self.progress_manager.update_progress(
                self.file_id,
                self.stage,
                100.0,
                f"Completed {self.stage.label.lower()} in {duration:.1f}s",
            )

    async def update(
        self,
        progress: float,
        message: Optional[str] = None,
        eta_seconds: Optional[int] = None,
    ):
        """Update progress within this stage."""
        await self.progress_manager.update_progress(
            self.file_id, self.stage, progress, message, eta_seconds
        )
