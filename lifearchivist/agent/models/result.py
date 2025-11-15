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
