"""
Folder watching service for automatic document ingestion.

Monitors specified folders for new documents and automatically queues them
for processing. Uses OS-level filesystem events for efficient detection.
"""

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Dict, Optional

import aiofiles
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from lifearchivist.utils.logging import log_event

logger = logging.getLogger(__name__)


class FolderWatcherService:
    """
    Service for watching folders and auto-ingesting new documents.

    Features:
    - OS-level filesystem events (no polling)
    - Debouncing for file writes
    - Hash-based deduplication
    - Configurable file type filters
    - Graceful start/stop
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
        debounce_seconds: float = 2.0,
    ):
        """
        Initialize the folder watcher service.

        Args:
            vault: Vault storage instance for deduplication checks
            server: MCP server instance for tool execution
            debounce_seconds: Seconds to wait before processing a file
        """
        self.vault = vault
        self.server = server
        self.debounce_seconds = debounce_seconds

        self.observer: Optional[Observer] = None
        self.watched_path: Optional[Path] = None
        self.handler: Optional[DocumentEventHandler] = None
        self.enabled = False
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None

        # Track pending files for debouncing
        self.pending_tasks: Dict[Path, asyncio.Task] = {}

    async def start(self, folder_path: Path) -> bool:
        """
        Start watching a folder.

        Args:
            folder_path: Path to folder to watch

        Returns:
            True if started successfully, False otherwise
        """
        if self.enabled:
            logger.warning("Folder watcher already running")
            return False

        # Validate folder exists
        if not folder_path.exists():
            logger.error(f"Folder does not exist: {folder_path}")
            return False

        if not folder_path.is_dir():
            logger.error(f"Path is not a directory: {folder_path}")
            return False

        try:
            # Capture the current event loop for thread-safe task scheduling
            # This must be called from within an async context (which it is, since start() is async)
            self.event_loop = asyncio.get_running_loop()
            logger.info(f"Captured event loop: {self.event_loop}")

            # Create event handler
            self.handler = DocumentEventHandler(
                watcher_service=self,
                vault=self.vault,
                server=self.server,
            )

            # Create and start observer
            self.observer = Observer()
            self.observer.schedule(
                self.handler, str(folder_path), recursive=True  # Watch subdirectories
            )
            self.observer.start()

            self.watched_path = folder_path
            self.enabled = True

            log_event(
                "folder_watcher_started",
                {
                    "folder_path": str(folder_path),
                    "recursive": True,
                    "supported_extensions": list(self.SUPPORTED_EXTENSIONS),
                },
            )

            logger.info(f"Folder watcher started: {folder_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to start folder watcher: {e}", exc_info=True)
            log_event(
                "folder_watcher_start_failed",
                {"folder_path": str(folder_path), "error": str(e)},
                level=logging.ERROR,
            )
            return False

    async def stop(self):
        """Stop watching the folder."""
        if not self.enabled:
            return

        try:
            # Cancel all pending tasks
            for task in self.pending_tasks.values():
                task.cancel()
            self.pending_tasks.clear()

            # Stop observer
            if self.observer:
                self.observer.stop()
                self.observer.join(timeout=5)

            self.enabled = False
            watched_path = self.watched_path
            self.watched_path = None
            self.observer = None
            self.handler = None

            log_event(
                "folder_watcher_stopped",
                {"folder_path": str(watched_path) if watched_path else None},
            )

            logger.info("Folder watcher stopped")

        except Exception as e:
            logger.error(f"Error stopping folder watcher: {e}", exc_info=True)

    def is_supported_file(self, file_path: Path) -> bool:
        """
        Check if file type is supported.

        Args:
            file_path: Path to file

        Returns:
            True if file extension is supported
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    async def schedule_ingestion(self, file_path: Path):
        """
        Schedule a file for ingestion after debounce period.

        Args:
            file_path: Path to file to ingest
        """
        # Cancel existing task for this file if any
        if file_path in self.pending_tasks:
            self.pending_tasks[file_path].cancel()

        # Schedule new task
        task = asyncio.create_task(self._debounced_ingestion(file_path))
        self.pending_tasks[file_path] = task

        # Notify frontend of status change
        await self._notify_status_change()

    async def _debounced_ingestion(self, file_path: Path):
        """
        Wait for debounce period, then ingest file.

        Args:
            file_path: Path to file to ingest
        """
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
                return

            # Check for duplicates using hash
            if await self._is_duplicate(file_path):
                logger.info(f"File already in vault (duplicate): {file_path.name}")
                log_event(
                    "folder_watch_duplicate_skipped",
                    {"file_path": str(file_path), "file_size": file_size},
                )
                return

            # Queue for ingestion
            await self._ingest_file(file_path)

        except asyncio.CancelledError:
            # Task was cancelled (new event for same file)
            logger.debug(f"Ingestion cancelled: {file_path}")
        except Exception as e:
            logger.error(f"Error during debounced ingestion: {e}", exc_info=True)
            log_event(
                "folder_watch_ingestion_error",
                {
                    "file_path": str(file_path),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
        finally:
            # Clean up task reference
            self.pending_tasks.pop(file_path, None)
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
            # Vault uses content-addressed storage with hash-based paths
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

        This prevents blocking the event loop when hashing large files.
        For a 100MB file, this can take 1-2 seconds, so async I/O is critical.

        Args:
            file_path: Path to file

        Returns:
            Hex string of SHA256 hash
        """
        sha256_hash = hashlib.sha256()

        # Use async file I/O to avoid blocking the event loop
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(8192):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()

    async def _ingest_file(self, file_path: Path):
        """
        Ingest a file using the file.import tool.

        Args:
            file_path: Path to file to ingest
        """
        if not self.server:
            logger.error("Server not available for ingestion")
            return

        try:
            logger.info(f"Auto-ingesting file: {file_path.name}")

            # Execute file import tool
            result = await self.server.execute_tool(
                "file.import",
                {
                    "path": str(file_path),
                    "tags": ["auto-ingested"],
                    "metadata": {
                        "source": "folder_watch",
                        "auto_ingested": True,
                        "watched_folder": str(self.watched_path),
                    },
                },
            )

            if result.get("success"):
                log_event(
                    "folder_watch_file_ingested",
                    {
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_size": file_path.stat().st_size,
                    },
                )
                logger.info(f"Successfully ingested: {file_path.name}")

                # Add activity event
                if self.server.activity_manager:
                    await self.server.activity_manager.add_folder_watch_event(
                        "file_ingested",
                        file_path.name,
                        file_size=file_path.stat().st_size,
                        watched_folder=str(self.watched_path),
                    )
            else:
                error = result.get("error", "Unknown error")
                logger.error(f"Failed to ingest {file_path.name}: {error}")
                log_event(
                    "folder_watch_ingestion_failed",
                    {
                        "file_path": str(file_path),
                        "error": error,
                    },
                    level=logging.ERROR,
                )

                # Add activity event for failure
                if self.server.activity_manager:
                    await self.server.activity_manager.add_folder_watch_event(
                        "file_failed",
                        file_path.name,
                        error=error,
                        watched_folder=str(self.watched_path),
                    )

        except Exception as e:
            logger.error(f"Error ingesting file: {e}", exc_info=True)
            log_event(
                "folder_watch_ingestion_exception",
                {
                    "file_path": str(file_path),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )

    async def _notify_status_change(self):
        """
        Broadcast status change to all connected WebSocket clients.

        This enables real-time updates in the frontend without polling.
        """
        if not self.server or not self.server.session_manager:
            return

        try:
            status = self.get_status()
            await self.server.session_manager.broadcast(
                {"type": "folder_watch_status", "data": status}
            )
            logger.debug(
                f"Broadcasted folder watch status: {status['pending_files']} pending"
            )
        except Exception as e:
            logger.error(f"Failed to broadcast status change: {e}", exc_info=True)

    def get_status(self) -> Dict:
        """
        Get current status of folder watcher.

        Returns:
            Dictionary with status information
        """
        return {
            "enabled": self.enabled,
            "watched_path": str(self.watched_path) if self.watched_path else None,
            "pending_files": len(self.pending_tasks),
            "supported_extensions": list(self.SUPPORTED_EXTENSIONS),
            "debounce_seconds": self.debounce_seconds,
        }


class DocumentEventHandler(FileSystemEventHandler):
    """
    Handles filesystem events for document ingestion.

    Filters events and schedules files for ingestion.
    """

    def __init__(
        self,
        watcher_service: FolderWatcherService,
        vault=None,
        server=None,
    ):
        """
        Initialize event handler.

        Args:
            watcher_service: Parent watcher service
            vault: Vault storage instance
            server: MCP server instance
        """
        super().__init__()
        self.watcher_service = watcher_service
        self.vault = vault
        self.server = server

    def on_created(self, event: FileSystemEvent):
        """
        Handle file creation events.

        Args:
            event: Filesystem event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Filter by extension
        if not self.watcher_service.is_supported_file(file_path):
            logger.debug(f"Ignoring unsupported file: {file_path.name}")
            return

        # Ignore hidden files and temp files
        if file_path.name.startswith(".") or file_path.name.startswith("~"):
            logger.debug(f"Ignoring hidden/temp file: {file_path.name}")
            return

        logger.info(f"New file detected: {file_path.name}")

        # Schedule for ingestion using thread-safe method
        self._schedule_async_task(file_path)

    def on_modified(self, event: FileSystemEvent):
        """
        Handle file modification events.

        For MVP, we treat modifications as potential new files
        (in case the file was being written when created event fired).

        Args:
            event: Filesystem event
        """
        if event.is_directory:
            return

        file_path = Path(event.src_path)

        # Only process supported files
        if not self.watcher_service.is_supported_file(file_path):
            return

        # Ignore hidden/temp files
        if file_path.name.startswith(".") or file_path.name.startswith("~"):
            return

        logger.debug(f"File modified: {file_path.name}")

        # Schedule for ingestion using thread-safe method
        self._schedule_async_task(file_path)

    def _schedule_async_task(self, file_path: Path):
        """
        Schedule an async task from a synchronous context (thread-safe).

        Watchdog runs in a separate thread, so we need to use
        run_coroutine_threadsafe to schedule tasks in the main event loop.

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
                self.watcher_service.schedule_ingestion(file_path),
                self.watcher_service.event_loop,
            )

            logger.debug(f"Scheduled ingestion for {file_path.name}, future: {future}")

        except Exception as e:
            logger.error(
                f"Failed to schedule ingestion for {file_path.name}: {e}", exc_info=True
            )
