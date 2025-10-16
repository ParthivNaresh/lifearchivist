"""
Background worker for processing document enrichment tasks.
"""

import asyncio
import logging
import signal
from datetime import datetime
from typing import Any, Dict, Optional

from lifearchivist.config import get_settings
from lifearchivist.server.enrichment_queue import EnrichmentQueue
from lifearchivist.storage.llamaindex_service import LlamaIndexService
from lifearchivist.storage.vault.vault import Vault
from lifearchivist.tools.date_extract.date_extraction_utils import (
    create_date_extraction_prompt,
    truncate_text_for_llm,
)
from lifearchivist.tools.ollama.ollama_tool import OllamaTool
from lifearchivist.utils.logging import log_event, track


class EnrichmentWorker:
    """Worker for processing background enrichment tasks."""

    def __init__(self, llamaindex_service=None, vault=None):
        self.settings = get_settings()
        self.queue = EnrichmentQueue(redis_url=self.settings.redis_url)
        self.vault = vault
        self.llamaindex_service = llamaindex_service
        self.ollama_tool: Optional[OllamaTool] = None
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.tasks_processed = 0
        self.tasks_failed = 0

    async def initialize(self):
        """Initialize worker components."""
        log_event("enrichment_worker_init_started", {})

        await self.queue.initialize()

        if not self.vault:
            vault_path = self.settings.vault_path
            if vault_path is None:
                raise RuntimeError("Vault path not configured in settings")
            self.vault = Vault(vault_path)
            await self.vault.initialize()

        if not self.llamaindex_service:
            self.llamaindex_service = LlamaIndexService(vault=self.vault)
            await self.llamaindex_service.ensure_initialized()

        self.ollama_tool = OllamaTool()

        self._setup_signal_handlers()

        log_event(
            "enrichment_worker_initialized",
            {
                "vault_path": str(self.settings.vault_path),
                "redis_url": self.settings.redis_url,
            },
        )

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""

        def signal_handler(signum, frame):
            log_event(
                "enrichment_worker_shutdown_signal",
                {
                    "signal": signum,
                },
            )
            self.shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    @track(
        operation="enrichment_worker_run",
        track_performance=True,
        frequency="low_frequency",
    )
    async def run(self):
        """Main worker loop."""
        self.running = True
        log_event("enrichment_worker_started", {})

        while self.running and not self.shutdown_event.is_set():
            try:
                task = await self.queue.get_next_task(timeout=1)

                if not task:
                    await asyncio.sleep(0.1)
                    continue

                await self._process_task(task)

            except asyncio.CancelledError:
                log_event(
                    "enrichment_worker_cancelled",
                    {
                        "tasks_processed": self.tasks_processed,
                        "tasks_failed": self.tasks_failed,
                    },
                )
                break
            except Exception as e:
                log_event(
                    "enrichment_worker_error",
                    {
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                    level=logging.ERROR,
                )
                await asyncio.sleep(1)

        await self._shutdown()

    @track(
        operation="process_enrichment_task",
        include_args=["task_type", "document_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _process_task(self, task: Dict[str, Any]):
        """Process a single enrichment task."""
        task_type = task.get("type")
        document_id = task.get("document_id")

        log_event(
            "enrichment_task_processing",
            {
                "task_type": task_type,
                "document_id": document_id,
                "retry_count": task.get("retry_count", 0),
            },
        )

        try:
            if task_type == "date_extraction":
                await self._process_date_extraction(task)
            elif task_type == "auto_tagging":
                await self._process_auto_tagging(task)
            else:
                log_event(
                    "enrichment_unknown_task_type",
                    {
                        "task_type": task_type,
                        "document_id": document_id,
                    },
                    level=logging.WARNING,
                )
                await self.queue.mark_complete(task)
                return

            await self.queue.mark_complete(task)
            self.tasks_processed += 1

        except asyncio.TimeoutError:
            log_event(
                "enrichment_task_timeout",
                {
                    "task_type": task_type,
                    "document_id": document_id,
                },
                level=logging.WARNING,
            )
            await self.queue.requeue_with_retry(task)
            self.tasks_failed += 1

        except Exception as e:
            log_event(
                "enrichment_task_error",
                {
                    "task_type": task_type,
                    "document_id": document_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            await self.queue.requeue_with_retry(task)
            self.tasks_failed += 1

    @track(
        operation="process_date_extraction",
        include_args=["document_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _process_date_extraction(self, task: Dict[str, Any]):
        """Process date extraction for a document."""
        document_id = task.get("document_id")
        data = task.get("data", {})
        text = data.get("text", "")

        if not text:
            log_event(
                "date_extraction_no_text",
                {
                    "document_id": document_id,
                },
                level=logging.WARNING,
            )
            return

        truncated_text = truncate_text_for_llm(
            text, max_chars=10000, document_id=document_id
        )
        prompt = create_date_extraction_prompt(truncated_text)

        log_event(
            "background_date_extraction_started",
            {
                "document_id": document_id,
                "text_length": len(text),
                "truncated_length": len(truncated_text),
            },
        )

        try:
            if not self.ollama_tool:
                raise RuntimeError("Ollama tool not initialized")
            response = await asyncio.wait_for(
                self.ollama_tool.generate(
                    prompt=prompt,
                    temperature=0.1,
                    max_tokens=1000,
                ),
                timeout=120.0,
            )

            extracted_date = response.strip() if response else ""

            has_valid_date = extracted_date and not extracted_date.lower().startswith(
                ("no date", "none", "not found", "unable")
            )

            metadata_updates = {
                "enrichment_status": (
                    "dates_extracted" if has_valid_date else "no_dates_found"
                ),
                "enriched_at": datetime.now().isoformat(),
            }

            if has_valid_date:
                metadata_updates["content_date"] = extracted_date

            success = await self.llamaindex_service.update_document_metadata(
                document_id, metadata_updates, merge_mode="update"
            )

            log_event(
                "background_date_extraction_completed",
                {
                    "document_id": document_id,
                    "dates_found": has_valid_date,
                    "extracted_date": extracted_date if has_valid_date else None,
                    "metadata_updated": success,
                },
            )

        except asyncio.TimeoutError:
            log_event(
                "background_date_extraction_timeout",
                {
                    "document_id": document_id,
                    "timeout_seconds": 120,
                },
                level=logging.WARNING,
            )
            raise

    @track(
        operation="process_auto_tagging",
        include_args=["document_id"],
        track_performance=True,
        frequency="medium_frequency",
    )
    async def _process_auto_tagging(self, task: Dict[str, Any]):
        """Process auto-tagging for a document."""
        document_id = task.get("document_id")
        data = task.get("data", {})
        text = data.get("text", "")

        log_event(
            "background_auto_tagging_started",
            {
                "document_id": document_id,
                "text_length": len(text),
            },
        )

        await self.llamaindex_service.update_document_metadata(
            document_id,
            {
                "enrichment_status": "tags_generated",
                "enriched_at": datetime.now().isoformat(),
            },
            merge_mode="update",
        )

        log_event(
            "background_auto_tagging_completed",
            {
                "document_id": document_id,
            },
        )

    async def shutdown(self):
        """
        Public method for graceful shutdown of the worker.

        Stops the worker loop and cleans up resources.
        """
        await self._shutdown()

    async def _shutdown(self):
        """Internal implementation for graceful shutdown."""
        self.running = False

        log_event(
            "enrichment_worker_shutdown",
            {
                "tasks_processed": self.tasks_processed,
                "tasks_failed": self.tasks_failed,
            },
        )

        await self.queue.cleanup()

    @track(
        operation="get_worker_status",
        track_performance=True,
        frequency="low_frequency",
    )
    async def get_status(self) -> Dict[str, Any]:
        """Get worker status."""
        queue_stats = await self.queue.get_stats()

        return {
            "worker": {
                "running": self.running,
                "tasks_processed": self.tasks_processed,
                "tasks_failed": self.tasks_failed,
            },
            "queue": queue_stats,
        }


async def main():
    """Main entry point for running the worker."""
    worker = EnrichmentWorker()

    try:
        await worker.initialize()
        await worker.run()
    except KeyboardInterrupt:
        log_event("enrichment_worker_interrupted", {})
    except Exception as e:
        log_event(
            "enrichment_worker_fatal_error",
            {
                "error_type": type(e).__name__,
                "error": str(e),
            },
            level=logging.ERROR,
        )
        raise
    finally:
        await worker.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
