import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Set

from ....llm.agent.models import ResultEnvelope


@dataclass(slots=True)
class _PlanState:
    # Terminal states
    completed: Set[str] = field(default_factory=set)
    failed: Set[str] = field(default_factory=set)
    skipped: Set[str] = field(default_factory=set)

    # Results by task_id
    results: Dict[str, Any] = field(default_factory=dict)

    # Running bookkeeping
    running: Dict[str, asyncio.Task[ResultEnvelope]] = field(
        default_factory=dict
    )  # task_id -> task
    running_per_tool: Dict[str, int] = field(default_factory=dict)  # tool_name -> count

    # Control flags
    terminated: bool = False  # set when fail_fast triggers
