import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Optional


class AgentEventType(Enum):
    COMPLEXITY_CLASSIFIED = "complexity_classified"
    PLAN_CREATED = "plan_created"
    PLAN_VALIDATED = "plan_validated"
    PHASE_COMPLETED = "phase_completed"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_SKIPPED = "task_skipped"
    SYNTHESIS_STARTED = "synthesis_started"
    RESPONSE_CHUNK = "response_chunk"
    PLAN_COMPLETED = "plan_completed"
    PLAN_FAILED = "plan_failed"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass(slots=True)
class AgentEvent:
    type: AgentEventType
    data: Mapping[str, Any] | None = None
    task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    monotonic_ns: int = field(default_factory=time.perf_counter_ns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "monotonic_ns": self.monotonic_ns,
            "data": self._json_safe(self.data),
        }

    @staticmethod
    def _json_safe(obj: Any) -> Any:
        try:
            if obj is None:
                return None
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, Mapping):
                return {k: AgentEvent._json_safe(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [AgentEvent._json_safe(v) for v in obj]
            return repr(obj)
        except Exception:
            return repr(obj)

    @classmethod
    def error(cls, message: str) -> "AgentEvent":
        return cls(type=AgentEventType.ERROR, data={"error": message})

    @classmethod
    def complete(cls) -> "AgentEvent":
        return cls(type=AgentEventType.COMPLETE, data={})

    @classmethod
    def synthesis_started(cls) -> "AgentEvent":
        return cls(type=AgentEventType.SYNTHESIS_STARTED, data={})

    @classmethod
    def response_chunk(cls, chunk: str) -> "AgentEvent":
        return cls(type=AgentEventType.RESPONSE_CHUNK, data={"text": chunk})

    @classmethod
    def task_started(cls, task) -> "AgentEvent":
        return cls(
            type=AgentEventType.TASK_STARTED,
            data={"task_id": task.task_id, "tool": getattr(task, "tool_name", None)},
            task_id=task.task_id,
        )

    @classmethod
    def task_completed(cls, task, result: Any) -> "AgentEvent":
        return cls(
            type=AgentEventType.TASK_COMPLETED, data=result, task_id=task.task_id
        )

    @classmethod
    def task_failed(cls, task, error: str) -> "AgentEvent":
        return cls(
            type=AgentEventType.TASK_FAILED,
            data={"error": error},
            task_id=task.task_id,
        )

    @classmethod
    def task_skipped(cls, task, reason: str) -> "AgentEvent":
        return cls(
            type=AgentEventType.TASK_SKIPPED,
            data={"reason": reason},
            task_id=task.task_id,
        )

    @classmethod
    def plan_completed(cls, results: dict[str, Any]) -> "AgentEvent":
        return cls(type=AgentEventType.PLAN_COMPLETED, data={"results": results})

    @classmethod
    def plan_failed(cls, message: str) -> "AgentEvent":
        return cls(type=AgentEventType.PLAN_FAILED, data={"error": message})

    @classmethod
    def complexity_classified(cls, classification: Any) -> "AgentEvent":
        return cls(type=AgentEventType.COMPLEXITY_CLASSIFIED, data=classification)

    @classmethod
    def phase_completed(cls, phase_id: str) -> "AgentEvent":
        return cls(type=AgentEventType.PHASE_COMPLETED, data={"phase_id": phase_id})
