from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from .query import ComplexityClassification
from .task import AgentTask, ExecutionPlan


class AgentEventType(Enum):
    COMPLEXITY_CLASSIFIED = "complexity_classified"
    PLAN_CREATED = "plan_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_SPAWNED = "agent_spawned"
    SYNTHESIS_STARTED = "synthesis_started"
    RESPONSE_CHUNK = "response_chunk"
    COMPLETE = "complete"
    ERROR = "error"
    TASK_SKIPPED = "task_skipped"
    PLAN_COMPLETED = "plan_completed"
    PLAN_FAILED = "plan_failed"


@dataclass
class AgentEvent:
    type: AgentEventType
    data: Any
    timestamp: datetime = field(default_factory=datetime.now)
    task_id: Optional[str] = None

    @classmethod
    def complexity_classified(
        cls, classification: ComplexityClassification
    ) -> "AgentEvent":
        return cls(type=AgentEventType.COMPLEXITY_CLASSIFIED, data=classification)

    @classmethod
    def plan_created(cls, plan: ExecutionPlan) -> "AgentEvent":
        return cls(type=AgentEventType.PLAN_CREATED, data=plan)

    @classmethod
    def task_started(cls, task: AgentTask) -> "AgentEvent":
        return cls(
            type=AgentEventType.TASK_STARTED,
            data={"task_id": task.task_id, "tool": task.tool_name},
            task_id=task.task_id,
        )

    @classmethod
    def task_completed(cls, task: AgentTask, result: Any) -> "AgentEvent":
        return cls(
            type=AgentEventType.TASK_COMPLETED, data=result, task_id=task.task_id
        )

    @classmethod
    def task_failed(cls, task: AgentTask, error: str) -> "AgentEvent":
        return cls(
            type=AgentEventType.TASK_FAILED, data={"error": error}, task_id=task.task_id
        )

    @classmethod
    def synthesis_started(cls) -> "AgentEvent":
        return cls(type=AgentEventType.SYNTHESIS_STARTED, data={})

    @classmethod
    def response_chunk(cls, chunk: str) -> "AgentEvent":
        return cls(type=AgentEventType.RESPONSE_CHUNK, data=chunk)

    @classmethod
    def complete(cls) -> "AgentEvent":
        return cls(type=AgentEventType.COMPLETE, data={})

    @classmethod
    def error(cls, error_message: str) -> "AgentEvent":
        return cls(type=AgentEventType.ERROR, data={"error": error_message})

    @classmethod
    def task_skipped(cls, task: AgentTask, reason: str) -> "AgentEvent":
        return cls(
            type=AgentEventType.TASK_SKIPPED,
            data={"reason": reason},
            task_id=task.task_id,
        )

    @classmethod
    def plan_completed(cls, results: dict[str, Any]) -> "AgentEvent":
        # keep results wrapped for extensibility
        return cls(type=AgentEventType.PLAN_COMPLETED, data={"results": results})

    @classmethod
    def plan_failed(cls, message: str) -> "AgentEvent":
        return cls(type=AgentEventType.PLAN_FAILED, data={"error": message})
