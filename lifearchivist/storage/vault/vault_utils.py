"""
Utility functions for vault operations.
"""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from PIL import Image


def get_hash_path_components(file_hash: str) -> tuple[str, str, str]:
    """Extract hash components for directory structure."""
    hash_prefix = file_hash[:2]
    hash_second_level = file_hash[2:4]
    hash_suffix = file_hash[4:]
    return hash_prefix, hash_second_level, hash_suffix


def build_content_path(base_dir: Path, file_hash: str, extension: str) -> Path:
    """Build content file path from hash and extension."""
    hash_prefix, hash_second_level, hash_suffix = get_hash_path_components(file_hash)
    return base_dir / hash_prefix / hash_second_level / f"{hash_suffix}.{extension}"


def build_thumbnail_path(base_dir: Path, file_hash: str) -> Path:
    """Build thumbnail path from hash."""
    hash_prefix, hash_second_level, hash_suffix = get_hash_path_components(file_hash)
    return base_dir / hash_prefix / hash_second_level / f"{hash_suffix}_thumb.webp"


def build_content_directory(base_dir: Path, file_hash: str) -> Path:
    """Build content directory path from hash."""
    hash_prefix, hash_second_level, _ = get_hash_path_components(file_hash)
    return base_dir / hash_prefix / hash_second_level


def is_image_file(file_path: Path) -> bool:
    """Check if file is a supported image format."""
    return file_path.suffix.lower() in {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".tiff",
        ".webp",
    }


async def calculate_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of a file."""
    hash_sha256 = hashlib.sha256()

    async with aiofiles.open(file_path, "rb") as f:
        while chunk := await f.read(8192):
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()


async def safe_file_operation(
    operation_func, *args, **kwargs
) -> tuple[bool, Optional[Exception]]:
    """Safely execute a file operation and return success status and any exception."""
    try:
        (
            await operation_func(*args, **kwargs)
            if callable(operation_func)
            else operation_func(*args, **kwargs)
        )
        return True, None
    except Exception as e:
        return False, e


def safe_get_file_size(file_path: Path) -> int:
    """Safely get file size, returning 0 if operation fails."""
    try:
        return file_path.stat().st_size
    except OSError:
        return 0


async def count_directory_files(directory: Path) -> Dict[str, int]:
    """Count files and calculate total size in a directory."""
    stats = {"files": 0, "bytes": 0}

    if not directory.exists():
        return stats

    for file_path in directory.rglob("*"):
        if file_path.is_file():
            stats["files"] += 1
            stats["bytes"] += safe_get_file_size(file_path)

    return stats


async def delete_file_safely(
    file_path: Path, metrics: Dict[str, Any], metric_prefix: str = ""
):
    """Safely delete a file and update metrics."""
    if not file_path.exists():
        return

    try:
        file_size = safe_get_file_size(file_path)
        file_path.unlink()

        files_key = (
            f"{metric_prefix}files_deleted" if metric_prefix else "files_deleted"
        )
        bytes_key = (
            f"{metric_prefix}bytes_reclaimed" if metric_prefix else "bytes_reclaimed"
        )

        metrics[files_key] = metrics.get(files_key, 0) + 1
        metrics[bytes_key] = metrics.get(bytes_key, 0) + file_size

    except Exception as e:
        error_msg = f"Failed to delete {file_path}: {e}"
        metrics.setdefault("errors", []).append(error_msg)


async def clear_directory_files(
    directory: Path, metrics: Dict[str, Any], exclude_files: Optional[List[str]] = None, metric_prefix: str = ""
):
    """Clear all files in a directory, updating metrics."""
    if not directory.exists():
        return

    exclude_files = exclude_files or [".DS_Store"]

    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.name not in exclude_files:
            await delete_file_safely(file_path, metrics, metric_prefix)


async def cleanup_empty_directories(
    directory: Path, preserve_dirs: Optional[List[Path]] = None
):
    """Recursively remove empty subdirectories."""
    if not directory.exists() or not directory.is_dir():
        return

    preserve_dirs = preserve_dirs or []

    # Process subdirectories first (bottom-up)
    for subdir in directory.iterdir():
        if subdir.is_dir():
            await cleanup_empty_directories(subdir, preserve_dirs)

    # Check if current directory is empty and not in preserve list
    if directory not in preserve_dirs:
        try:
            if not any(directory.iterdir()):  # Directory is empty
                directory.rmdir()
        except OSError:
            # Directory not empty or other OS error
            pass


async def generate_image_thumbnail(
    source_path: Path,
    thumbnail_path: Path,
    size: tuple[int, int] = (256, 256),
    quality: int = 80,
) -> bool:
    """Generate a thumbnail for an image file."""
    if not is_image_file(source_path):
        return False

    # Skip if thumbnail already exists
    if thumbnail_path.exists():
        return True

    try:
        # Create thumbnail directory
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

        with Image.open(source_path) as img:
            # Convert to RGB if necessary
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGB")

            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, "WEBP", quality=quality, optimize=True)

        return True

    except Exception:
        # Clean up partial thumbnail file if it exists
        if thumbnail_path.exists():
            try:
                thumbnail_path.unlink()
            except OSError:
                pass
        return False


def bytes_to_mb(bytes_value: int) -> float:
    """Convert bytes to megabytes with 2 decimal places."""
    return round(bytes_value / (1024 * 1024), 2)


async def cleanup_old_temp_files(temp_dir: Path, hours_old: int = 24) -> Dict[str, Any]:
    """Clean up temporary files older than specified hours."""
    if not temp_dir.exists():
        return {"cleaned_files": 0, "cleaned_bytes": 0, "errors": []}

    cutoff_time = datetime.now().timestamp() - (hours_old * 60 * 60)
    cleaned_files = 0
    cleaned_bytes = 0
    errors = []

    try:
        for temp_file in temp_dir.rglob("*"):
            if temp_file.is_file():
                try:
                    file_stat = temp_file.stat()
                    if file_stat.st_mtime < cutoff_time:
                        file_size = file_stat.st_size
                        temp_file.unlink()
                        cleaned_files += 1
                        cleaned_bytes += file_size
                except OSError as e:
                    error_msg = f"Failed to clean temp file {temp_file}: {e}"
                    errors.append(error_msg)

        return {
            "cleaned_files": cleaned_files,
            "cleaned_bytes": cleaned_bytes,
            "errors": errors,
        }

    except Exception as e:
        return {"cleaned_files": 0, "cleaned_bytes": 0, "errors": [str(e)]}


def find_files_by_hash_pattern(directory: Path, file_hash: str) -> List[Path]:
    """Find all files matching a hash pattern in a directory."""
    if not directory.exists():
        return []

    hash_suffix = file_hash[2:]  # Remove first 2 chars used for directory structure
    matching_files = []

    for file_path in directory.glob(f"{hash_suffix}.*"):
        if file_path.is_file():
            matching_files.append(file_path)

    return matching_files


async def get_comprehensive_directory_stats(
    directories: Dict[str, Path],
) -> Dict[str, Any]:
    """Get comprehensive statistics for multiple directories."""
    stats: Dict[str, Any] = {
        "total_files": 0,
        "total_size_bytes": 0,
        "total_size_mb": 0.0,
    }

    try:
        for dir_name, directory in directories.items():
            dir_stats = await count_directory_files(directory)

            # Add individual directory stats
            stats[f"{dir_name}_files"] = dir_stats["files"]
            stats[f"{dir_name}_size_bytes"] = dir_stats["bytes"]
            stats[f"{dir_name}_size_mb"] = bytes_to_mb(dir_stats["bytes"])

            # Add to totals
            stats["total_files"] += dir_stats["files"]
            stats["total_size_bytes"] += dir_stats["bytes"]

        stats["total_size_mb"] = bytes_to_mb(int(stats["total_size_bytes"]))

    except Exception as e:
        stats["error"] = str(e)
        stats["total_size_mb"] = 0.0

    return stats
