import asyncio
import logging
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    cast,
)

from ...utils.logx import log_event, track
from .models import (
    AgentEvent,
    AgentEventType,
    ConversationContext,
    ExecutionPlan,
    ResultEnvelope,
)
from .models.plan import _PlanState
from .models.task import AgentTask


class _CancellationSentinel:
    pass


CANCELLATION_SENTINEL = _CancellationSentinel()


class TaskExecutor:

    def __init__(
        self,
        agent_spawner,
        *,
        max_concurrency: int = 32,
        per_tool_limits: Optional[Dict[str, int]] = None,
        fail_fast: bool = True,
        on_observe: Optional[Callable[[str, Mapping[str, Any]], None]] = None,
        cancellation_poll_interval: float = 0.1,
    ):
        self.spawner = agent_spawner
        self.max_concurrency = max_concurrency
        self.per_tool_limits = per_tool_limits or {}
        self.fail_fast = fail_fast
        self._obs = on_observe
        self._cancellation_poll_interval = cancellation_poll_interval

    @track(operation="execute_plan")
    async def execute_plan(
        self, plan: ExecutionPlan, context: ConversationContext
    ) -> AsyncGenerator[AgentEvent, None]:
        state = _PlanState()
        cancelled = False

        try:
            while not state.terminated and not self._is_plan_complete(plan, state):
                if context.is_cancelled:
                    log_event(
                        "executor_cancellation_detected",
                        {
                            "conversation_id": context.conversation_id,
                            "completed": len(state.completed),
                            "running": len(state.running),
                        },
                    )
                    cancelled = True
                    state.terminated = True
                    break

                for ev in self._skip_due_to_failed_or_skipped_deps(plan, state):
                    log_event(
                        "executor_task_skipped",
                        {
                            "conversation_id": context.conversation_id,
                            "task_id": ev.task_id,
                            "reason": ev.data.get("reason") if ev.data else None,
                        },
                    )
                    self._observe(
                        "task_skipped",
                        task_id=ev.task_id,
                        reason=ev.data.get("reason") if ev.data else None,
                    )
                    yield ev

                for ev in self._schedule_ready_tasks(plan, state, context):
                    log_event(
                        "executor_task_started",
                        {
                            "task_id": ev.task_id,
                            "running_count": len(state.running),
                        },
                    )
                    self._observe("task_started", task_id=ev.task_id)
                    yield ev

                if not state.running and not self._is_plan_complete(plan, state):
                    deadlock_msg = self._deadlock_message(plan, state)
                    log_event(
                        "executor_deadlock_detected",
                        {
                            "conversation_id": context.conversation_id,
                            "message": deadlock_msg,
                            "completed": len(state.completed),
                            "failed": len(state.failed),
                            "skipped": len(state.skipped),
                        },
                        level=logging.ERROR,
                    )
                    self._observe("deadlock", message=deadlock_msg)
                    yield AgentEvent.plan_failed(deadlock_msg)
                    state.terminated = True
                    break

                result = await self._wait_one_or_cancellation(plan, state, context)

                if isinstance(result, _CancellationSentinel):
                    log_event(
                        "executor_cancellation_during_wait",
                        {
                            "conversation_id": context.conversation_id,
                            "running": len(state.running),
                        },
                    )
                    await self._cancel_all(state)
                    cancelled = True
                    state.terminated = True
                    break

                for ev in result:
                    if ev.type == AgentEventType.TASK_COMPLETED:
                        self._observe("task_completed", task_id=ev.task_id)
                    elif ev.type == AgentEventType.TASK_FAILED:
                        log_event(
                            "executor_task_failed",
                            {
                                "conversation_id": context.conversation_id,
                                "task_id": ev.task_id,
                                "error": ev.data.get("error") if ev.data else None,
                                "failed_count": len(state.failed),
                            },
                            level=logging.ERROR,
                        )
                        self._observe(
                            "task_failed",
                            task_id=ev.task_id,
                            error=ev.data.get("error") if ev.data else None,
                        )
                    elif ev.type == AgentEventType.TASK_CANCELLED:
                        log_event(
                            "executor_task_cancelled",
                            {
                                "conversation_id": context.conversation_id,
                                "task_id": ev.task_id,
                            },
                        )
                        self._observe("task_cancelled", task_id=ev.task_id)
                    elif ev.type == AgentEventType.PLAN_FAILED:
                        log_event(
                            "executor_plan_failed",
                            {
                                "conversation_id": context.conversation_id,
                                "message": ev.data.get("error") if ev.data else None,
                            },
                            level=logging.ERROR,
                        )
                        self._observe(
                            "plan_failed",
                            message=ev.data.get("error") if ev.data else None,
                        )
                    elif ev.type == AgentEventType.PLAN_CANCELLED:
                        log_event(
                            "executor_plan_cancelled",
                            {
                                "conversation_id": context.conversation_id,
                            },
                        )
                        self._observe("plan_cancelled")
                        cancelled = True
                    yield ev

            if cancelled:
                log_event(
                    "executor_plan_cancelled_final",
                    {
                        "conversation_id": context.conversation_id,
                        "completed": len(state.completed),
                        "failed": len(state.failed),
                        "skipped": len(state.skipped),
                    },
                )
                self._observe("plan_cancelled", completed_count=len(state.completed))
                yield AgentEvent.plan_cancelled("Execution was cancelled")
            elif not state.terminated:
                log_event(
                    "executor_plan_completed",
                    {
                        "conversation_id": context.conversation_id,
                        "results_count": len(state.results),
                        "completed": len(state.completed),
                        "failed": len(state.failed),
                        "skipped": len(state.skipped),
                    },
                )
                self._observe("plan_completed", results_count=len(state.results))
                yield AgentEvent.plan_completed(state.results)

        except asyncio.CancelledError:
            log_event(
                "executor_cancelled_error",
                {
                    "conversation_id": context.conversation_id,
                    "running_count": len(state.running),
                },
            )
            self._observe("cancelled_error")
            yield AgentEvent.plan_cancelled("Execution was cancelled")

        finally:
            if state.running:
                log_event(
                    "executor_cancelling_tasks",
                    {
                        "conversation_id": context.conversation_id,
                        "running_count": len(state.running),
                    },
                )
            await self._cancel_all(state)

    def _is_plan_complete(self, plan: ExecutionPlan, state: _PlanState) -> bool:
        done = len(state.completed | state.failed | state.skipped)
        return done >= len(plan.tasks)

    def _skip_due_to_failed_or_skipped_deps(
        self, plan: ExecutionPlan, state: _PlanState
    ) -> List[AgentEvent]:
        events: List[AgentEvent] = []
        seen = (
            state.completed | state.failed | state.skipped | set(state.running.keys())
        )
        blockers = state.failed | state.skipped

        for task in plan.tasks:
            if task.task_id in seen:
                continue
            if any(dep in blockers for dep in task.depends_on):
                state.skipped.add(task.task_id)
                events.append(
                    AgentEvent.task_skipped(task, "Blocked by upstream failure/skip")
                )
        return events

    def _schedule_ready_tasks(
        self, plan: ExecutionPlan, state: _PlanState, context: ConversationContext
    ) -> List[AgentEvent]:
        events: List[AgentEvent] = []

        global_headroom = self.max_concurrency - len(state.running)
        if global_headroom <= 0:
            return events

        seen = (
            state.completed | state.failed | state.skipped | set(state.running.keys())
        )
        ready = [
            t
            for t in plan.get_executable_tasks(state.completed)
            if t.task_id not in seen
        ]

        if not ready:
            return events

        for task in ready:
            if global_headroom <= 0:
                break

            limit = self.per_tool_limits.get(task.tool_name)
            running_for_tool = state.running_per_tool.get(task.tool_name, 0)
            if limit is not None and running_for_tool >= limit:
                continue

            fut = asyncio.create_task(self._run_task(task, state, context))
            state.running[task.task_id] = fut
            state.running_per_tool[task.tool_name] = running_for_tool + 1
            global_headroom -= 1

            events.append(AgentEvent.task_started(task))

        return events

    async def _wait_one_or_cancellation(
        self, plan: ExecutionPlan, state: _PlanState, context: ConversationContext
    ) -> List[AgentEvent] | _CancellationSentinel:
        if not state.running:
            return []

        async def cancellation_monitor() -> _CancellationSentinel:
            while not context.is_cancelled:
                await asyncio.sleep(self._cancellation_poll_interval)
            return CANCELLATION_SENTINEL

        monitor_task = asyncio.create_task(cancellation_monitor())
        all_tasks: Set[asyncio.Task[Any]] = set(state.running.values()) | {monitor_task}

        try:
            done, _ = await asyncio.wait(all_tasks, return_when=asyncio.FIRST_COMPLETED)

            if monitor_task in done:
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass
                return CANCELLATION_SENTINEL

            return self._process_completed_tasks(done, plan, state)

        finally:
            if not monitor_task.done():
                monitor_task.cancel()
                try:
                    await monitor_task
                except asyncio.CancelledError:
                    pass

    def _process_completed_tasks(
        self,
        done: Set[asyncio.Task[Any]],
        plan: ExecutionPlan,
        state: _PlanState,
    ) -> List[AgentEvent]:
        events: List[AgentEvent] = []

        for fut in done:
            finished_id = None
            for tid, task_fut in list(state.running.items()):
                if task_fut is fut:
                    finished_id = tid
                    break

            if finished_id is None:
                continue

            agent_task = plan.task_by_id(finished_id)
            tool_name = agent_task.tool_name
            state.running_per_tool[tool_name] = max(
                0, state.running_per_tool.get(tool_name, 1) - 1
            )
            del state.running[finished_id]

            try:
                result: ResultEnvelope = fut.result()
            except asyncio.CancelledError:
                state.failed.add(finished_id)
                events.append(AgentEvent.task_cancelled(agent_task))
                if self.fail_fast and not state.terminated:
                    events.append(
                        AgentEvent.plan_cancelled(f"Task {finished_id} cancelled")
                    )
                    state.terminated = True
                continue
            except Exception as exc:
                state.failed.add(finished_id)
                events.append(AgentEvent.task_failed(agent_task, str(exc)))
                if self.fail_fast and not state.terminated:
                    events.append(
                        AgentEvent.plan_failed(f"Task {finished_id} failed: {exc}")
                    )
                    state.terminated = True
                continue

            if result.status != "ok":
                state.failed.add(finished_id)
                msg = f"{result.error_type}: {result.error_message}"
                events.append(AgentEvent.task_failed(agent_task, msg))
                if self.fail_fast and not state.terminated:
                    events.append(
                        AgentEvent.plan_failed(
                            f"Task {finished_id} failed: {result.error_message}"
                        )
                    )
                    state.terminated = True
                continue

            state.completed.add(finished_id)
            state.results[finished_id] = result.value
            events.append(AgentEvent.task_completed(agent_task, result.value))

        return events

    async def _run_task(
        self, task: AgentTask, state: _PlanState, context: ConversationContext
    ) -> ResultEnvelope:
        res = await self.spawner.spawn_and_execute(task, state.results, context)
        return cast(ResultEnvelope, res)

    async def _cancel_all(self, state: _PlanState) -> None:
        if not state.running:
            return
        for fut in state.running.values():
            fut.cancel()
        await asyncio.gather(*state.running.values(), return_exceptions=True)
        state.running.clear()
        state.running_per_tool.clear()

    def _deadlock_message(self, plan: ExecutionPlan, state: _PlanState) -> str:
        remaining = {
            t.task_id: t
            for t in plan.tasks
            if t.task_id not in (state.completed | state.failed | state.skipped)
        }
        blockers = state.completed | state.skipped | state.failed
        unmet_deps_map: Dict[str, List[str]] = {}
        for tid, task in remaining.items():
            unmet = [d for d in task.depends_on if d not in blockers]
            if unmet:
                unmet_deps_map[tid] = unmet

        remaining_ids = sorted(remaining.keys())
        unmet_deps_str = ", ".join(
            f"{tid}: {deps}" for tid, deps in sorted(unmet_deps_map.items())
        )

        return (
            f"No runnable tasks (deadlock). "
            f"Remaining tasks: {remaining_ids}. "
            f"Unmet dependencies: {{{unmet_deps_str}}}"
        )

    def _observe(self, event: str, **fields: Any) -> None:
        if callable(self._obs):
            try:
                self._obs(event, fields)
            except Exception:
                pass
