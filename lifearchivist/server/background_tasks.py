"""
Background task management for integrated enrichment processing.
"""

import asyncio
import logging
from typing import Optional

from lifearchivist.utils.logging import log_event
from lifearchivist.workers.enrichment_worker import EnrichmentWorker


class BackgroundTaskManager:
    """Manages background tasks within the main server process."""

    def __init__(self, llamaindex_service=None, vault=None):
        self.enrichment_worker: Optional[EnrichmentWorker] = None
        self.worker_task: Optional[asyncio.Task] = None
        self.enabled = False
        self.llamaindex_service = llamaindex_service
        self.vault = vault

    async def start(self):
        """Start background tasks."""
        try:
            self.enrichment_worker = EnrichmentWorker(
                llamaindex_service=self.llamaindex_service, vault=self.vault
            )
            await self.enrichment_worker.initialize()

            self.worker_task = asyncio.create_task(self._run_worker_with_restart())

            self.enabled = True

            log_event(
                "background_tasks_started",
                {
                    "enrichment_worker": True,
                },
            )

        except Exception as e:
            log_event(
                "background_tasks_start_failed",
                {
                    "error": str(e),
                },
                level=logging.WARNING,
            )
            self.enabled = False

    async def _run_worker_with_restart(self):
        """Run worker with automatic restart on failure."""
        restart_count = 0
        max_restarts = 5

        while restart_count < max_restarts:
            try:
                if self.enrichment_worker:
                    await self.enrichment_worker.run()
                break

            except Exception as e:
                restart_count += 1
                log_event(
                    "enrichment_worker_restart",
                    {
                        "restart_count": restart_count,
                        "max_restarts": max_restarts,
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )

                if restart_count < max_restarts:
                    await asyncio.sleep(5 * restart_count)

                    if self.enrichment_worker:
                        await self.enrichment_worker.initialize()
                else:
                    log_event(
                        "enrichment_worker_max_restarts",
                        {
                            "error": str(e),
                        },
                        level=logging.ERROR,
                    )
                    self.enabled = False

    async def stop(self):
        """Stop background tasks gracefully."""
        if self.worker_task and not self.worker_task.done():
            if self.enrichment_worker:
                self.enrichment_worker.shutdown_event.set()

            try:
                await asyncio.wait_for(self.worker_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.worker_task.cancel()

        self.enabled = False

        log_event("background_tasks_stopped", {})

    async def get_status(self):
        """Get status of background tasks."""
        status = {
            "enabled": self.enabled,
            "enrichment_worker": None,
        }

        if self.enrichment_worker and self.enabled:
            status["enrichment_worker"] = await self.enrichment_worker.get_status()

        return status
