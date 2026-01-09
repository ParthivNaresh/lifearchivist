from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class PhaseResult:
    phase_id: str
    completed: Dict[str, Any] = field(default_factory=dict)
    failed: Dict[str, str] = field(default_factory=dict)
    skipped: Dict[str, str] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return len(self.failed) == 0 and len(self.skipped) == 0

    @property
    def is_partial(self) -> bool:
        return len(self.completed) > 0 and not self.is_success

    @property
    def is_empty(self) -> bool:
        return (
            len(self.completed) == 0
            and len(self.failed) == 0
            and len(self.skipped) == 0
        )

    @property
    def total_tasks(self) -> int:
        return len(self.completed) + len(self.failed) + len(self.skipped)

    @property
    def completed_task_ids(self) -> List[str]:
        return list(self.completed.keys())

    @property
    def failed_task_ids(self) -> List[str]:
        return list(self.failed.keys())

    @property
    def skipped_task_ids(self) -> List[str]:
        return list(self.skipped.keys())

    def add_completed(self, task_id: str, result: Any) -> None:
        self.completed[task_id] = result

    def add_failed(self, task_id: str, error: str) -> None:
        self.failed[task_id] = error

    def add_skipped(self, task_id: str, reason: str) -> None:
        self.skipped[task_id] = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "is_success": self.is_success,
            "is_partial": self.is_partial,
            "total_tasks": self.total_tasks,
        }

    def to_synthesis_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}

        for task_id, data in self.completed.items():
            result[task_id] = data

        for task_id, error in self.failed.items():
            result[f"{task_id}_error"] = {"status": "failed", "error": error}

        for task_id, reason in self.skipped.items():
            result[f"{task_id}_skipped"] = {"status": "skipped", "reason": reason}

        return result
