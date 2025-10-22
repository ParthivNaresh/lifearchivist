"""
Data models for folder watching system.

These models define the structure for multi-folder watching configurations,
statistics, and runtime state management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver


class FolderWatchStatus(str, Enum):
    """Status of a watched folder."""

    ACTIVE = "active"  # Watching and processing files
    PAUSED = "paused"  # Temporarily disabled
    ERROR = "error"  # Experiencing errors
    STOPPED = "stopped"  # Not watching


class FolderHealthStatus(str, Enum):
    """Health status of a watched folder."""

    HEALTHY = "healthy"  # No issues
    DEGRADED = "degraded"  # Some errors but still functional
    UNHEALTHY = "unhealthy"  # Too many errors, auto-disabled
    UNREACHABLE = "unreachable"  # Folder no longer accessible


@dataclass
class FolderStats:
    """
    Statistics for a watched folder.

    Tracks all file processing metrics for monitoring and debugging.
    All counters are cumulative since folder was added.
    """

    # File processing counters
    files_detected: int = 0  # Total files detected by watchdog
    files_ingested: int = 0  # Successfully processed and indexed
    files_skipped: int = 0  # Skipped (duplicates)
    files_failed: int = 0  # Failed to process

    # Data metrics
    bytes_processed: int = 0  # Total bytes successfully processed

    # Timing
    last_activity: Optional[datetime] = None  # Last file event
    last_success: Optional[datetime] = None  # Last successful ingestion
    last_failure: Optional[datetime] = None  # Last failure

    # Error tracking
    error_count: int = 0  # Consecutive errors (resets on success)
    last_error: str = ""  # Last error message

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "files_detected": self.files_detected,
            "files_ingested": self.files_ingested,
            "files_skipped": self.files_skipped,
            "files_failed": self.files_failed,
            "bytes_processed": self.bytes_processed,
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "last_success": (
                self.last_success.isoformat() if self.last_success else None
            ),
            "last_failure": (
                self.last_failure.isoformat() if self.last_failure else None
            ),
            "error_count": self.error_count,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FolderStats":
        """Create from dictionary."""
        return cls(
            files_detected=data.get("files_detected", 0),
            files_ingested=data.get("files_ingested", 0),
            files_skipped=data.get("files_skipped", 0),
            files_failed=data.get("files_failed", 0),
            bytes_processed=data.get("bytes_processed", 0),
            last_activity=(
                datetime.fromisoformat(data["last_activity"])
                if data.get("last_activity")
                else None
            ),
            last_success=(
                datetime.fromisoformat(data["last_success"])
                if data.get("last_success")
                else None
            ),
            last_failure=(
                datetime.fromisoformat(data["last_failure"])
                if data.get("last_failure")
                else None
            ),
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error", ""),
        )

    def get_health_status(self) -> FolderHealthStatus:
        """
        Determine health status based on error metrics.

        Returns:
            Health status enum
        """
        if self.error_count >= 10:
            return FolderHealthStatus.UNHEALTHY
        elif self.error_count >= 5:
            return FolderHealthStatus.DEGRADED
        elif self.last_error:
            return FolderHealthStatus.DEGRADED
        else:
            return FolderHealthStatus.HEALTHY

    def get_success_rate(self) -> float:
        """
        Calculate success rate as percentage.

        Returns:
            Success rate 0.0-1.0
        """
        total = self.files_ingested + self.files_failed
        if total == 0:
            return 1.0
        return self.files_ingested / total


@dataclass
class WatchedFolder:
    """
    Runtime state for a watched folder.

    This dataclass holds both persistent configuration (from Redis)
    and runtime objects (Observer, Handler) that cannot be serialized.

    Lifecycle:
    1. Created when folder watching starts
    2. Observer and handler are active while enabled
    3. Destroyed when folder is removed or server stops
    """

    # Persistent configuration (stored in Redis)
    id: str  # UUID
    path: Union[str, Path]  # Absolute path to watched folder (accepts str or Path)
    enabled: bool  # Whether watching is active
    created_at: datetime  # When folder was added
    stats: FolderStats = field(default_factory=FolderStats)

    # Runtime state (not persisted)
    observer: Optional["BaseObserver"] = None  # Watchdog observer instance
    handler: Optional[Any] = None  # Event handler instance (DocumentEventHandler)
    status: FolderWatchStatus = FolderWatchStatus.STOPPED

    def __post_init__(self) -> None:
        """Ensure path is a Path object."""
        if not isinstance(self.path, Path):
            self.path = Path(self.path)

    def is_active(self) -> bool:
        """Check if folder is actively watching."""
        return (
            self.enabled
            and self.observer is not None
            and self.observer.is_alive()
            and self.status == FolderWatchStatus.ACTIVE
        )

    def is_healthy(self) -> bool:
        """Check if folder is in healthy state."""
        health = self.stats.get_health_status()
        return health in (FolderHealthStatus.HEALTHY, FolderHealthStatus.DEGRADED)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API responses.

        Excludes runtime objects (observer, handler).
        """
        return {
            "id": self.id,
            "path": str(self.path),
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "status": self.status.value,
            "health": self.stats.get_health_status().value,
            "stats": self.stats.to_dict(),
            "is_active": self.is_active(),
            "success_rate": self.stats.get_success_rate(),
        }


# Pydantic models for API requests/responses


class AddFolderRequest(BaseModel):
    """Request to add a watched folder."""

    folder_path: str = Field(
        description="Absolute path to folder to watch",
        examples=["/Users/username/Documents"],
    )
    enabled: bool = Field(
        default=True, description="Whether to start watching immediately"
    )


class UpdateFolderRequest(BaseModel):
    """Request to update a watched folder."""

    enabled: Optional[bool] = Field(
        default=None, description="Enable or disable watching"
    )


class FolderResponse(BaseModel):
    """Response containing folder information."""

    id: str = Field(description="Folder UUID")
    path: str = Field(description="Absolute folder path")
    enabled: bool = Field(description="Whether watching is enabled")
    created_at: str = Field(description="ISO timestamp when folder was added")
    status: str = Field(description="Current status (active/paused/error/stopped)")
    health: str = Field(description="Health status (healthy/degraded/unhealthy)")
    is_active: bool = Field(description="Whether actively watching")
    success_rate: float = Field(description="Success rate 0.0-1.0")
    stats: Dict[str, Any] = Field(description="Detailed statistics")


class FolderListResponse(BaseModel):
    """Response containing list of folders."""

    success: bool = Field(description="Whether request succeeded")
    folders: List[FolderResponse] = Field(description="List of watched folders")
    total: int = Field(description="Total number of folders")


class AggregateStatusResponse(BaseModel):
    """Aggregate status across all watched folders."""

    success: bool = Field(description="Whether request succeeded")
    total_folders: int = Field(description="Total watched folders")
    active_folders: int = Field(description="Currently active folders")
    total_pending: int = Field(description="Total pending files across all folders")
    total_detected: int = Field(description="Total files detected (all time)")
    total_ingested: int = Field(description="Total files ingested (all time)")
    total_failed: int = Field(description="Total files failed (all time)")
    total_bytes_processed: int = Field(description="Total bytes processed (all time)")
    folders: List[FolderResponse] = Field(description="Individual folder details")
    supported_extensions: List[str] = Field(description="Supported file extensions")
    ingestion_concurrency: int = Field(
        description="Max concurrent ingestions across all folders"
    )


class FolderScanResponse(BaseModel):
    """Response from manual folder scan."""

    success: bool = Field(description="Whether scan succeeded")
    folder_id: str = Field(description="Folder UUID")
    folder_path: str = Field(description="Folder path")
    files_found: int = Field(description="Number of files found")
    files_queued: int = Field(description="Number of files queued for ingestion")
    message: str = Field(description="Status message")


class FolderHealthCheckResponse(BaseModel):
    """Response from folder health check."""

    success: bool = Field(description="Whether check succeeded")
    folder_id: str = Field(description="Folder UUID")
    folder_path: str = Field(description="Folder path")
    accessible: bool = Field(description="Whether folder is accessible")
    exists: bool = Field(description="Whether folder exists")
    readable: bool = Field(description="Whether folder is readable")
    health: str = Field(description="Health status")
    error: Optional[str] = Field(default=None, description="Error message if any")
