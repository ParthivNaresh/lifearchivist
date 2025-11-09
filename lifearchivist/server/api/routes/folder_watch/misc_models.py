from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional

if TYPE_CHECKING:
    from watchdog.observers.api import BaseObserver


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


class FolderWatchStatus(str, Enum):
    """Status of a watched folder."""

    ACTIVE = "active"  # Watching and processing files
    PAUSED = "paused"  # Temporarily disabled
    ERROR = "error"  # Experiencing errors
    STOPPED = "stopped"  # Not watching


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
    path: str | Path  # Absolute path to watched folder (accepts str or Path)
    enabled: bool  # Whether watching is active
    created_at: datetime  # When folder was added
    stats: FolderStats = field(default_factory=FolderStats)

    # Runtime state (not persisted)
    observer: Optional["BaseObserver"] = None
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
