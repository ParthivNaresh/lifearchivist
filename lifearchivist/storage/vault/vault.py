"""
File vault for content-addressed storage.
"""

import logging
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
from lifearchivist.utils.logging import log_event, track


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

    @track(
        operation="vault_initialization",
        track_performance=True,
        frequency="low_frequency",
    )
    async def initialize(self):
        """
        Create vault directory structure if it doesn't exist.

        Creates all necessary subdirectories for content, thumbnails, temp files,
        and exports. Safe to call multiple times.

        Raises:
            OSError: If directory creation fails due to permissions or disk space
        """
        directories = [
            ("vault", self.vault_path),
            ("content", self.content_dir),
            ("thumbnails", self.thumbnails_dir),
            ("temp", self.temp_dir),
            ("exports", self.exports_dir),
        ]

        log_event(
            "vault_init_started",
            {
                "vault_path": str(self.vault_path),
                "directories_to_create": len(directories),
            },
        )

        created_count = 0
        existing_count = 0

        for dir_name, directory in directories:
            try:
                existed_before = directory.exists()
                directory.mkdir(parents=True, exist_ok=True)

                if not existed_before:
                    created_count += 1
                    log_event(
                        "vault_directory_created",
                        {
                            "directory_name": dir_name,
                            "path": str(directory),
                        },
                        level=logging.DEBUG,
                    )
                else:
                    existing_count += 1

            except OSError as e:
                log_event(
                    "vault_directory_creation_failed",
                    {
                        "directory_name": dir_name,
                        "path": str(directory),
                        "error": str(e),
                    },
                    level=logging.ERROR,
                )
                raise OSError(
                    f"Failed to create vault directory {directory}: {e}"
                ) from None

        log_event(
            "vault_initialized",
            {
                "vault_path": str(self.vault_path),
                "directories_created": created_count,
                "directories_existing": existing_count,
            },
        )

    @track(
        operation="vault_file_clearing",
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
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
        cleared_metrics: Dict[str, Any] = {
            "files_deleted": 0,
            "bytes_reclaimed": 0,
            "directories_cleaned": 0,
            "orphaned_files_deleted": 0,
            "orphaned_bytes_reclaimed": 0,
            "errors": [],
        }

        # Log clearing operation start
        log_event(
            "vault_clearing_started",
            {
                "mode": "specific_hashes" if file_hashes else "clear_all",
                "hash_count": len(file_hashes) if file_hashes else 0,
            },
        )

        # Clear files by specific hashes
        for file_hash in file_hashes:
            try:
                await self._delete_file_by_hash(file_hash, cleared_metrics)
            except Exception as e:
                error_msg = f"Failed to delete files for hash {file_hash}: {e}"
                if isinstance(cleared_metrics["errors"], list):
                    cleared_metrics["errors"].append(error_msg)
                log_event(
                    "vault_file_deletion_failed",
                    {
                        "file_hash": file_hash[:8],
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )

        # If no file hashes provided or we need comprehensive cleanup, clear all files
        if not file_hashes:
            await self._clear_all_vault_files(cleared_metrics)

        # Clean up empty directories
        dirs_cleaned = await self._cleanup_empty_directories()
        cleared_metrics["directories_cleaned"] = dirs_cleaned

        # Log clearing results
        log_event(
            "vault_clearing_completed",
            {
                "files_deleted": cleared_metrics["files_deleted"],
                "mb_reclaimed": round(
                    cleared_metrics["bytes_reclaimed"] / (1024 * 1024), 2
                ),
                "directories_cleaned": cleared_metrics["directories_cleaned"],
                "errors_count": len(cleared_metrics.get("errors", [])),
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
            # Use empty prefix for main vault clearing (not "orphaned_")
            await clear_directory_files(directory, metrics, None, "")

    async def delete_file_by_hash(self, file_hash: str, metrics: Dict[str, Any]):
        """
        Delete all files (content and thumbnails) associated with a specific hash.

        Public method for deleting files by their hash value.

        Args:
            file_hash: SHA256 hash of the file to delete
            metrics: Dictionary to update with deletion statistics
        """
        await self._delete_file_by_hash(file_hash, metrics)

    async def _delete_file_by_hash(self, file_hash: str, metrics: Dict[str, Any]):
        """
        Delete all files (content and thumbnails) associated with a specific hash.

        Internal implementation for file deletion.

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

    async def _cleanup_empty_directories(self) -> int:
        """
        Remove empty directories from vault structure while preserving base directories.

        Recursively removes empty subdirectories but keeps the main vault directories
        (content, thumbnails, temp, exports) intact.

        Returns:
            Number of directories cleaned up
        """
        directories_to_check = [self.content_dir, self.thumbnails_dir, self.temp_dir]
        preserve_dirs = [
            self.vault_path,
            self.content_dir,
            self.thumbnails_dir,
            self.temp_dir,
            self.exports_dir,
        ]

        total_cleaned = 0
        for base_dir in directories_to_check:
            cleaned = await cleanup_empty_directories(base_dir, preserve_dirs)
            cleaned = int(cleaned or 0)
            total_cleaned += cleaned

        if total_cleaned > 0:
            log_event(
                "vault_directories_cleaned",
                {
                    "directories_removed": total_cleaned,
                },
                level=logging.DEBUG,
            )

        return total_cleaned

    @track(
        operation="vault_statistics",
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
    async def get_vault_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about vault storage usage.

        Returns:
            Dictionary containing storage metrics:
            - vault_path: Absolute path to vault root directory
            - directories: Nested structure with per-directory stats
            - total_files: Total number of files across all directories
            - total_size_bytes: Total storage used in bytes
            - total_size_mb: Total storage used in megabytes
            - error: Error message if statistics collection fails
        """
        try:
            log_event(
                "vault_stats_collection_started",
                {
                    "vault_path": str(self.vault_path),
                },
                level=logging.DEBUG,
            )

            directories = {
                "content": self.content_dir,
                "thumbnails": self.thumbnails_dir,  # Note: UI expects "thumbnails", not "thumbnail"
                "temp": self.temp_dir,
                "exports": self.exports_dir,
            }

            flat_stats = await get_comprehensive_directory_stats(directories)

            # Transform flat structure to nested structure expected by UI
            nested_directories = {}
            for dir_name in directories.keys():
                nested_directories[dir_name] = {
                    "file_count": flat_stats.get(f"{dir_name}_files", 0),
                    "total_size_bytes": flat_stats.get(f"{dir_name}_size_bytes", 0),
                    "total_size_mb": flat_stats.get(f"{dir_name}_size_mb", 0.0),
                }

            total_files = flat_stats.get("total_files", 0)
            total_mb = flat_stats.get("total_size_mb", 0.0)

            log_event(
                "vault_stats_collected",
                {
                    "total_files": total_files,
                    "total_size_mb": round(total_mb, 2),
                    "content_files": flat_stats.get("content_files", 0),
                    "thumbnail_files": flat_stats.get("thumbnails_files", 0),
                    "temp_files": flat_stats.get("temp_files", 0),
                },
            )

            return {
                "vault_path": str(self.vault_path),
                "directories": nested_directories,
                "total_files": total_files,
                "total_size_bytes": flat_stats.get("total_size_bytes", 0),
                "total_size_mb": total_mb,
            }

        except Exception as e:
            log_event(
                "vault_stats_collection_failed",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                level=logging.ERROR,
            )
            return {
                "vault_path": str(self.vault_path),
                "directories": {},
                "error": f"Failed to collect vault statistics: {e}",
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0.0,
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

    @track(
        operation="file_hash_calculation",
        track_performance=True,
        frequency="high_frequency",
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
        if not file_path.exists():
            log_event(
                "hash_calculation_failed",
                {
                    "file_path": str(file_path),
                    "reason": "file_not_found",
                },
                level=logging.WARNING,
            )
            raise FileNotFoundError(f"File not found: {file_path}")

        file_size = file_path.stat().st_size
        log_event(
            "hash_calculation_started",
            {
                "file_name": file_path.name,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
            },
            level=logging.DEBUG,
        )

        file_hash = await calculate_file_hash(file_path)

        log_event(
            "hash_calculated",
            {
                "file_name": file_path.name,
                "hash": file_hash[:8],
            },
            level=logging.DEBUG,
        )

        return file_hash

    @track(
        operation="file_storage",
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
    )
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
        if not source_path.exists():
            log_event(
                "vault_store_failed",
                {
                    "source_path": str(source_path),
                    "reason": "source_not_found",
                },
                level=logging.ERROR,
            )
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Calculate hash if not provided
        if file_hash is None:
            file_hash = await self.calculate_hash(source_path)

        # Get file extension
        extension = source_path.suffix.lstrip(".")
        if not extension:
            extension = "bin"

        # Get storage path
        target_path = self._get_content_path(file_hash, extension)

        # Check if file already exists
        if target_path.exists():
            size_bytes = safe_get_file_size(target_path)
            log_event(
                "vault_file_exists",
                {
                    "file_hash": file_hash[:8],
                    "extension": extension,
                    "size_bytes": size_bytes,
                },
                level=logging.DEBUG,
            )
            return {
                "file_hash": file_hash,
                "path": str(target_path),
                "size_bytes": size_bytes,
                "existed": True,
            }

        # Log new file storage
        source_size = source_path.stat().st_size
        log_event(
            "vault_storing_file",
            {
                "source_name": source_path.name,
                "file_hash": file_hash[:8],
                "extension": extension,
                "size_mb": round(source_size / (1024 * 1024), 2),
            },
        )

        # Create directory if needed
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log_event(
                "vault_directory_creation_failed",
                {
                    "directory": str(target_path.parent),
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            raise RuntimeError(
                f"Failed to create vault directory {target_path.parent}: {e}"
            ) from None

        # Copy file to vault
        try:
            shutil.copy2(source_path, target_path)
        except (OSError, shutil.Error) as e:
            log_event(
                "vault_file_copy_failed",
                {
                    "source": str(source_path),
                    "target": str(target_path),
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            raise RuntimeError(f"Failed to copy file to vault: {e}") from None

        # Generate thumbnail for images
        thumbnail_generated = await self._generate_thumbnail(target_path, file_hash)

        # Get file size
        size_bytes = safe_get_file_size(target_path)

        log_event(
            "vault_file_stored",
            {
                "file_hash": file_hash[:8],
                "extension": extension,
                "size_bytes": size_bytes,
                "thumbnail_generated": thumbnail_generated,
            },
        )

        return {
            "file_hash": file_hash,
            "path": str(target_path),
            "size_bytes": size_bytes,
            "existed": False,
        }

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

    async def _generate_thumbnail(self, file_path: Path, file_hash: str) -> bool:
        """
        Generate a thumbnail for an image file (internal method).

        Creates a 256x256 pixel WEBP thumbnail for supported image formats.
        Skips generation if thumbnail already exists or file is not an image.

        Args:
            file_path: Path to the original image file
            file_hash: SHA256 hash of the original file

        Returns:
            True if thumbnail was generated, False otherwise
        """
        thumbnail_path = self._get_thumbnail_path(file_hash)
        generated = await generate_image_thumbnail(file_path, thumbnail_path)

        if generated:
            log_event(
                "thumbnail_generated",
                {
                    "file_hash": file_hash[:8],
                    "thumbnail_path": str(thumbnail_path),
                },
                level=logging.DEBUG,
            )

        return generated

    @track(
        operation="file_deletion",
        include_args=["extension"],
        include_result=True,
        track_performance=True,
        frequency="medium_frequency",
    )
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
        file_path = self._get_content_path(file_hash, extension)
        thumbnail_path = self._get_thumbnail_path(file_hash)

        deleted = False
        content_existed = file_path.exists()
        thumbnail_existed = thumbnail_path.exists()
        content_size = safe_get_file_size(file_path) if content_existed else 0
        thumbnail_size = safe_get_file_size(thumbnail_path) if thumbnail_existed else 0

        # Delete content file
        if content_existed:
            try:
                file_path.unlink()
                deleted = True
                log_event(
                    "vault_content_deleted",
                    {
                        "file_hash": file_hash[:8],
                        "extension": extension,
                        "size_bytes": content_size,
                    },
                    level=logging.DEBUG,
                )
            except Exception as e:
                log_event(
                    "vault_content_deletion_failed",
                    {
                        "file_hash": file_hash[:8],
                        "error": str(e),
                    },
                    level=logging.WARNING,
                )

        # Delete thumbnail file
        if thumbnail_existed:
            try:
                thumbnail_path.unlink()
                log_event(
                    "vault_thumbnail_deleted",
                    {
                        "file_hash": file_hash[:8],
                        "size_bytes": thumbnail_size,
                    },
                    level=logging.DEBUG,
                )
            except Exception as e:
                log_event(
                    "vault_thumbnail_deletion_failed",
                    {
                        "file_hash": file_hash[:8],
                        "error": str(e),
                    },
                    level=logging.DEBUG,
                )

        if deleted:
            total_reclaimed = content_size + thumbnail_size
            log_event(
                "vault_file_deleted",
                {
                    "file_hash": file_hash[:8],
                    "extension": extension,
                    "bytes_reclaimed": total_reclaimed,
                    "had_thumbnail": thumbnail_existed,
                },
            )
        elif not content_existed:
            log_event(
                "vault_file_not_found",
                {
                    "file_hash": file_hash[:8],
                    "extension": extension,
                },
                level=logging.DEBUG,
            )

        return deleted

    @track(
        operation="temp_file_cleanup",
        include_result=True,
        track_performance=True,
        frequency="low_frequency",
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
        log_event(
            "temp_cleanup_started",
            {
                "temp_dir": str(self.temp_dir),
            },
            level=logging.DEBUG,
        )

        cleanup_result = await cleanup_old_temp_files(self.temp_dir)

        if cleanup_result.get("cleaned_files", 0) > 0:
            log_event(
                "temp_cleanup_completed",
                {
                    "files_cleaned": cleanup_result.get("cleaned_files", 0),
                    "mb_reclaimed": round(
                        cleanup_result.get("cleaned_bytes", 0) / (1024 * 1024), 2
                    ),
                    "errors_count": len(cleanup_result.get("errors", [])),
                },
            )
        else:
            log_event(
                "temp_cleanup_nothing_to_clean",
                {
                    "temp_dir": str(self.temp_dir),
                },
                level=logging.DEBUG,
            )

        return cleanup_result
