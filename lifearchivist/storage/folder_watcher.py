"""
Multi-folder watching service for automatic document ingestion.

Monitors multiple folders for new documents and automatically queues them
for processing. Uses OS-level filesystem events for efficient detection.

Architecture:
- Each folder has its own Observer and EventHandler
- Shared semaphore limits concurrent ingestions across all folders
- Redis persistence for folder configurations
- Thread-safe event loop integration
"""

import asyncio
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
from uuid import uuid4

import aiofiles
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from lifearchivist.models.folder_watch import (
    FolderStats,
    FolderWatchStatus,
    WatchedFolder,
)
from lifearchivist.storage.redis_folder_watch_store import RedisFolderWatchStore
from lifearchivist.utils.logging import log_event

logger = logging.getLogger(__name__)


class FolderWatcherService:
    """
    Service for watching multiple folders and auto-ingesting new documents.

    Features:
    - Multi-folder support with individual observers per folder
    - OS-level filesystem events (no polling)
    - Debouncing for file writes
    - Hash-based deduplication
    - Configurable file type filters
    - Concurrency control via semaphore
    - Redis persistence for folder configurations
    - Graceful start/stop per folder
    """

    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        ".pdf",
        ".docx",
        ".doc",
        ".txt",
        ".md",
        ".rtf",
        ".odt",
        ".xlsx",
        ".xls",
        ".csv",
    }

    def __init__(
        self,
        vault=None,
        server=None,
        redis_url: str = "redis://localhost:6379",
        debounce_seconds: float = 2.0,
        ingestion_concurrency: int = 5,
        max_folders: int = 100,
    ):
        """
        Initialize the multi-folder watcher service.

        Args:
            vault: Vault storage instance for deduplication checks
            server: Application server instance for tool execution
            redis_url: Redis connection URL for persistence
            debounce_seconds: Seconds to wait before processing a file
            ingestion_concurrency: Maximum concurrent file ingestions across all folders
            max_folders: Maximum number of folders that can be watched
        """
        self.vault = vault
        self.server = server
        self.redis_url = redis_url
        self.debounce_seconds = debounce_seconds
        self.ingestion_concurrency = ingestion_concurrency
        self.max_folders = max_folders

        # Multi-folder state: folder_id -> WatchedFolder
        self.watched_folders: Dict[str, WatchedFolder] = {}

        # Event loop for thread-safe task scheduling
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None

        # Track pending files: (folder_id, file_path) -> asyncio.Task
        # This allows us to track which folder each file belongs to
        self.pending_tasks: Dict[Tuple[str, Path], asyncio.Task] = {}

        # Concurrency control: Limit simultaneous ingestions across all folders
        # This prevents resource exhaustion when multiple folders drop files simultaneously
        self.ingestion_semaphore: Optional[asyncio.Semaphore] = None

        # Redis persistence store
        self.store: Optional[RedisFolderWatchStore] = None

        # Initialization state
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the folder watcher service.

        This must be called before using the service.
        Initializes Redis store, event loop, and auto-resumes persisted folders.
        """
        if self._initialized:
            logger.warning("FolderWatcherService already initialized")
            return

        try:
            # Capture event loop
            self.event_loop = asyncio.get_running_loop()
            logger.info(f"Captured event loop: {self.event_loop}")

            # Initialize semaphore for concurrency control
            self.ingestion_semaphore = asyncio.Semaphore(self.ingestion_concurrency)
            logger.info(
                f"Initialized ingestion semaphore with limit: {self.ingestion_concurrency}"
            )

            # Initialize Redis store
            self.store = RedisFolderWatchStore(redis_url=self.redis_url)
            await self.store.initialize()

            # Auto-resume persisted folders from Redis
            await self._resume_persisted_folders()

            self._initialized = True

            log_event(
                "folder_watcher_service_initialized",
                {
                    "max_folders": self.max_folders,
                    "ingestion_concurrency": self.ingestion_concurrency,
                    "debounce_seconds": self.debounce_seconds,
                    "resumed_folders": len(self.watched_folders),
                },
            )

        except Exception as e:
            logger.error(
                f"Failed to initialize FolderWatcherService: {e}", exc_info=True
            )
            raise

    @property
    def _store(self) -> RedisFolderWatchStore:
        """
        Get Redis store, ensuring service is initialized.

        Returns:
            RedisFolderWatchStore instance

        Raises:
            RuntimeError: If service not initialized
        """
        if self.store is None:
            raise RuntimeError(
                "FolderWatcherService not initialized. Call initialize() first."
            )
        return self.store

    async def cleanup(self) -> None:
        """
        Cleanup all resources.

        Stops all folder watchers and closes Redis connection.
        """
        if not self._initialized:
            return

        try:
            # Stop all folder watchers
            folder_ids = list(self.watched_folders.keys())
            for folder_id in folder_ids:
                await self.remove_folder(folder_id)

            # Close Redis store
            if self.store:
                await self.store.close()

            self._initialized = False

            log_event("folder_watcher_service_cleaned_up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

    async def add_folder(
        self, path: Path, folder_id: Optional[str] = None, enabled: bool = True
    ) -> str:
        """
        Add a folder to watch.

        Args:
            path: Absolute path to folder
            folder_id: Optional UUID (generated if not provided)
            enabled: Whether to start watching immediately

        Returns:
            folder_id of the added folder

        Raises:
            ValueError: If path already watched, folder limit reached, or path invalid
            RuntimeError: If service not initialized
        """
        if not self._initialized:
            raise RuntimeError("FolderWatcherService not initialized")

        # Validate folder count
        if len(self.watched_folders) >= self.max_folders:
            raise ValueError(
                f"Maximum folder limit reached ({self.max_folders}). "
                f"Remove a folder before adding more."
            )

        # Validate path
        if not path.exists():
            raise ValueError(f"Folder does not exist: {path}")

        if not path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        # Check if path already watched
        existing_id = await self._store.get_folder_id_by_path(str(path))
        if existing_id:
            raise ValueError(f"Folder already being watched: {path}")

        # Generate folder_id if not provided
        if not folder_id:
            folder_id = str(uuid4())

        # Create WatchedFolder instance first (in-memory only)
        watched_folder = WatchedFolder(
            id=folder_id,
            path=path,
            enabled=enabled,
            created_at=datetime.utcnow(),
            stats=FolderStats(),
            observer=None,
            handler=None,
            status=FolderWatchStatus.STOPPED,
        )

        redis_persisted = False
        watching_started = False

        try:
            # Add to in-memory state first
            self.watched_folders[folder_id] = watched_folder

            # Start watching if enabled (before Redis to fail fast)
            if enabled:
                await self._start_watching(folder_id)
                watching_started = True

            # Persist to Redis last (after everything else succeeds)
            await self._store.add_folder(
                path=str(path), folder_id=folder_id, enabled=enabled
            )
            redis_persisted = True

            log_event(
                "folder_watch_added",
                {
                    "folder_id": folder_id,
                    "path": str(path),
                    "enabled": enabled,
                },
            )

            logger.info(f"Added watched folder: {path} (ID: {folder_id})")

            return folder_id

        except Exception as e:
            # Cleanup in reverse order of operations
            logger.error(f"Failed to add folder {path}: {e}", exc_info=True)

            # Stop watching if we started it
            if watching_started:
                try:
                    await self._stop_watching(folder_id)
                except Exception as stop_err:
                    logger.error(f"Error stopping watcher during cleanup: {stop_err}")

            # Remove from Redis if we persisted it
            if redis_persisted:
                try:
                    await self._store.remove_folder(folder_id)
                except Exception as redis_err:
                    logger.error(
                        f"Error removing from Redis during cleanup: {redis_err}"
                    )

            # Remove from in-memory state
            if folder_id in self.watched_folders:
                del self.watched_folders[folder_id]

            raise

    async def remove_folder(self, folder_id: str) -> bool:
        """
        Remove a watched folder.

        Args:
            folder_id: Folder UUID

        Returns:
            True if folder was removed, False if not found

        Raises:
            Exception: If removal fails (folder remains in inconsistent state)
        """
        if not self._initialized:
            raise RuntimeError("FolderWatcherService not initialized")

        if folder_id not in self.watched_folders:
            return False

        watched_folder = self.watched_folders[folder_id]
        folder_path = watched_folder.path

        try:
            # Stop watching if active
            if watched_folder.is_active():
                await self._stop_watching(folder_id)

            # Cancel pending tasks for this folder
            tasks_to_cancel = [
                (key, task)
                for key, task in self.pending_tasks.items()
                if key[0] == folder_id
            ]
            for key, task in tasks_to_cancel:
                task.cancel()
                self.pending_tasks.pop(key, None)

            # Remove from Redis first (fail fast if Redis is down)
            await self._store.remove_folder(folder_id)

            # Only remove from in-memory state if Redis removal succeeded
            del self.watched_folders[folder_id]

            log_event(
                "folder_watch_removed",
                {
                    "folder_id": folder_id,
                    "path": str(folder_path),
                },
            )

            logger.info(f"Removed watched folder: {folder_path} (ID: {folder_id})")

            return True

        except Exception as e:
            logger.error(
                f"Error removing folder {folder_id}: {e}. "
                f"Folder may be in inconsistent state.",
                exc_info=True,
            )
            # Don't delete from memory if Redis failed - keeps state consistent
            raise

    async def enable_folder(self, folder_id: str) -> bool:
        """
        Enable watching for a folder.

        Args:
            folder_id: Folder UUID

        Returns:
            True if folder was enabled, False if not found
        """
        if not self._initialized:
            raise RuntimeError("FolderWatcherService not initialized")

        if folder_id not in self.watched_folders:
            return False

        watched_folder = self.watched_folders[folder_id]

        if watched_folder.enabled and watched_folder.is_active():
            logger.debug(f"Folder {folder_id} already enabled and active")
            return True

        try:
            # Update state
            watched_folder.enabled = True
            await self._store.update_folder(folder_id, {"enabled": True})

            # Start watching
            await self._start_watching(folder_id)

            logger.info(f"Enabled folder watching: {watched_folder.path}")

            return True

        except Exception as e:
            logger.error(f"Error enabling folder {folder_id}: {e}", exc_info=True)
            raise

    async def disable_folder(self, folder_id: str) -> bool:
        """
        Disable watching for a folder.

        Args:
            folder_id: Folder UUID

        Returns:
            True if folder was disabled, False if not found
        """
        if not self._initialized:
            raise RuntimeError("FolderWatcherService not initialized")

        if folder_id not in self.watched_folders:
            return False

        watched_folder = self.watched_folders[folder_id]

        if not watched_folder.enabled:
            logger.debug(f"Folder {folder_id} already disabled")
            return True

        try:
            # Stop watching
            await self._stop_watching(folder_id)

            # Update state
            watched_folder.enabled = False
            await self._store.update_folder(folder_id, {"enabled": False})

            logger.info(f"Disabled folder watching: {watched_folder.path}")

            return True

        except Exception as e:
            logger.error(f"Error disabling folder {folder_id}: {e}", exc_info=True)
            raise

    async def get_folder(self, folder_id: str) -> Optional[WatchedFolder]:
        """
        Get folder by ID.

        Args:
            folder_id: Folder UUID

        Returns:
            WatchedFolder instance or None if not found
        """
        return self.watched_folders.get(folder_id)

    async def list_folders(self, enabled_only: bool = False) -> list[WatchedFolder]:
        """
        List all watched folders with fresh stats from Redis.

        Args:
            enabled_only: If True, only return enabled folders

        Returns:
            List of WatchedFolder instances with current stats
        """
        folders = list(self.watched_folders.values())

        # Refresh stats from Redis for each folder
        for folder in folders:
            try:
                folder_data = await self._store.get_folder(folder.id)
                if folder_data:
                    # Update stats from Redis
                    folder.stats.files_detected = folder_data.get("files_detected", 0)
                    folder.stats.files_ingested = folder_data.get("files_ingested", 0)
                    folder.stats.files_skipped = folder_data.get("files_skipped", 0)
                    folder.stats.files_failed = folder_data.get("files_failed", 0)
                    folder.stats.bytes_processed = folder_data.get("bytes_processed", 0)
                    folder.stats.error_count = folder_data.get("error_count", 0)
                    folder.stats.last_error = folder_data.get("last_error", "")

                    # Update timestamps if present
                    if folder_data.get("last_activity"):
                        folder.stats.last_activity = datetime.fromisoformat(
                            folder_data["last_activity"]
                        )
            except Exception as e:
                logger.warning(f"Failed to refresh stats for folder {folder.id}: {e}")

        if enabled_only:
            folders = [f for f in folders if f.enabled]

        # Sort by created_at descending (newest first)
        folders.sort(key=lambda f: f.created_at, reverse=True)

        return folders

    async def _start_watching(self, folder_id: str) -> None:
        """
        Start watching a folder (internal method).

        Args:
            folder_id: Folder UUID
        """
        watched_folder = self.watched_folders.get(folder_id)
        if not watched_folder:
            raise ValueError(f"Folder not found: {folder_id}")

        if watched_folder.is_active():
            logger.debug(f"Folder {folder_id} already watching")
            return

        try:
            # Create event handler
            handler = DocumentEventHandler(
                watcher_service=self,
                folder_id=folder_id,
                vault=self.vault,
                server=self.server,
            )

            # Create and start observer
            observer = Observer()
            observer.schedule(handler, str(watched_folder.path), recursive=True)
            observer.start()

            # Update watched folder
            watched_folder.observer = observer
            watched_folder.handler = handler
            watched_folder.status = FolderWatchStatus.ACTIVE

            log_event(
                "folder_watch_started",
                {
                    "folder_id": folder_id,
                    "path": str(watched_folder.path),
                    "recursive": True,
                },
            )

            logger.info(f"Started watching folder: {watched_folder.path}")

        except Exception as e:
            watched_folder.status = FolderWatchStatus.ERROR
            logger.error(
                f"Failed to start watching folder {folder_id}: {e}", exc_info=True
            )
            raise

    async def _stop_watching(self, folder_id: str) -> None:
        """
        Stop watching a folder (internal method).

        Args:
            folder_id: Folder UUID
        """
        watched_folder = self.watched_folders.get(folder_id)
        if not watched_folder:
            return

        try:
            # Stop observer
            if watched_folder.observer:
                watched_folder.observer.stop()
                watched_folder.observer.join(timeout=5)

            # Clear references
            watched_folder.observer = None
            watched_folder.handler = None
            watched_folder.status = FolderWatchStatus.STOPPED

            log_event(
                "folder_watch_stopped",
                {
                    "folder_id": folder_id,
                    "path": str(watched_folder.path),
                },
            )

            logger.info(f"Stopped watching folder: {watched_folder.path}")

        except Exception as e:
            logger.error(f"Error stopping folder {folder_id}: {e}", exc_info=True)

    async def _resume_persisted_folders(self) -> None:
        """
        Resume watching folders persisted in Redis.

        Called during initialization to restore watched folders after server restart.
        """
        try:
            # Fetch all folders from Redis
            persisted_folders = await self._store.list_folders()

            if not persisted_folders:
                logger.info("No persisted folders to resume")
                return

            resumed_count = 0
            failed_count = 0

            for folder_data in persisted_folders:
                folder_id = folder_data["id"]
                folder_path = Path(folder_data["path"])
                enabled = folder_data["enabled"]

                try:
                    # Validate folder still exists
                    if not folder_path.exists() or not folder_path.is_dir():
                        logger.warning(
                            f"Skipping folder {folder_id}: path no longer exists or not a directory: {folder_path}"
                        )
                        # Mark as error in Redis but don't remove
                        await self._store.set_folder_error(
                            folder_id, "Folder path no longer accessible"
                        )
                        failed_count += 1
                        continue

                    # Load stats from Redis
                    stats = FolderStats(
                        files_detected=folder_data.get("files_detected", 0),
                        files_ingested=folder_data.get("files_ingested", 0),
                        files_skipped=folder_data.get("files_skipped", 0),
                        files_failed=folder_data.get("files_failed", 0),
                        bytes_processed=folder_data.get("bytes_processed", 0),
                        last_activity=(
                            datetime.fromisoformat(folder_data["last_activity"])
                            if folder_data.get("last_activity")
                            else None
                        ),
                        error_count=folder_data.get("error_count", 0),
                        last_error=folder_data.get("last_error", ""),
                    )

                    # Create WatchedFolder instance
                    watched_folder = WatchedFolder(
                        id=folder_id,
                        path=folder_path,
                        enabled=enabled,
                        created_at=datetime.fromisoformat(folder_data["created_at"]),
                        stats=stats,
                        observer=None,
                        handler=None,
                        status=FolderWatchStatus.STOPPED,
                    )

                    # Add to in-memory state
                    self.watched_folders[folder_id] = watched_folder

                    # Start watching if enabled
                    if enabled:
                        await self._start_watching(folder_id)
                        resumed_count += 1
                    else:
                        logger.info(f"Loaded disabled folder: {folder_path}")

                except Exception as e:
                    logger.error(
                        f"Failed to resume folder {folder_id} ({folder_path}): {e}",
                        exc_info=True,
                    )
                    failed_count += 1

            log_event(
                "folder_watch_resume_complete",
                {
                    "total_folders": len(persisted_folders),
                    "resumed": resumed_count,
                    "failed": failed_count,
                },
            )

            logger.info(
                f"Resumed {resumed_count} folders, {failed_count} failed, "
                f"{len(persisted_folders) - resumed_count - failed_count} disabled"
            )

        except Exception as e:
            logger.error(f"Error resuming persisted folders: {e}", exc_info=True)
            # Don't fail initialization if resume fails

    def is_supported_file(self, file_path: Path) -> bool:
        """
        Check if file type is supported.

        Args:
            file_path: Path to file

        Returns:
            True if file extension is supported
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def schedule_ingestion(self, folder_id: str, file_path: Path) -> None:
        """
        Schedule a file for ingestion after debounce period.

        Args:
            folder_id: Folder UUID that detected the file
            file_path: Path to file to ingest
        """
        key = (folder_id, file_path)

        # Cancel existing task for this file if any
        if key in self.pending_tasks:
            self.pending_tasks[key].cancel()

        # Schedule new task
        task = asyncio.create_task(self._debounced_ingestion(folder_id, file_path))
        self.pending_tasks[key] = task

        # Notify frontend of status change
        await self._notify_status_change()

    async def _debounced_ingestion(self, folder_id: str, file_path: Path) -> None:
        """
        Wait for debounce period, then ingest file.

        Args:
            folder_id: Folder UUID
            file_path: Path to file to ingest
        """
        key = (folder_id, file_path)

        try:
            # Wait for file to stabilize
            await asyncio.sleep(self.debounce_seconds)

            # Verify file still exists
            if not file_path.exists():
                logger.debug(f"File no longer exists: {file_path}")
                return

            # Verify file is readable
            if not file_path.is_file():
                logger.debug(f"Path is not a file: {file_path}")
                return

            # Check file size is reasonable
            file_size = file_path.stat().st_size
            if file_size == 0:
                logger.debug(f"File is empty: {file_path}")
                return

            if file_size > 100 * 1024 * 1024:  # 100MB
                logger.warning(f"File too large: {file_path} ({file_size} bytes)")
                await self._record_file_failed(folder_id, file_path, "File too large")
                return

            # Increment detected counter
            await self._store.increment_stat(folder_id, "files_detected", 1)

            # Check for duplicates using hash
            if await self._is_duplicate(file_path):
                logger.info(f"File already in vault (duplicate): {file_path.name}")
                await self._store.increment_stat(folder_id, "files_skipped", 1)
                log_event(
                    "folder_watch_duplicate_skipped",
                    {
                        "folder_id": folder_id,
                        "file_path": str(file_path),
                        "file_size": file_size,
                    },
                )
                return

            # Queue for ingestion
            await self._ingest_file(folder_id, file_path)

        except asyncio.CancelledError:
            # Task was cancelled (new event for same file)
            logger.debug(f"Ingestion cancelled: {file_path}")
        except Exception as e:
            logger.error(f"Error during debounced ingestion: {e}", exc_info=True)
            await self._record_file_failed(folder_id, file_path, str(e))
        finally:
            # Clean up task reference
            self.pending_tasks.pop(key, None)
            # Notify frontend that pending count changed
            await self._notify_status_change()

    async def _is_duplicate(self, file_path: Path) -> bool:
        """
        Check if file is already in vault using hash.

        Args:
            file_path: Path to file

        Returns:
            True if file already exists in vault
        """
        if not self.vault:
            return False

        try:
            # Calculate file hash
            file_hash = await self._calculate_hash(file_path)

            # Check if file exists in vault
            content_dir = self.vault.content_dir
            dir1 = file_hash[:2]
            dir2 = file_hash[2:4]
            file_stem = file_hash[4:]

            file_dir = content_dir / dir1 / dir2
            if not file_dir.exists():
                return False

            # Check if any file with this hash exists
            matching_files = list(file_dir.glob(f"{file_stem}.*"))
            return len(matching_files) > 0

        except Exception as e:
            logger.error(f"Error checking for duplicate: {e}")
            return False

    async def _calculate_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file using async I/O.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA256 hash
        """
        sha256_hash = hashlib.sha256()

        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    async def _ingest_file(self, folder_id: str, file_path: Path) -> None:
        """
        Ingest a file using the file.import tool with concurrency control.

        Args:
            folder_id: Folder UUID
            file_path: Path to file to ingest
        """
        if not self.server:
            logger.error("Server not available for ingestion")
            return

        if not self.ingestion_semaphore:
            logger.error("Ingestion semaphore not initialized")
            return

        watched_folder = self.watched_folders.get(folder_id)
        if not watched_folder:
            logger.error(f"Folder not found: {folder_id}")
            return

        # Acquire semaphore to limit concurrent ingestions
        async with self.ingestion_semaphore:
            logger.debug(
                f"Acquired ingestion slot for {file_path.name} "
                f"({self.ingestion_semaphore._value}/{self.ingestion_concurrency} available)"
            )

            try:
                logger.info(
                    f"Auto-ingesting file: {file_path.name} from folder {folder_id}"
                )

                # Execute file import tool
                result = await self.server.execute_tool(
                    "file.import",
                    {
                        "path": str(file_path),
                        "tags": ["auto-ingested"],
                        "metadata": {
                            "source": "folder_watch",
                            "auto_ingested": True,
                            "watched_folder": str(watched_folder.path),
                            "folder_id": folder_id,
                        },
                    },
                )

                if result.get("success"):
                    # Update stats
                    file_size = file_path.stat().st_size
                    await self._store.increment_stat(folder_id, "files_ingested", 1)
                    await self._store.increment_stat(
                        folder_id, "bytes_processed", file_size
                    )
                    await self._store.clear_folder_error(folder_id)

                    log_event(
                        "folder_watch_file_ingested",
                        {
                            "folder_id": folder_id,
                            "file_path": str(file_path),
                            "file_name": file_path.name,
                            "file_size": file_size,
                        },
                    )
                    logger.info(f"Successfully ingested: {file_path.name}")

                    # Add activity event with folder context
                    if self.server.activity_manager:
                        await self.server.activity_manager.add_folder_watch_event(
                            "file_ingested",
                            file_path.name,
                            folder_id=folder_id,
                            folder_path=str(watched_folder.path),
                            file_size=file_size,
                        )
                else:
                    error = result.get("error", "Unknown error")
                    await self._record_file_failed(folder_id, file_path, error)

            except Exception as e:
                logger.error(f"Error ingesting file: {e}", exc_info=True)
                await self._record_file_failed(folder_id, file_path, str(e))

    async def _record_file_failed(
        self, folder_id: str, file_path: Path, error: str
    ) -> None:
        """
        Record a failed file ingestion.

        Args:
            folder_id: Folder UUID
            file_path: Path to file
            error: Error message
        """
        try:
            await self._store.increment_stat(folder_id, "files_failed", 1)
            await self._store.set_folder_error(folder_id, error)

            log_event(
                "folder_watch_ingestion_failed",
                {
                    "folder_id": folder_id,
                    "file_path": str(file_path),
                    "error": error,
                },
                level=logging.ERROR,
            )

            # Add activity event with folder context
            if self.server and self.server.activity_manager:
                watched_folder = self.watched_folders.get(folder_id)
                await self.server.activity_manager.add_folder_watch_event(
                    "file_failed",
                    file_path.name,
                    folder_id=folder_id,
                    folder_path=str(watched_folder.path) if watched_folder else None,
                    error=error,
                )

        except Exception as e:
            logger.error(f"Error recording failure: {e}", exc_info=True)

    async def _notify_status_change(self) -> None:
        """Broadcast status change to all connected WebSocket clients."""
        if not self.server or not self.server.session_manager:
            return

        try:
            status = await self.get_aggregate_status()
            await self.server.session_manager.broadcast(
                {"type": "folder_watch_status", "data": status}
            )
            logger.debug(
                f"Broadcasted folder watch status: {status['total_pending']} pending"
            )
        except Exception as e:
            logger.error(f"Failed to broadcast status change: {e}", exc_info=True)

    async def get_status(self) -> Dict[str, Dict]:
        """
        Get per-folder status for all watched folders.

        Returns:
            Dictionary mapping folder_id to folder status dict

        Example:
            {
                "uuid-1": {
                    "folder_id": "uuid-1",
                    "path": "/path/to/folder",
                    "enabled": True,
                    "status": "active",
                    "health": "healthy",
                    "is_active": True,
                    "pending_files": 3,
                    "stats": {...},
                    "created_at": "2024-01-01T00:00:00",
                    "success_rate": 0.95
                },
                ...
            }
        """
        folders = await self.list_folders()
        status_dict = {}

        for folder in folders:
            # Count pending files for this folder
            pending_count = sum(
                1 for key in self.pending_tasks.keys() if key[0] == folder.id
            )

            status_dict[folder.id] = {
                "folder_id": folder.id,
                "path": str(folder.path),
                "enabled": folder.enabled,
                "status": folder.status.value,
                "health": folder.stats.get_health_status().value,
                "is_active": folder.is_active(),
                "pending_files": pending_count,
                "stats": folder.stats.to_dict(),
                "created_at": folder.created_at.isoformat(),
                "success_rate": folder.stats.get_success_rate(),
            }

        return status_dict

    async def get_aggregate_status(self) -> Dict:
        """
        Get aggregate status across all watched folders.

        Returns:
            Dictionary with aggregate statistics

        Example:
            {
                "total_folders": 5,
                "active_folders": 3,
                "total_pending": 10,
                "total_detected": 1000,
                "total_ingested": 950,
                "total_failed": 50,
                "total_bytes_processed": 1073741824,
                "supported_extensions": [".pdf", ".docx", ...],
                "ingestion_concurrency": 5
            }
        """
        folders = await self.list_folders()

        total_detected = 0
        total_ingested = 0
        total_failed = 0
        total_bytes = 0
        active_count = 0

        for folder in folders:
            if folder.is_active():
                active_count += 1
            total_detected += folder.stats.files_detected
            total_ingested += folder.stats.files_ingested
            total_failed += folder.stats.files_failed
            total_bytes += folder.stats.bytes_processed

        return {
            "total_folders": len(folders),
            "active_folders": active_count,
            "total_pending": len(self.pending_tasks),
            "total_detected": total_detected,
            "total_ingested": total_ingested,
            "total_failed": total_failed,
            "total_bytes_processed": total_bytes,
            "supported_extensions": list(self.SUPPORTED_EXTENSIONS),
            "ingestion_concurrency": self.ingestion_concurrency,
        }


class DocumentEventHandler(FileSystemEventHandler):
    """
    Handles filesystem events for document ingestion.

    Each folder has its own handler instance.
    """

    def __init__(
        self,
        watcher_service: FolderWatcherService,
        folder_id: str,
        vault=None,
        server=None,
    ):
        """
        Initialize event handler.

        Args:
            watcher_service: Parent watcher service
            folder_id: UUID of folder being watched
            vault: Vault storage instance
            server: Application server instance
        """
        super().__init__()
        self.watcher_service = watcher_service
        self.folder_id = folder_id
        self.vault = vault
        self.server = server

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        file_path = Path(os.fsdecode(event.src_path))

        # Filter by extension
        if not self.watcher_service.is_supported_file(file_path):
            logger.debug(f"Ignoring unsupported file: {file_path.name}")
            return

        # Ignore hidden files and temp files
        if file_path.name.startswith(".") or file_path.name.startswith("~"):
            logger.debug(f"Ignoring hidden/temp file: {file_path.name}")
            return

        logger.info(f"New file detected: {file_path.name} in folder {self.folder_id}")

        # Schedule for ingestion using thread-safe method
        self._schedule_async_task(file_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        if event.is_directory:
            return

        file_path = Path(os.fsdecode(event.src_path))

        # Only process supported files
        if not self.watcher_service.is_supported_file(file_path):
            return

        # Ignore hidden/temp files
        if file_path.name.startswith(".") or file_path.name.startswith("~"):
            return

        logger.debug(f"File modified: {file_path.name} in folder {self.folder_id}")

        # Schedule for ingestion using thread-safe method
        self._schedule_async_task(file_path)

    def _schedule_async_task(self, file_path: Path) -> None:
        """
        Schedule an async task from a synchronous context (thread-safe).

        Args:
            file_path: Path to file to schedule
        """
        try:
            # Use the captured event loop from the watcher service
            if not self.watcher_service.event_loop:
                logger.error("No event loop available for scheduling")
                return

            # Schedule the coroutine in a thread-safe manner
            future = asyncio.run_coroutine_threadsafe(
                self.watcher_service.schedule_ingestion(self.folder_id, file_path),
                self.watcher_service.event_loop,
            )

            logger.debug(
                f"Scheduled ingestion for {file_path.name} "
                f"from folder {self.folder_id}, future: {future}"
            )

        except Exception as e:
            logger.error(
                f"Failed to schedule ingestion for {file_path.name}: {e}",
                exc_info=True,
            )
