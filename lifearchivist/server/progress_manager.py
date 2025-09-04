"""
Progress tracking system for upload and processing operations.
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)


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


@dataclass
class ProgressUpdate:
    """Represents a progress update for a specific file upload."""

    file_id: str
    stage: ProcessingStage
    progress: float  # 0.0 to 100.0
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


class ProgressManager:
    """Manages progress tracking for upload operations using Redis."""

    def __init__(self, redis_url: str = "redis://localhost:6379", session_manager=None):
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.session_manager = session_manager
        self.progress_ttl = 3600  # 1 hour TTL for progress records
        self.key_prefix = "lifearchivist"

        # Test Redis connection
        try:
            self.redis_client.ping()
            logger.info("Redis connection established for progress tracking")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _get_progress_key(self, file_id: str) -> str:
        """Generate Redis key for file progress."""
        return f"progress:{file_id}"

    def _get_session_key(self, file_id: str) -> str:
        """Generate Redis key for file-to-session mapping."""
        return f"session:{file_id}"

    async def start_progress(
        self, file_id: str, session_id: Optional[str] = None
    ) -> None:
        """Initialize progress tracking for a file upload."""
        try:
            # Store session mapping if provided
            if session_id:
                self.redis_client.setex(
                    self._get_session_key(file_id), self.progress_ttl, session_id
                )

            # Initialize progress with upload stage
            initial_update = ProgressUpdate(
                file_id=file_id,
                stage=ProcessingStage.UPLOAD,
                progress=0.0,
                message=ProcessingStage.UPLOAD.label,
                timestamp=time.time(),
            )

            await self._store_progress(initial_update)
            await self._broadcast_progress(initial_update)

            logger.info(f"Started progress tracking for file {file_id}")

        except Exception as e:
            logger.error(f"Failed to start progress tracking for {file_id}: {e}")

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
            # Calculate cumulative progress based on stage weights
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

            logger.debug(
                f"Updated progress for {file_id}: {stage.stage_id} - {cumulative_progress:.1f}%"
            )

        except Exception as e:
            logger.error(f"Failed to update progress for {file_id}: {e}")

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

            logger.info(f"Completed progress tracking for file {file_id}")

        except Exception as e:
            logger.error(f"Failed to complete progress for {file_id}: {e}")

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

            logger.warning(f"Error in progress tracking for {file_id}: {error_message}")

        except Exception as e:
            logger.error(f"Failed to record error progress for {file_id}: {e}")

    async def get_progress(self, file_id: str) -> Optional[ProgressUpdate]:
        """Get current progress for a file."""
        try:
            progress_data = self.redis_client.get(self._get_progress_key(file_id))
            if not progress_data:
                return None

            data = json.loads(progress_data)
            # Convert stage back to enum by finding matching stage_id
            stage_id = data["stage"]
            stage = next(s for s in ProcessingStage if s.stage_id == stage_id)
            data["stage"] = stage

            return ProgressUpdate(**data)

        except Exception as e:
            logger.error(f"Failed to get progress for {file_id}: {e}")
            return None

    async def cleanup_progress(self, file_id: str) -> None:
        """Clean up progress data for a file."""
        try:
            self.redis_client.delete(
                self._get_progress_key(file_id), self._get_session_key(file_id)
            )
            logger.debug(f"Cleaned up progress data for {file_id}")

        except Exception as e:
            logger.error(f"Failed to cleanup progress for {file_id}: {e}")

    async def clear_all_progress(self) -> Dict[str, Any]:
        """Clear all progress tracking data from Redis."""
        logger.info("Clearing all progress tracking data from Redis")

        cleared_metrics = {
            "progress_keys_deleted": 0,
            "session_keys_deleted": 0,
            "total_keys_deleted": 0,
            "errors": [],
        }

        try:
            # Get all progress and session keys
            progress_pattern = f"{self.key_prefix}:progress:*"
            session_pattern = f"{self.key_prefix}:session:*"

            progress_keys = self.redis_client.keys(progress_pattern)
            session_keys = self.redis_client.keys(session_pattern)

            # Delete progress keys
            if progress_keys:
                deleted_progress = self.redis_client.delete(*progress_keys)
                cleared_metrics["progress_keys_deleted"] = deleted_progress
                logger.info(f"Deleted {deleted_progress} progress keys")

            # Delete session keys
            if session_keys:
                deleted_sessions = self.redis_client.delete(*session_keys)
                cleared_metrics["session_keys_deleted"] = deleted_sessions
                logger.info(f"Deleted {deleted_sessions} session keys")

            progress_deleted = cleared_metrics.get("progress_keys_deleted", 0)
            session_deleted = cleared_metrics.get("session_keys_deleted", 0)
            progress_count = (
                progress_deleted if isinstance(progress_deleted, int) else 0
            )
            session_count = session_deleted if isinstance(session_deleted, int) else 0
            total_deleted = progress_count + session_count
            cleared_metrics["total_keys_deleted"] = total_deleted

            logger.info(
                f"Progress data clearing completed: {total_deleted} total keys deleted"
            )
            return cleared_metrics

        except Exception as e:
            error_msg = f"Failed to clear progress data: {e}"
            logger.error(error_msg)
            if isinstance(cleared_metrics["errors"], list):
                cleared_metrics["errors"].append(error_msg)
            return cleared_metrics

    def _calculate_cumulative_progress(
        self, current_stage: ProcessingStage, stage_progress: float
    ) -> float:
        """Calculate cumulative progress across all stages."""
        stages = list(ProcessingStage)
        total_weight = sum(stage.weight for stage in stages[:-1])  # Exclude COMPLETE

        # Calculate weight of completed stages
        completed_weight = 0
        for stage in stages:
            if stage == current_stage:
                break
            completed_weight += stage.weight

        # Add progress within current stage
        current_stage_contribution = (stage_progress / 100.0) * current_stage.weight

        # Calculate final percentage
        total_progress = (
            (completed_weight + current_stage_contribution) / total_weight * 100
        )

        return min(100.0, max(0.0, total_progress))

    async def _store_progress(self, update: ProgressUpdate) -> None:
        """Store progress update in Redis."""
        key = self._get_progress_key(update.file_id)
        data = json.dumps(update.to_dict())
        self.redis_client.setex(key, self.progress_ttl, data)

    async def _broadcast_progress(self, update: ProgressUpdate) -> None:
        """Broadcast progress update via WebSocket."""
        if not self.session_manager:
            return

        try:
            # Get session ID for this file
            session_id = self.redis_client.get(self._get_session_key(update.file_id))

            if session_id:
                message = {"type": "upload_progress", "data": update.to_dict()}

                await self.session_manager.send_to_session(session_id, message)
                logger.debug(
                    f"Broadcasted progress update for {update.file_id} to session {session_id}"
                )

        except Exception as e:
            logger.error(f"Failed to broadcast progress update: {e}")


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
            # Error occurred
            await self.progress_manager.error_progress(
                self.file_id, str(exc_val), self.stage
            )
        else:
            # Success
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
