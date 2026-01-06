from dataclasses import dataclass
from typing import Any, Optional


@dataclass(slots=True)
class ResultEnvelope:
    task_id: str
    status: str  # "ok" | "error" | "cancelled"
    value: Any | None = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    attempts: int = 1
    duration_ms: int = 0

    @classmethod
    def ok(
        cls, task_id: str, value: Any, *, attempts: int = 1, duration_ms: int = 0
    ) -> "ResultEnvelope":
        return cls(
            task_id=task_id,
            status="ok",
            value=value,
            attempts=attempts,
            duration_ms=duration_ms,
        )

    @classmethod
    def error(
        cls, task_id: str, exc_or_msg: Any, *, attempts: int = 1, duration_ms: int = 0
    ) -> "ResultEnvelope":
        if isinstance(exc_or_msg, BaseException):
            return cls(
                task_id=task_id,
                status="error",
                error_type=type(exc_or_msg).__name__,
                error_message=str(exc_or_msg),
                attempts=attempts,
                duration_ms=duration_ms,
            )
        return cls(
            task_id=task_id,
            status="error",
            error_type="Error",
            error_message=str(exc_or_msg),
            attempts=attempts,
            duration_ms=duration_ms,
        )

    @classmethod
    def cancelled(
        cls, task_id: str, *, attempts: int = 1, duration_ms: int = 0
    ) -> "ResultEnvelope":
        return cls(
            task_id=task_id,
            status="cancelled",
            attempts=attempts,
            duration_ms=duration_ms,
        )

    def is_ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "value": self.value,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "attempts": self.attempts,
            "duration_ms": self.duration_ms,
        }
