import asyncio
from typing import Any, Dict, List, Optional

import pytest

from lifearchivist.llm.agent.executor import TaskExecutor
from lifearchivist.llm.agent.models import (
    AgentEventType,
    ConversationContext,
    ExecutionPlan,
    ResultEnvelope,
)
from lifearchivist.llm.agent.models.task import AgentTask


class DummySpawner:
    def __init__(
        self,
        outcomes: Optional[Dict[str, str]] = None,
        values: Optional[Dict[str, Any]] = None,
        wait_events: Optional[Dict[str, asyncio.Event]] = None,
        delays: Optional[Dict[str, float]] = None,
    ):
        self.outcomes = outcomes or {}
        self.values = values or {}
        self.wait_events = wait_events or {}
        self.delays = delays or {}
        self.calls: List[str] = []

    async def spawn_and_execute(self, task: AgentTask, results: Dict[str, Any], context: ConversationContext) -> ResultEnvelope:
        self.calls.append(task.task_id)
        if task.task_id in self.delays:
            await asyncio.sleep(self.delays[task.task_id])
        if task.task_id in self.wait_events:
            await self.wait_events[task.task_id].wait()
        outcome = self.outcomes.get(task.task_id, "ok")
        if outcome == "error":
            return ResultEnvelope.error(task.task_id, "boom")
        return ResultEnvelope.ok(task.task_id, self.values.get(task.task_id, {"ok": True}))


def make_context() -> ConversationContext:
    return ConversationContext(conversation_id="c1", user_id="u1")


def make_task(tid: str, tool: str = "toolA", deps: Optional[List[str]] = None) -> AgentTask:
    return AgentTask(task_id=tid, tool_name=tool, description="d", requires_llm=False, parameters={}, depends_on=list(deps or []))


def make_plan(tasks: List[AgentTask]) -> ExecutionPlan:
    return ExecutionPlan(tasks=tasks, estimated_time_seconds=0, estimated_cost_usd=0.0, reasoning="")


async def collect_events(agen) -> List:
    evs = []
    async for ev in agen:
        evs.append(ev)
    return evs


async def anext_with_timeout(agen, timeout: float):
    return await asyncio.wait_for(agen.__anext__(), timeout=timeout)


@pytest.mark.asyncio
async def test_executes_tasks_with_dependencies_and_collects_results():
    t1 = make_task("t1")
    t2 = make_task("t2", deps=["t1"])
    spawner = DummySpawner()
    executor = TaskExecutor(spawner, max_concurrency=4, fail_fast=True)
    plan = make_plan([t1, t2])
    ctx = make_context()

    events = []
    async for ev in executor.execute_plan(plan, ctx):
        events.append(ev)

    types = [e.type for e in events]
    assert AgentEventType.TASK_STARTED in types
    assert AgentEventType.TASK_COMPLETED in types
    assert AgentEventType.PLAN_COMPLETED in types

    started_ids = [e.task_id for e in events if e.type == AgentEventType.TASK_STARTED]
    completed_ids = [e.task_id for e in events if e.type == AgentEventType.TASK_COMPLETED]
    assert started_ids[0] == "t1"
    assert completed_ids[0] == "t1"

    final = [e for e in events if e.type == AgentEventType.PLAN_COMPLETED][-1]
    results = final.data.get("results", {}) if final.data else {}
    assert set(results.keys()) == {"t1", "t2"}


@pytest.mark.asyncio
async def test_respects_global_max_concurrency():
    wait1 = asyncio.Event()
    wait2 = asyncio.Event()
    wait3 = asyncio.Event()

    t1 = make_task("t1")
    t2 = make_task("t2")
    t3 = make_task("t3")

    spawner = DummySpawner(wait_events={"t1": wait1, "t2": wait2, "t3": wait3})
    executor = TaskExecutor(spawner, max_concurrency=2, fail_fast=True)
    plan = make_plan([t1, t2, t3])
    ctx = make_context()

    agen = executor.execute_plan(plan, ctx)

    ev1 = await anext_with_timeout(agen, 1.0)
    ev2 = await anext_with_timeout(agen, 1.0)
    assert ev1.type == AgentEventType.TASK_STARTED
    assert ev2.type == AgentEventType.TASK_STARTED
    started = {ev1.task_id, ev2.task_id}
    assert started.issubset({"t1", "t2", "t3"})

    with pytest.raises(asyncio.TimeoutError):
        await anext_with_timeout(agen, 0.2)

    wait1.set()
    ev3 = await anext_with_timeout(agen, 1.0)
    assert ev3.type in {AgentEventType.TASK_COMPLETED, AgentEventType.TASK_FAILED}

    ev4 = await anext_with_timeout(agen, 1.0)
    assert ev4.type == AgentEventType.TASK_STARTED

    wait2.set()
    wait3.set()

    remaining = await collect_events(agen)
    assert any(e.type == AgentEventType.PLAN_COMPLETED for e in remaining)


@pytest.mark.asyncio
async def test_respects_per_tool_limits():
    wait1 = asyncio.Event()
    wait2 = asyncio.Event()
    wait3 = asyncio.Event()

    t1 = make_task("t1", tool="toolA")
    t2 = make_task("t2", tool="toolA")
    t3 = make_task("t3", tool="toolB")

    spawner = DummySpawner(wait_events={"t1": wait1, "t2": wait2, "t3": wait3})
    executor = TaskExecutor(spawner, max_concurrency=3, per_tool_limits={"toolA": 1}, fail_fast=True)
    plan = make_plan([t1, t2, t3])
    ctx = make_context()

    agen = executor.execute_plan(plan, ctx)

    ev1 = await anext_with_timeout(agen, 1.0)
    ev2 = await anext_with_timeout(agen, 1.0)
    assert {ev1.type, ev2.type} == {AgentEventType.TASK_STARTED}
    started = {ev1.task_id, ev2.task_id}
    assert started == {"t1", "t3"}

    with pytest.raises(asyncio.TimeoutError):
        await anext_with_timeout(agen, 0.2)

    wait1.set()
    ev3 = await anext_with_timeout(agen, 1.0)
    assert ev3.type in {AgentEventType.TASK_COMPLETED, AgentEventType.TASK_FAILED}

    ev4 = await anext_with_timeout(agen, 1.0)
    assert ev4.type == AgentEventType.TASK_STARTED
    assert ev4.task_id == "t2"

    wait2.set()
    wait3.set()
    rest = await collect_events(agen)
    assert any(e.type == AgentEventType.PLAN_COMPLETED for e in rest)


@pytest.mark.asyncio
async def test_fail_fast_on_task_failure_emits_plan_failed_and_cancels_others():
    wait2 = asyncio.Event()

    t1 = make_task("t1")
    t2 = make_task("t2")

    spawner = DummySpawner(outcomes={"t1": "error", "t2": "ok"}, wait_events={"t2": wait2})
    executor = TaskExecutor(spawner, max_concurrency=2, fail_fast=True)
    plan = make_plan([t1, t2])
    ctx = make_context()

    events = []
    async for ev in executor.execute_plan(plan, ctx):
        events.append(ev)

    types = [e.type for e in events]
    assert AgentEventType.TASK_FAILED in types
    assert AgentEventType.PLAN_FAILED in types
    assert AgentEventType.PLAN_COMPLETED not in types


@pytest.mark.asyncio
async def test_deadlock_detection_emits_plan_failed():
    t1 = make_task("t1", deps=["t2"])
    t2 = make_task("t2", deps=["t1"])
    spawner = DummySpawner()
    executor = TaskExecutor(spawner, max_concurrency=2, fail_fast=True)
    plan = make_plan([t1, t2])
    ctx = make_context()

    events = []
    async for ev in executor.execute_plan(plan, ctx):
        events.append(ev)

    types = [e.type for e in events]
    assert AgentEventType.PLAN_FAILED in types


@pytest.mark.asyncio
async def test_non_fail_fast_skips_downstream_and_completes():
    t1 = make_task("t1")
    t2 = make_task("t2", deps=["t1"])

    spawner = DummySpawner(outcomes={"t1": "error"})
    executor = TaskExecutor(spawner, max_concurrency=2, fail_fast=False)
    plan = make_plan([t1, t2])
    ctx = make_context()

    events = []
    async for ev in executor.execute_plan(plan, ctx):
        events.append(ev)

    types = [e.type for e in events]
    assert AgentEventType.TASK_FAILED in types
    assert AgentEventType.TASK_SKIPPED in types
    assert AgentEventType.PLAN_COMPLETED in types
