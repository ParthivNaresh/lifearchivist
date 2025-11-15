import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from .exceptions import CircularDependencyError, ToolExecutionError
from .models import (
    AgentEvent,
    AgentTask,
    ConversationContext,
    ExecutionPlan,
    ResultEnvelope,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _PlanState:
    completed: Set[str] = field(default_factory=set)
    failed: Set[str] = field(default_factory=set)
    skipped: Set[str] = field(default_factory=set)
    results: Dict[str, Any] = field(default_factory=dict)

    # Running tasks and lookups
    running: Dict[str, asyncio.Task] = field(default_factory=dict)  # task_id -> Task
    task_of: Dict[asyncio.Task, str] = field(default_factory=dict)  # Task -> task_id

    # Concurrency control
    global_sem: asyncio.Semaphore = field(default_factory=lambda: asyncio.Semaphore(32))
    per_tool_sems: Dict[str, asyncio.Semaphore] = field(default_factory=dict)


class TaskExecutor:
    """Concurrent execution of an ExecutionPlan with streaming events."""

    def __init__(
        self,
        agent_spawner,
        *,
        max_concurrency: int = 32,
        per_tool_limits: Optional[Dict[str, int]] = None,
        fail_fast: bool = True,
    ):
        self.spawner = agent_spawner
        self.max_concurrency = max_concurrency
        self.per_tool_limits = per_tool_limits or {}
        self.fail_fast = fail_fast

    # ----------------------------
    # Public API (refactored)
    # ----------------------------
    async def execute_plan(
        self, plan: ExecutionPlan, context: ConversationContext
    ) -> AsyncGenerator[AgentEvent, None]:
        state = self._init_state()

        try:
            while not self._is_plan_complete(plan, state):
                # 1) Mark skips due to upstream failures
                for ev in self._skip_due_to_failed_deps(plan, state):
                    yield ev

                # 2) Schedule all ready tasks
                for ev in self._schedule_ready_tasks(plan, state, context):
                    yield ev

                # 3) Deadlock detection (no progress possible)
                self._assert_not_deadlocked(plan, state)

                # 4) Wait for a single completion and process it
                for ev in await self._wait_one_and_process(plan, state):
                    yield ev

            # 5) Plan complete
            yield AgentEvent.plan_completed(state.results)

        finally:
            await self._cancel_all(state)

    # ----------------------------
    # Helpers (small, focused)
    # ----------------------------
    def _init_state(self) -> _PlanState:
        per_tool_sems = {
            tool: asyncio.Semaphore(limit)
            for tool, limit in self.per_tool_limits.items()
        }
        return _PlanState(
            global_sem=asyncio.Semaphore(self.max_concurrency),
            per_tool_sems=per_tool_sems,
        )

    def _is_plan_complete(self, plan: ExecutionPlan, state: _PlanState) -> bool:
        return len(state.completed | state.failed | state.skipped) >= len(plan.tasks)

    def _skip_due_to_failed_deps(
        self, plan: ExecutionPlan, state: _PlanState
    ) -> List[AgentEvent]:
        events: List[AgentEvent] = []
        seen = (
            state.completed | state.failed | state.skipped | set(state.running.keys())
        )

        for task in plan.tasks:
            if task.task_id in seen:
                continue
            if any(dep in state.failed for dep in task.depends_on):
                state.skipped.add(task.task_id)
                events.append(AgentEvent.task_skipped(task, "Upstream failure"))

        return events

    def _schedule_ready_tasks(
        self, plan: ExecutionPlan, state: _PlanState, context: ConversationContext
    ) -> List[AgentEvent]:
        """Create asyncio tasks for all runnable tasks and emit started events."""
        events: List[AgentEvent] = []
        seen = (
            state.completed | state.failed | state.skipped | set(state.running.keys())
        )

        ready = [
            t
            for t in plan.get_executable_tasks(state.completed)
            if t.task_id not in seen
        ]
        for task in ready:
            events.append(AgentEvent.task_started(task))
            fut = asyncio.create_task(self._run_task(task, state, context))
            state.running[task.task_id] = fut
            state.task_of[fut] = task.task_id
        return events

    def _assert_not_deadlocked(self, plan: ExecutionPlan, state: _PlanState) -> None:
        if state.running:
            return

        remaining = {t.task_id for t in plan.tasks} - (
            state.completed | state.failed | state.skipped
        )
        if not remaining:
            return  # truly done

        # No running tasks, remaining exists -> either cycle or unmet deps
        raise CircularDependencyError(f"Circular dependency or deadlock: {remaining}")

    async def _wait_one_and_process(
        self, plan: ExecutionPlan, state: _PlanState
    ) -> List[AgentEvent]:
        """Wait for the next finished task and update state."""
        if not state.running:
            return []  # no-op; caller already checked deadlock

        done, _ = await asyncio.wait(
            state.running.values(), return_when=asyncio.FIRST_COMPLETED
        )
        events: List[AgentEvent] = []
        for fut in done:
            task_id = state.task_of.pop(fut)
            agent_task = plan.task_by_id(task_id)
            del state.running[task_id]

            try:
                result: ResultEnvelope = await fut
            except asyncio.CancelledError:
                events.append(AgentEvent.task_failed(agent_task, "Cancelled"))
                raise
            except Exception as e:
                events.extend(
                    await self._handle_unexpected_exception(agent_task, state, e)
                )
                continue

            if result.status != "ok":
                events.extend(await self._handle_failure(agent_task, state, result))
                continue

            # success path
            state.completed.add(task_id)
            state.results[task_id] = result.value
            events.append(AgentEvent.task_completed(agent_task, result.value))

        return events

    async def _handle_failure(
        self, agent_task: AgentTask, state: _PlanState, result: ResultEnvelope
    ) -> List[AgentEvent]:
        events = [
            AgentEvent.task_failed(
                agent_task, f"{result.error_type}: {result.error_message}"
            )
        ]
        state.failed.add(agent_task.task_id)

        if self.fail_fast:
            await self._cancel_all(state)
            events.append(
                AgentEvent.plan_failed(
                    f"Task {agent_task.task_id} failed: {result.error_message}"
                )
            )
            raise ToolExecutionError(result.error_message)

        return events

    async def _handle_unexpected_exception(
        self, agent_task: AgentTask, state: _PlanState, exc: Exception
    ) -> List[AgentEvent]:
        events = [AgentEvent.task_failed(agent_task, str(exc))]
        state.failed.add(agent_task.task_id)

        if self.fail_fast:
            await self._cancel_all(state)
            events.append(
                AgentEvent.plan_failed(f"Task {agent_task.task_id} failed: {exc}")
            )
            raise ToolExecutionError(f"Task {agent_task.task_id} failed") from exc

        return events

    async def _cancel_all(self, state: _PlanState) -> None:
        if not state.running:
            return
        for t in state.running.values():
            t.cancel()
        await asyncio.gather(*state.running.values(), return_exceptions=True)
        state.running.clear()
        state.task_of.clear()

    async def _run_task(
        self, task: AgentTask, state: _PlanState, context: ConversationContext
    ) -> ResultEnvelope:
        """Run a single task under global/per-tool semaphores via the spawner."""
        tool_sem = state.per_tool_sems.get(task.tool_name)

        if tool_sem:
            async with state.global_sem, tool_sem:
                return await self.spawner.spawn_and_execute(
                    task, state.results, context
                )
        else:
            async with state.global_sem:
                return await self.spawner.spawn_and_execute(
                    task, state.results, context
                )
