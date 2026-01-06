from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class PhaseComplexity(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass(slots=True)
class StrategicPhase:
    phase_id: str
    description: str
    required_tools: List[str]
    depends_on: List[str] = field(default_factory=list)
    estimated_complexity: PhaseComplexity = PhaseComplexity.MEDIUM

    def __post_init__(self):
        if self.depends_on:
            self.depends_on = list(dict.fromkeys(self.depends_on))
        if not self.required_tools:
            self.required_tools = []

    def is_ready(self, completed: set[str]) -> bool:
        return all(dep in completed for dep in self.depends_on)

    def missing_deps(self, done: set[str]) -> List[str]:
        return [dep for dep in self.depends_on if dep not in done]

    def to_dict(self) -> dict:
        return {
            "phase_id": self.phase_id,
            "description": self.description,
            "required_tools": list(self.required_tools),
            "depends_on": list(self.depends_on),
            "estimated_complexity": self.estimated_complexity.value,
        }


@dataclass(slots=True)
class StrategicPlan:
    strategy: str
    phases: List[StrategicPhase]
    estimated_time_seconds: int
    estimated_cost_usd: float
    _by_id: Dict[str, StrategicPhase] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        self._by_id = {p.phase_id: p for p in self.phases}

    def phase_by_id(self, phase_id: str) -> StrategicPhase:
        return self._by_id[phase_id]

    def get_executable_phases(self, completed: set[str]) -> List[StrategicPhase]:
        ready = [p for p in self.phases if p.is_ready(completed)]
        return sorted(ready, key=lambda p: p.phase_id)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "estimated_time_seconds": self.estimated_time_seconds,
            "estimated_cost_usd": self.estimated_cost_usd,
            "phases": [p.to_dict() for p in self.phases],
        }
