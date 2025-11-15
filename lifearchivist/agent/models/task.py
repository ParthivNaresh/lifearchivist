from dataclasses import dataclass, field
from typing import Any, Dict, List
from uuid import uuid4


@dataclass
class AgentTask:
    tool_name: str
    description: str
    requires_llm: bool
    parameters: Dict[str, Any]
    depends_on: List[str] = field(default_factory=list)
    task_id: str = field(default_factory=lambda: str(uuid4()))

    def is_ready(self, completed_tasks: set[str]) -> bool:
        return all(dep in completed_tasks for dep in self.depends_on)

    def missing_deps(self, completed: set[str]) -> List[str]:
        """List any unmet dependencies."""
        return [dep for dep in self.depends_on if dep not in completed]


@dataclass
class ExecutionPlan:
    tasks: List[AgentTask]
    estimated_time_seconds: int
    estimated_cost_usd: float
    reasoning: str

    def __post_init__(self):
        self._by_id = {t.task_id: t for t in self.tasks}

    def task_by_id(self, task_id: str) -> AgentTask:
        return self._by_id[task_id]

    def get_executable_tasks(self, completed: set[str]) -> List[AgentTask]:
        ready = [t for t in self.tasks if t.is_ready(completed)]
        return sorted(ready, key=lambda t: t.task_id)
