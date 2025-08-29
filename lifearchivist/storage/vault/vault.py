"""
File vault for content-addressed storage.
"""

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from lifearchivist.storage.vault.vault_utils import (
    build_content_directory,
    build_content_path,
    build_thumbnail_path,
    calculate_file_hash,
    cleanup_empty_directories,
    cleanup_old_temp_files,
    clear_directory_files,
    delete_file_safely,
    find_files_by_hash_pattern,
    generate_image_thumbnail,
    get_comprehensive_directory_stats,
    safe_get_file_size,
)
from lifearchivist.utils.logging import log_context, log_event, log_method
from lifearchivist.utils.logging.structured import MetricsCollector


class Vault:
    """
    Content-addressed file storage system that organizes files by their SHA256 hash.

    Provides automatic deduplication, integrity verification, and efficient storage
    organization. Files are stored in a hierarchical directory structure based on
    their hash to avoid filesystem limitations and enable fast lookups.

    Directory structure:
    - content/: Actual file content organized by hash (ab/cd/efgh123...)
    - thumbnails/: Auto-generated image previews in WEBP format
    - temp/: Temporary files (cleaned up automatically)
    - exports/: Generated export files
    """

    def __init__(self, vault_path: Path):
        """
        Initialize vault with specified storage path.

        Args:
            vault_path: Root directory path for vault storage
        """
        self.vault_path = Path(vault_path)
        self.content_dir = self.vault_path / "content"
        self.thumbnails_dir = self.vault_path / "thumbnails"
        self.temp_dir = self.vault_path / "temp"
        self.exports_dir = self.vault_path / "exports"

    @log_method(
        operation_name="vault_initialization", include_args=True, include_result=True
    )
    async def initialize(self):
        """
        Create vault directory structure if it doesn't exist.

        Creates all necessary subdirectories for content, thumbnails, temp files,
        and exports. Safe to call multiple times.

        Raises:
            OSError: If directory creation fails due to permissions or disk space
        """
        with log_context(
            operation="vault_initialization",
            vault_path=str(self.vault_path),
        ):
            metrics = MetricsCollector("vault_initialization")
            metrics.start()

            directories = [
                ("vault", self.vault_path),
                ("content", self.content_dir),
                ("thumbnails", self.thumbnails_dir),
                ("temp", self.temp_dir),
                ("exports", self.exports_dir),
            ]

            metrics.add_metric("directories_to_create", len(directories))

            log_event(
                "vault_initialization_started",
                {
                    "vault_path": str(self.vault_path),
                    "directories_count": len(directories),
                },
            )

            created_count = 0
            for name, directory in directories:
                try:
                    existed_before = directory.exists()
                    directory.mkdir(parents=True, exist_ok=True)

                    if not existed_before:
                        created_count += 1
                        log_event(
                            "vault_directory_created",
                            {"directory_type": name, "directory_path": str(directory)},
                        )

                    metrics.add_metric(f"{name}_directory_created", not existed_before)

                except OSError as e:
                    metrics.set_error(e)
                    metrics.report("vault_initialization_failed")

                    log_event(
                        "vault_directory_creation_failed",
                        {
                            "directory_type": name,
                            "directory_path": str(directory),
                            "error_message": str(e),
                        },
                    )
                    raise OSError(
                        f"Failed to create vault directory {directory}: {e}"
                    ) from None

            metrics.add_metric("directories_created", created_count)
            metrics.add_metric("directories_existed", len(directories) - created_count)
            metrics.set_success(True)
            metrics.report("vault_initialization_completed")

            log_event(
                "vault_initialization_successful",
                {
                    "vault_path": str(self.vault_path),
                    "directories_created": created_count,
                    "directories_existed": len(directories) - created_count,
                },
            )

    @log_method(
        operation_name="vault_file_clearing", include_args=True, include_result=True
    )
    async def clear_all_files(self, file_hashes: List[str]) -> Dict[str, Any]:
        """
        Remove files from vault storage by hash, or clear entire vault if no hashes provided.

        Args:
            file_hashes: List of SHA256 hashes to delete. If empty, clears all files.

        Returns:
            Dictionary containing deletion metrics:
            - files_deleted: Number of content/thumbnail files removed
            - bytes_reclaimed: Total bytes freed
            - orphaned_files_deleted: Files removed during comprehensive cleanup
            - orphaned_bytes_reclaimed: Bytes freed from orphaned files
            - errors: List of error messages for failed deletions
        """
        with log_context(
            operation="vault_file_clearing",
            vault_path=str(self.vault_path),
            target_hashes_count=len(file_hashes),
            clear_all_mode=len(file_hashes) == 0,
        ):
            metrics = MetricsCollector("vault_file_clearing")
            metrics.start()

            cleared_metrics = {
                "files_deleted": 0,
                "bytes_reclaimed": 0,
                "directories_cleaned": 0,
                "orphaned_files_deleted": 0,
                "orphaned_bytes_reclaimed": 0,
                "errors": [],
            }

            metrics.add_metric("target_hashes_count", len(file_hashes))
            metrics.add_metric("clear_all_mode", len(file_hashes) == 0)

            log_event(
                "vault_clearing_started",
                {
                    "vault_path": str(self.vault_path),
                    "target_hashes_count": len(file_hashes),
                    "clear_all_mode": len(file_hashes) == 0,
                },
            )

            # Clear files by specific hashes
            for file_hash in file_hashes:
                try:
                    await self._delete_file_by_hash(file_hash, cleared_metrics)
                    log_event(
                        "file_hash_cleared", {"file_hash": file_hash, "success": True}
                    )
                except Exception as e:
                    error_msg = f"Failed to delete files for hash {file_hash}: {e}"
                    cleared_metrics["errors"].append(error_msg)
                    log_event(
                        "file_hash_clear_failed",
                        {
                            "file_hash": file_hash,
                            "error_message": str(e),
                            "error_type": type(e).__name__,
                        },
                    )

            # If no file hashes provided or we need comprehensive cleanup, clear all files
            if not file_hashes:
                log_event("vault_comprehensive_clearing_started", {})
                await self._clear_all_vault_files(cleared_metrics)

            # Clean up empty directories
            log_event("vault_directory_cleanup_started", {})
            await self._cleanup_empty_directories()

            # Update final metrics
            metrics.add_metric("files_deleted", cleared_metrics["files_deleted"])
            metrics.add_metric("bytes_reclaimed", cleared_metrics["bytes_reclaimed"])
            metrics.add_metric("errors_count", len(cleared_metrics["errors"]))

            if cleared_metrics["errors"]:
                metrics.set_error(
                    RuntimeError(
                        f"{len(cleared_metrics['errors'])} deletion errors occurred"
                    )
                )
                metrics.report("vault_clearing_completed_with_errors")
            else:
                metrics.set_success(True)
                metrics.report("vault_clearing_completed")

            log_event(
                "vault_clearing_finished",
                {
                    "files_deleted": cleared_metrics["files_deleted"],
                    "bytes_reclaimed": cleared_metrics["bytes_reclaimed"],
                    "errors_count": len(cleared_metrics["errors"]),
                    "success": len(cleared_metrics["errors"]) == 0,
                },
            )

            return cleared_metrics

    async def _clear_all_vault_files(self, metrics: Dict[str, Any]):
        """
        Remove all files from vault storage directories (comprehensive cleanup).

        Args:
            metrics: Dictionary to update with deletion statistics
        """
        directories_to_clear = [self.content_dir, self.thumbnails_dir, self.temp_dir]

        for directory in directories_to_clear:
            await clear_directory_files(directory, metrics)

    async def _delete_file_by_hash(self, file_hash: str, metrics: Dict[str, Any]):
        """
        Delete all files (content and thumbnails) associated with a specific hash.

        Args:
            file_hash: SHA256 hash of the file to delete
            metrics: Dictionary to update with deletion statistics
        """
        # Content files - find all files matching this hash pattern
        content_directory = self._get_content_directory(file_hash)
        matching_files = find_files_by_hash_pattern(content_directory, file_hash)

        for file_path in matching_files:
            await delete_file_safely(file_path, metrics)

        # Thumbnail files
        thumbnail_path = self._get_thumbnail_path(file_hash)
        await delete_file_safely(thumbnail_path, metrics)

    def _get_content_directory(self, file_hash: str) -> Path:
        """
        Get the directory path where content files for this hash are stored.

        Args:
            file_hash: SHA256 hash of the file

        Returns:
            Path to the directory (e.g., content/ab/cd/ for hash starting with 'abcd')
        """
        return build_content_directory(self.content_dir, file_hash)

    async def _cleanup_empty_directories(self):
        """
        Remove empty directories from vault structure while preserving base directories.

        Recursively removes empty subdirectories but keeps the main vault directories
        (content, thumbnails, temp, exports) intact.
        """
        directories_to_check = [self.content_dir, self.thumbnails_dir, self.temp_dir]
        preserve_dirs = [
            self.vault_path,
            self.content_dir,
            self.thumbnails_dir,
            self.temp_dir,
            self.exports_dir,
        ]

        for base_dir in directories_to_check:
            await cleanup_empty_directories(base_dir, preserve_dirs)

    @log_method(
        operation_name="vault_statistics", include_args=True, include_result=True
    )
    async def get_vault_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about vault storage usage.

        Returns:
            Dictionary containing storage metrics:
            - total_files: Total number of files across all directories
            - total_size_bytes: Total storage used in bytes
            - total_size_mb: Total storage used in megabytes
            - content_files/content_size_bytes/content_size_mb: Content file metrics
            - thumbnail_files/thumbnail_size_bytes/thumbnail_size_mb: Thumbnail metrics
            - temp_files/temp_size_bytes/temp_size_mb: Temporary file metrics
            - vault_path: Absolute path to vault root directory
            - error: Error message if statistics collection fails
        """
        with log_context(
            operation="vault_statistics",
            vault_path=str(self.vault_path),
        ):
            metrics = MetricsCollector("vault_statistics")
            metrics.start()

            log_event(
                "vault_statistics_collection_started",
                {"vault_path": str(self.vault_path)},
            )

            try:
                directories = {
                    "content": self.content_dir,
                    "thumbnail": self.thumbnails_dir,
                    "temp": self.temp_dir,
                }

                metrics.add_metric("directories_to_analyze", len(directories))

                stats = await get_comprehensive_directory_stats(directories)
                stats["vault_path"] = str(self.vault_path)

                # Add metrics from calculated statistics
                metrics.add_metric("total_files", stats.get("total_files", 0))
                metrics.add_metric("total_size_bytes", stats.get("total_size_bytes", 0))
                metrics.add_metric("content_files", stats.get("content_files", 0))
                metrics.add_metric("thumbnail_files", stats.get("thumbnail_files", 0))
                metrics.add_metric("temp_files", stats.get("temp_files", 0))

                metrics.set_success(True)
                metrics.report("vault_statistics_completed")

                log_event(
                    "vault_statistics_collection_successful",
                    {
                        "vault_path": str(self.vault_path),
                        "total_files": stats.get("total_files", 0),
                        "total_size_mb": stats.get("total_size_mb", 0),
                        "content_files": stats.get("content_files", 0),
                        "thumbnail_files": stats.get("thumbnail_files", 0),
                        "temp_files": stats.get("temp_files", 0),
                    },
                )

                return stats

            except Exception as e:
                metrics.set_error(e)
                metrics.report("vault_statistics_failed")

                log_event(
                    "vault_statistics_collection_error",
                    {
                        "vault_path": str(self.vault_path),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )

                return {
                    "vault_path": str(self.vault_path),
                    "error": f"Failed to collect vault statistics: {e}",
                    "total_files": 0,
                    "total_size_bytes": 0,
                }

    def _get_content_path(self, file_hash: str, extension: str) -> Path:
        """
        Get the full storage path for a file based on its hash and extension.

        Args:
            file_hash: SHA256 hash of the file
            extension: File extension (without dot)

        Returns:
            Full path where file should be stored (e.g., content/ab/cd/efgh123.pdf)
        """
        return build_content_path(self.content_dir, file_hash, extension)

    def _get_thumbnail_path(self, file_hash: str) -> Path:
        """
        Get the storage path for a file's thumbnail image.

        Args:
            file_hash: SHA256 hash of the original file

        Returns:
            Path where thumbnail should be stored (e.g., thumbnails/ab/cd/efgh123_thumb.webp)
        """
        return build_thumbnail_path(self.thumbnails_dir, file_hash)

    @log_method(
        operation_name="file_hash_calculation", include_args=True, include_result=True
    )
    async def calculate_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of a file for content-addressed storage.

        Args:
            file_path: Path to the file to hash

        Returns:
            SHA256 hash as lowercase hexadecimal string

        Raises:
            FileNotFoundError: If file doesn't exist
            OSError: If file cannot be read
        """
        with log_context(
            operation="file_hash_calculation",
            file_path=str(file_path),
        ):
            metrics = MetricsCollector("file_hash_calculation")
            metrics.start()

            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            file_size = file_path.stat().st_size
            metrics.add_metric("file_size_bytes", file_size)
            metrics.add_metric("file_path", str(file_path))

            log_event(
                "file_hash_calculation_started",
                {
                    "file_path": str(file_path),
                    "file_size_bytes": file_size,
                },
            )

            try:
                file_hash = await calculate_file_hash(file_path)

                metrics.add_metric("hash_calculated", True)
                metrics.add_metric("hash_length", len(file_hash))
                metrics.set_success(True)
                metrics.report("file_hash_calculation_completed")

                log_event(
                    "file_hash_calculation_successful",
                    {
                        "file_path": str(file_path),
                        "file_size_bytes": file_size,
                        "hash": file_hash,
                        "hash_length": len(file_hash),
                    },
                )

                return file_hash

            except Exception as e:
                metrics.set_error(e)
                metrics.report("file_hash_calculation_failed")

                log_event(
                    "file_hash_calculation_error",
                    {
                        "file_path": str(file_path),
                        "file_size_bytes": file_size,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )
                raise

    @log_method(operation_name="file_storage", include_args=True, include_result=True)
    async def store_file(
        self, source_path: Path, file_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store a file in the vault using content-addressed storage.

        Copies the file to vault storage organized by its SHA256 hash. Automatically
        generates thumbnails for image files. If file already exists (same hash),
        returns existing file information without copying.

        Args:
            source_path: Path to the file to store
            file_hash: Pre-calculated SHA256 hash (optional, will calculate if not provided)

        Returns:
            Dictionary containing:
            - file_hash: SHA256 hash of the stored file
            - path: Full path where file is stored in vault
            - size_bytes: File size in bytes
            - existed: True if file already existed, False if newly stored

        Raises:
            FileNotFoundError: If source file doesn't exist
            RuntimeError: If vault directory creation or file copy fails
            OSError: If file operations fail
        """
        with log_context(
            operation="file_storage",
            source_path=str(source_path),
            has_precomputed_hash=file_hash is not None,
        ):
            metrics = MetricsCollector("file_storage")
            metrics.start()

            if not source_path.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")

            source_size = source_path.stat().st_size
            metrics.add_metric("source_file_size_bytes", source_size)
            metrics.add_metric("has_precomputed_hash", file_hash is not None)

            log_event(
                "file_storage_started",
                {
                    "source_path": str(source_path),
                    "source_file_size_bytes": source_size,
                    "has_precomputed_hash": file_hash is not None,
                },
            )

            try:
                # Calculate hash if not provided
                if file_hash is None:
                    log_event(
                        "hash_calculation_needed", {"source_path": str(source_path)}
                    )
                    file_hash = await self.calculate_hash(source_path)
                    metrics.add_metric("hash_calculated_internally", True)
                else:
                    metrics.add_metric("hash_calculated_internally", False)

                # Get file extension
                extension = source_path.suffix.lstrip(".")
                if not extension:
                    extension = "bin"
                    log_event(
                        "extension_defaulted_to_bin",
                        {
                            "source_path": str(source_path),
                            "original_suffix": source_path.suffix,
                        },
                    )

                metrics.add_metric("file_extension", extension)

                # Get storage path
                target_path = self._get_content_path(file_hash, extension)
                metrics.add_metric("target_path", str(target_path))

                log_event(
                    "storage_path_determined",
                    {
                        "file_hash": file_hash,
                        "extension": extension,
                        "target_path": str(target_path),
                    },
                )

                # Check if file already exists
                if target_path.exists():
                    size_bytes = safe_get_file_size(target_path)

                    metrics.add_metric("file_already_existed", True)
                    metrics.add_metric("existing_file_size_bytes", size_bytes)
                    metrics.set_success(True)
                    metrics.report("file_storage_completed")

                    log_event(
                        "file_storage_duplicate_found",
                        {
                            "file_hash": file_hash,
                            "target_path": str(target_path),
                            "size_bytes": size_bytes,
                        },
                    )

                    return {
                        "file_hash": file_hash,
                        "path": str(target_path),
                        "size_bytes": size_bytes,
                        "existed": True,
                    }

                # Create directory if needed
                try:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    log_event(
                        "vault_directory_ensured",
                        {"directory_path": str(target_path.parent)},
                    )
                except OSError as e:
                    metrics.set_error(e)
                    metrics.report("file_storage_failed")

                    log_event(
                        "vault_directory_creation_failed",
                        {
                            "directory_path": str(target_path.parent),
                            "error_message": str(e),
                        },
                    )
                    raise RuntimeError(
                        f"Failed to create vault directory {target_path.parent}: {e}"
                    ) from None

                # Copy file to vault
                try:
                    shutil.copy2(source_path, target_path)
                    metrics.add_metric("file_copied", True)

                    log_event(
                        "file_copied_to_vault",
                        {
                            "source_path": str(source_path),
                            "target_path": str(target_path),
                            "file_hash": file_hash,
                        },
                    )
                except (OSError, shutil.Error) as e:
                    metrics.set_error(e)
                    metrics.report("file_storage_failed")

                    log_event(
                        "file_copy_failed",
                        {
                            "source_path": str(source_path),
                            "target_path": str(target_path),
                            "error_message": str(e),
                        },
                    )
                    raise RuntimeError(f"Failed to copy file to vault: {e}") from None

                # Generate thumbnail for images
                log_event("thumbnail_generation_started", {"file_hash": file_hash})
                await self._generate_thumbnail(target_path, file_hash)
                metrics.add_metric("thumbnail_generation_attempted", True)

                # Get file size
                size_bytes = safe_get_file_size(target_path)
                metrics.add_metric("file_already_existed", False)
                metrics.add_metric("final_file_size_bytes", size_bytes)
                metrics.set_success(True)
                metrics.report("file_storage_completed")

                log_event(
                    "file_storage_successful",
                    {
                        "source_path": str(source_path),
                        "target_path": str(target_path),
                        "file_hash": file_hash,
                        "size_bytes": size_bytes,
                        "extension": extension,
                    },
                )

                return {
                    "file_hash": file_hash,
                    "path": str(target_path),
                    "size_bytes": size_bytes,
                    "existed": False,
                }

            except Exception as e:
                metrics.set_error(e)
                metrics.report("file_storage_failed")

                log_event(
                    "file_storage_error",
                    {
                        "source_path": str(source_path),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "file_hash": file_hash if file_hash else "not_calculated",
                    },
                )
                raise

    async def get_file_path(self, file_hash: str, extension: str) -> Optional[Path]:
        """
        Get the path to a stored file if it exists in the vault.

        Args:
            file_hash: SHA256 hash of the file
            extension: File extension (without dot)

        Returns:
            Path to the file if it exists, None otherwise
        """
        file_path = self._get_content_path(file_hash, extension)
        return file_path if file_path.exists() else None

    async def get_thumbnail_path(self, file_hash: str) -> Optional[Path]:
        """
        Get the path to a file's thumbnail image if it exists.

        Args:
            file_hash: SHA256 hash of the original file

        Returns:
            Path to the thumbnail file if it exists, None otherwise
        """
        thumbnail_path = self._get_thumbnail_path(file_hash)
        return thumbnail_path if thumbnail_path.exists() else None

    async def _generate_thumbnail(self, file_path: Path, file_hash: str):
        """
        Generate a thumbnail for an image file (internal method).

        Creates a 256x256 pixel WEBP thumbnail for supported image formats.
        Skips generation if thumbnail already exists or file is not an image.

        Args:
            file_path: Path to the original image file
            file_hash: SHA256 hash of the original file
        """
        thumbnail_path = self._get_thumbnail_path(file_hash)
        await generate_image_thumbnail(file_path, thumbnail_path)

    @log_method(operation_name="file_deletion", include_args=True, include_result=True)
    async def delete_file(self, file_hash: str, extension: str) -> bool:
        """
        Delete a file and its thumbnail from the vault.

        Removes both the content file and associated thumbnail (if any).

        Args:
            file_hash: SHA256 hash of the file to delete
            extension: File extension (without dot)

        Returns:
            True if content file was deleted, False if file didn't exist
            (thumbnail deletion doesn't affect return value)
        """
        with log_context(
            operation="file_deletion",
            file_hash=file_hash,
            extension=extension,
        ):
            metrics = MetricsCollector("file_deletion")
            metrics.start()

            file_path = self._get_content_path(file_hash, extension)
            thumbnail_path = self._get_thumbnail_path(file_hash)

            metrics.add_metric("file_hash", file_hash)
            metrics.add_metric("extension", extension)
            metrics.add_metric("content_file_path", str(file_path))
            metrics.add_metric("thumbnail_path", str(thumbnail_path))

            log_event(
                "file_deletion_started",
                {
                    "file_hash": file_hash,
                    "extension": extension,
                    "content_file_path": str(file_path),
                    "thumbnail_path": str(thumbnail_path),
                },
            )

            deleted = False
            content_existed = file_path.exists()
            thumbnail_existed = thumbnail_path.exists()

            metrics.add_metric("content_file_existed", content_existed)
            metrics.add_metric("thumbnail_existed", thumbnail_existed)

            # Delete content file
            if content_existed:
                try:
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted = True
                    metrics.add_metric("content_file_deleted", True)
                    metrics.add_metric("content_file_size_bytes", file_size)

                    log_event(
                        "content_file_deleted",
                        {
                            "file_hash": file_hash,
                            "file_path": str(file_path),
                            "file_size_bytes": file_size,
                        },
                    )
                except Exception as e:
                    metrics.add_metric("content_file_deleted", False)
                    log_event(
                        "content_file_deletion_failed",
                        {
                            "file_hash": file_hash,
                            "file_path": str(file_path),
                            "error_message": str(e),
                        },
                    )
            else:
                metrics.add_metric("content_file_deleted", False)

            # Delete thumbnail file
            if thumbnail_existed:
                try:
                    thumbnail_size = thumbnail_path.stat().st_size
                    thumbnail_path.unlink()
                    metrics.add_metric("thumbnail_deleted", True)
                    metrics.add_metric("thumbnail_size_bytes", thumbnail_size)

                    log_event(
                        "thumbnail_file_deleted",
                        {
                            "file_hash": file_hash,
                            "thumbnail_path": str(thumbnail_path),
                            "thumbnail_size_bytes": thumbnail_size,
                        },
                    )
                except Exception as e:
                    metrics.add_metric("thumbnail_deleted", False)
                    log_event(
                        "thumbnail_deletion_failed",
                        {
                            "file_hash": file_hash,
                            "thumbnail_path": str(thumbnail_path),
                            "error_message": str(e),
                        },
                    )
            else:
                metrics.add_metric("thumbnail_deleted", False)

            metrics.set_success(True)
            metrics.report("file_deletion_completed")

            log_event(
                "file_deletion_finished",
                {
                    "file_hash": file_hash,
                    "extension": extension,
                    "content_file_deleted": deleted,
                    "thumbnail_deleted": thumbnail_existed
                    and not thumbnail_path.exists(),
                    "any_files_existed": content_existed or thumbnail_existed,
                },
            )

            return deleted

    @log_method(
        operation_name="temp_file_cleanup", include_args=True, include_result=True
    )
    async def cleanup_temp(self):
        """
        Clean up temporary files older than 24 hours.

        Removes old temporary files to prevent the temp directory from growing
        indefinitely. Only affects files in the vault's temp directory.

        Returns:
            Dictionary containing cleanup metrics:
            - cleaned_files: Number of files removed
            - cleaned_bytes: Total bytes freed
            - errors: List of error messages for failed deletions
        """
        with log_context(
            operation="temp_file_cleanup",
            temp_directory=str(self.temp_dir),
        ):
            metrics = MetricsCollector("temp_file_cleanup")
            metrics.start()

            log_event(
                "temp_file_cleanup_started", {"temp_directory": str(self.temp_dir)}
            )

            try:
                cleanup_result = await cleanup_old_temp_files(self.temp_dir)

                # Extract metrics from cleanup result
                cleaned_files = cleanup_result.get("cleaned_files", 0)
                cleaned_bytes = cleanup_result.get("cleaned_bytes", 0)
                errors_count = len(cleanup_result.get("errors", []))

                metrics.add_metric("cleaned_files", cleaned_files)
                metrics.add_metric("cleaned_bytes", cleaned_bytes)
                metrics.add_metric("errors_count", errors_count)

                if errors_count > 0:
                    metrics.set_error(
                        RuntimeError(f"{errors_count} cleanup errors occurred")
                    )
                    metrics.report("temp_file_cleanup_completed_with_errors")
                else:
                    metrics.set_success(True)
                    metrics.report("temp_file_cleanup_completed")

                log_event(
                    "temp_file_cleanup_finished",
                    {
                        "temp_directory": str(self.temp_dir),
                        "cleaned_files": cleaned_files,
                        "cleaned_bytes": cleaned_bytes,
                        "cleaned_mb": (
                            round(cleaned_bytes / (1024 * 1024), 2)
                            if cleaned_bytes > 0
                            else 0
                        ),
                        "errors_count": errors_count,
                        "success": errors_count == 0,
                    },
                )

                return cleanup_result

            except Exception as e:
                metrics.set_error(e)
                metrics.report("temp_file_cleanup_failed")

                log_event(
                    "temp_file_cleanup_error",
                    {
                        "temp_directory": str(self.temp_dir),
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )
                raise
