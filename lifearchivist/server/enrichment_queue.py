"""
Background enrichment queue for asynchronous document processing.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import redis.asyncio as redis

from lifearchivist.utils.logging import log_event, track


class EnrichmentQueue:
    """Manages background enrichment tasks for documents."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.queue_key = "lifearchivist:enrichment:queue"
        self.processing_key = "lifearchivist:enrichment:processing"
        self.completed_key = "lifearchivist:enrichment:completed"
        self.failed_key = "lifearchivist:enrichment:failed"

    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.redis_client.ping()
            log_event(
                "enrichment_queue_initialized",
                {
                    "redis_url": self.redis_url,
                },
            )
        except Exception as e:
            log_event(
                "enrichment_queue_init_failed",
                {
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            raise

    @track(
        operation="enqueue_enrichment_task",
        include_args=["task_type", "document_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def enqueue_task(
        self, task_type: str, document_id: str, data: Dict[str, Any], priority: int = 0
    ) -> bool:
        """Add a task to the enrichment queue."""
        if not self.redis_client:
            log_event(
                "enrichment_queue_not_initialized",
                {
                    "task_type": task_type,
                    "document_id": document_id,
                },
                level=logging.WARNING,
            )
            return False

        task = {
            "type": task_type,
            "document_id": document_id,
            "data": data,
            "priority": priority,
            "enqueued_at": datetime.now().isoformat(),
            "retry_count": 0,
            "max_retries": 3,
        }

        try:
            await self.redis_client.lpush(self.queue_key, json.dumps(task))

            log_event(
                "enrichment_task_enqueued",
                {
                    "task_type": task_type,
                    "document_id": document_id,
                    "queue_length": await self.redis_client.llen(self.queue_key),
                },
            )
            return True

        except Exception as e:
            log_event(
                "enrichment_enqueue_failed",
                {
                    "task_type": task_type,
                    "document_id": document_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return False

    @track(
        operation="dequeue_enrichment_task",
        track_performance=True,
        frequency="high_frequency",
    )
    async def get_next_task(self, timeout: int = 1) -> Optional[Dict[str, Any]]:
        """Get the next task from the queue."""
        if not self.redis_client:
            return None

        try:
            task_json = await self.redis_client.brpoplpush(
                self.queue_key, self.processing_key, timeout
            )

            if task_json:
                task = json.loads(task_json)
                log_event(
                    "enrichment_task_dequeued",
                    {
                        "task_type": task.get("type"),
                        "document_id": task.get("document_id"),
                        "retry_count": task.get("retry_count", 0),
                    },
                )
                return task
            return None

        except json.JSONDecodeError as e:
            log_event(
                "enrichment_task_decode_error",
                {
                    "error": str(e),
                    "task_json": task_json[:100] if task_json else None,
                },
                level=logging.ERROR,
            )
            return None
        except Exception as e:
            log_event(
                "enrichment_dequeue_failed",
                {
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return None

    @track(
        operation="complete_enrichment_task",
        include_args=["document_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def mark_complete(self, task: Dict[str, Any]) -> bool:
        """Mark a task as completed."""
        if not self.redis_client:
            return False

        try:
            task_json = json.dumps(task)

            await self.redis_client.lrem(self.processing_key, 1, task_json)

            completion_record = {
                **task,
                "completed_at": datetime.now().isoformat(),
            }
            await self.redis_client.lpush(
                self.completed_key, json.dumps(completion_record)
            )

            await self.redis_client.ltrim(self.completed_key, 0, 999)

            log_event(
                "enrichment_task_completed",
                {
                    "task_type": task.get("type"),
                    "document_id": task.get("document_id"),
                    "processing_time_seconds": self._calculate_processing_time(task),
                },
            )
            return True

        except Exception as e:
            log_event(
                "enrichment_complete_failed",
                {
                    "document_id": task.get("document_id"),
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return False

    @track(
        operation="requeue_enrichment_task",
        include_args=["document_id"],
        track_performance=True,
        frequency="low_frequency",
    )
    async def requeue_with_retry(self, task: Dict[str, Any]) -> bool:
        """Requeue a task with incremented retry count."""
        if not self.redis_client:
            return False

        try:
            task_json = json.dumps(task)
            await self.redis_client.lrem(self.processing_key, 1, task_json)

            task["retry_count"] = task.get("retry_count", 0) + 1
            task["last_retry_at"] = datetime.now().isoformat()

            if task["retry_count"] <= task.get("max_retries", 3):
                await self.redis_client.lpush(self.queue_key, json.dumps(task))

                log_event(
                    "enrichment_task_requeued",
                    {
                        "task_type": task.get("type"),
                        "document_id": task.get("document_id"),
                        "retry_count": task["retry_count"],
                        "max_retries": task.get("max_retries", 3),
                    },
                )
                return True
            else:
                await self._mark_failed(task, "Max retries exceeded")
                return False

        except Exception as e:
            log_event(
                "enrichment_requeue_failed",
                {
                    "document_id": task.get("document_id"),
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return False

    async def _mark_failed(self, task: Dict[str, Any], reason: str):
        """Mark a task as failed."""
        if not self.redis_client:
            return

        failure_record = {
            **task,
            "failed_at": datetime.now().isoformat(),
            "failure_reason": reason,
        }

        await self.redis_client.lpush(self.failed_key, json.dumps(failure_record))

        await self.redis_client.ltrim(self.failed_key, 0, 999)

        log_event(
            "enrichment_task_failed",
            {
                "task_type": task.get("type"),
                "document_id": task.get("document_id"),
                "reason": reason,
                "retry_count": task.get("retry_count", 0),
            },
            level=logging.WARNING,
        )

    def _calculate_processing_time(self, task: Dict[str, Any]) -> float:
        """Calculate processing time in seconds."""
        try:
            enqueued_at = datetime.fromisoformat(task.get("enqueued_at", ""))
            completed_at = datetime.now()
            return (completed_at - enqueued_at).total_seconds()
        except (ValueError, TypeError, AttributeError):
            # ValueError: Invalid date format
            # TypeError: task.get() returned None
            # AttributeError: Missing expected attributes
            return 0.0

    @track(
        operation="get_queue_stats",
        track_performance=True,
        frequency="low_frequency",
    )
    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        if not self.redis_client:
            return {
                "status": "not_initialized",
                "queue_length": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
            }

        try:
            stats = {
                "status": "operational",
                "queue_length": await self.redis_client.llen(self.queue_key),
                "processing": await self.redis_client.llen(self.processing_key),
                "completed": await self.redis_client.llen(self.completed_key),
                "failed": await self.redis_client.llen(self.failed_key),
            }

            log_event("enrichment_queue_stats", stats)

            return stats

        except Exception as e:
            log_event(
                "enrichment_stats_failed",
                {
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            return {
                "status": "error",
                "error": str(e),
            }

    async def cleanup(self):
        """Clean up Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            log_event("enrichment_queue_closed", {})
