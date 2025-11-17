from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(slots=True)
class AgentTask:
    tool_name: str
    description: str
    requires_llm: bool
    parameters: Dict[str, Any]
    task_id: str
    depends_on: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.depends_on:
            self.depends_on = list(dict.fromkeys(self.depends_on))

    def is_ready(self, completed: set[str]) -> bool:
        return all(dep in completed for dep in self.depends_on)

    def missing_deps(self, done: set[str]) -> List[str]:
        return [dep for dep in self.depends_on if dep not in done]

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "tool_name": self.tool_name,
            "description": self.description,
            "requires_llm": bool(self.requires_llm),
            "parameters": self.parameters,
            "depends_on": list(self.depends_on),
        }


@dataclass(slots=True)
class ExecutionPlan:
    tasks: List[AgentTask]
    estimated_time_seconds: int
    estimated_cost_usd: float
    reasoning: str
    _by_id: Dict[str, "AgentTask"] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self._by_id = {t.task_id: t for t in self.tasks}

    def task_by_id(self, task_id: str) -> AgentTask:
        return self._by_id[task_id]

    def get_executable_tasks(self, completed: set[str]) -> List[AgentTask]:
        ready = [t for t in self.tasks if t.is_ready(completed)]
        # Deterministic ordering (swap with heuristic if desired)
        return sorted(ready, key=lambda t: t.task_id)

    def to_dict(self) -> dict:
        return {
            "estimated_time_seconds": self.estimated_time_seconds,
            "estimated_cost_usd": self.estimated_cost_usd,
            "reasoning": self.reasoning,
            "tasks": [t.to_dict() for t in self.tasks],
        }
