import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from ...utils.logx import log_event
from .constants import AgentExecutionDefaults
from .exceptions import PlanningError
from .models.context import ConversationContext
from .models.events import AgentEvent, AgentEventType
from .models.phase_result import PhaseResult
from .models.strategic_plan import StrategicPhase, StrategicPlan
from .models.task import ExecutionPlan
from .strategic_planner import StrategicPlanner
from .tactical_planner_factory import TacticalPlannerFactory
from .utils.async_utils import maybe_timeout


def _check_cancelled(context: ConversationContext) -> bool:
    return context.is_cancelled


class PhaseCoordinator:

    def __init__(
        self,
        strategic_planner: StrategicPlanner,
        tactical_planner_factory: TacticalPlannerFactory,
        *,
        phase_timeout_s: float | None = AgentExecutionDefaults.PHASE_TIMEOUT_SECONDS,
    ):
        self.strategic_planner = strategic_planner
        self.tactical_planner_factory = tactical_planner_factory
        self.phase_timeout_s = phase_timeout_s

    async def execute_query(
        self, query: str, context: ConversationContext
    ) -> AsyncGenerator[AgentEvent, None]:
        log_event(
            "================================================ PHASE COORDINATOR STARTS ================================================"
        )
        log_event("")

        current_phase_id: Optional[str] = None

        try:
            if _check_cancelled(context):
                log_event(
                    "phase_coordinator_cancelled_before_start",
                    {"conversation_id": context.conversation_id},
                )
                yield AgentEvent.plan_cancelled("Cancelled before execution started")
                yield AgentEvent.cancelled()
                return

            strategic_plan = await self._create_strategic_plan_with_cancellation(
                query, context
            )
            if strategic_plan is None:
                return

            log_event(
                "phase_coordinator_strategic_plan_created",
                {
                    "strategy": strategic_plan.strategy,
                    "phase_count": len(strategic_plan.phases),
                    "phases": [p.phase_id for p in strategic_plan.phases],
                },
            )

            yield AgentEvent(
                type=AgentEventType.PLAN_CREATED,
                data={
                    "type": "strategic",
                    "strategy": strategic_plan.strategy,
                    "phase_count": len(strategic_plan.phases),
                    "phases": [
                        {
                            "phase_id": p.phase_id,
                            "description": p.description,
                            "complexity": p.estimated_complexity.value,
                            "required_tools": p.required_tools,
                        }
                        for p in strategic_plan.phases
                    ],
                    "estimated_time_seconds": strategic_plan.estimated_time_seconds,
                    "estimated_cost_usd": strategic_plan.estimated_cost_usd,
                },
            )

            phase_results: Dict[str, PhaseResult] = {}
            completed_phases: set[str] = set()

            for phase_idx, phase in enumerate(strategic_plan.phases, 1):
                current_phase_id = phase.phase_id

                if _check_cancelled(context):
                    log_event(
                        "phase_coordinator_cancelled_before_phase",
                        {
                            "conversation_id": context.conversation_id,
                            "phase_id": phase.phase_id,
                        },
                    )
                    yield AgentEvent.phase_cancelled(phase.phase_id)
                    yield AgentEvent.plan_cancelled(
                        f"Cancelled before phase {phase.phase_id}"
                    )
                    yield AgentEvent.cancelled()
                    return

                log_event(
                    "phase_coordinator_executing_phase",
                    {
                        "phase_id": phase.phase_id,
                        "phase_number": phase_idx,
                        "total_phases": len(strategic_plan.phases),
                        "description": phase.description,
                        "timeout_seconds": self.phase_timeout_s,
                    },
                )

                if not phase.is_ready(completed_phases):
                    missing = phase.missing_deps(completed_phases)
                    error_msg = (
                        f"Phase {phase.phase_id} dependencies not met: {missing}"
                    )
                    log_event(
                        "phase_coordinator_dependency_error",
                        {
                            "phase_id": phase.phase_id,
                            "missing_dependencies": missing,
                        },
                        level=logging.ERROR,
                    )
                    yield AgentEvent.plan_failed(error_msg)
                    yield AgentEvent.complete()
                    return

                log_event(
                    f"================================================ EXECUTING PHASE {phase} ================================================"
                )
                log_event("")

                phase_result = PhaseResult(phase_id=phase.phase_id)

                try:
                    async for ev in self._execute_phase_with_timeout(
                        phase=phase,
                        phase_number=phase_idx,
                        total_phases=len(strategic_plan.phases),
                        query=query,
                        context=context,
                        previous_results=phase_results,
                        phase_result=phase_result,
                    ):
                        yield ev

                        if ev.type == AgentEventType.PLAN_FAILED:
                            phase_results[phase.phase_id] = phase_result
                            raise PlanningError(
                                f"Phase {phase.phase_id} execution failed"
                            )
                        if ev.type == AgentEventType.PLAN_CANCELLED:
                            phase_results[phase.phase_id] = phase_result
                            yield AgentEvent.cancelled()
                            return

                    phase_results[phase.phase_id] = phase_result
                    completed_phases.add(phase.phase_id)

                    yield AgentEvent.phase_completed(phase.phase_id)

                    log_event(
                        "phase_coordinator_phase_completed",
                        {
                            "phase_id": phase.phase_id,
                            "phase_number": phase_idx,
                            "total_phases": len(strategic_plan.phases),
                            "completed_tasks": len(phase_result.completed),
                            "failed_tasks": len(phase_result.failed),
                            "skipped_tasks": len(phase_result.skipped),
                        },
                    )

                except TimeoutError:
                    phase_results[phase.phase_id] = phase_result
                    log_event(
                        "phase_coordinator_phase_timeout",
                        {
                            "conversation_id": context.conversation_id,
                            "phase_id": phase.phase_id,
                            "timeout_seconds": self.phase_timeout_s,
                            "completed_tasks": len(phase_result.completed),
                            "failed_tasks": len(phase_result.failed),
                            "skipped_tasks": len(phase_result.skipped),
                        },
                        level=logging.ERROR,
                    )
                    yield AgentEvent.plan_failed(
                        f"Phase {phase.phase_id} timed out after {self.phase_timeout_s}s"
                    )
                    yield AgentEvent.complete()
                    return

                except asyncio.CancelledError:
                    log_event(
                        "phase_coordinator_phase_cancelled",
                        {
                            "conversation_id": context.conversation_id,
                            "phase_id": phase.phase_id,
                        },
                    )
                    yield AgentEvent.phase_cancelled(phase.phase_id)
                    yield AgentEvent.plan_cancelled(
                        f"Phase {phase.phase_id} was cancelled"
                    )
                    yield AgentEvent.cancelled()
                    return

                except PlanningError:
                    raise

                except Exception as e:
                    log_event(
                        "phase_coordinator_phase_execution_failed",
                        {
                            "phase_id": phase.phase_id,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                        level=logging.ERROR,
                    )
                    yield AgentEvent.plan_failed(
                        f"Phase {phase.phase_id} execution failed: {e}"
                    )
                    yield AgentEvent.complete()
                    return

            current_phase_id = None

            log_event(
                "phase_coordinator_all_phases_completed",
                {
                    "total_phases": len(strategic_plan.phases),
                    "completed_phases": len(completed_phases),
                },
            )

            if _check_cancelled(context):
                log_event(
                    "phase_coordinator_cancelled_before_synthesis",
                    {"conversation_id": context.conversation_id},
                )
                yield AgentEvent.plan_cancelled("Cancelled before synthesis")
                yield AgentEvent.cancelled()
                return

            log_event(
                "------------------------------------------------ STARTING PHASE COORDINATOR SYNTHESIS ------------------------------------------------"
            )
            yield AgentEvent.synthesis_started()

            try:
                synthesis_planner = self.tactical_planner_factory.create()
                synthesis_results = self._flatten_phase_results_for_synthesis(
                    phase_results
                )

                async for chunk in synthesis_planner._synthesize_response(
                    query=query,
                    plan=self._create_synthetic_execution_plan(strategic_plan),
                    task_results=synthesis_results,
                    context=context,
                ):
                    if _check_cancelled(context):
                        log_event(
                            "phase_coordinator_synthesis_cancelled",
                            {"conversation_id": context.conversation_id},
                        )
                        yield AgentEvent.plan_cancelled("Synthesis cancelled")
                        yield AgentEvent.cancelled()
                        return
                    yield AgentEvent.response_chunk(chunk)

                log_event(
                    "------------------------------------------------ FINISHED PHASE COORDINATOR SYNTHESIS ------------------------------------------------"
                )
            except asyncio.CancelledError:
                log_event(
                    "phase_coordinator_synthesis_cancelled",
                    {"conversation_id": context.conversation_id},
                )
                yield AgentEvent.plan_cancelled("Synthesis was cancelled")
                yield AgentEvent.cancelled()
                return
            except Exception as e:
                log_event(
                    "phase_coordinator_synthesis_failed",
                    {
                        "conversation_id": context.conversation_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    level=logging.ERROR,
                )
                yield AgentEvent.error(f"Synthesis failed: {e}")

            yield AgentEvent.complete()

        except asyncio.CancelledError:
            log_event(
                "phase_coordinator_cancelled",
                {
                    "conversation_id": context.conversation_id,
                    "current_phase": current_phase_id,
                },
            )
            if current_phase_id:
                yield AgentEvent.phase_cancelled(current_phase_id)
            yield AgentEvent.plan_cancelled("Execution was cancelled")
            yield AgentEvent.cancelled()

        except PlanningError as e:
            log_event(
                "phase_coordinator_planning_error",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            yield AgentEvent.plan_failed(str(e))
            yield AgentEvent.complete()

        except Exception as e:
            log_event(
                "phase_coordinator_unexpected_error",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            yield AgentEvent.error(f"Unexpected error: {e}")
            yield AgentEvent.complete()

    async def _execute_phase_with_timeout(
        self,
        phase: StrategicPhase,
        phase_number: int,
        total_phases: int,
        query: str,
        context: ConversationContext,
        previous_results: Dict[str, PhaseResult],
        phase_result: PhaseResult,
    ) -> AsyncGenerator[AgentEvent, None]:
        async with maybe_timeout(self.phase_timeout_s):
            async for ev in self._execute_phase_streaming(
                phase=phase,
                phase_number=phase_number,
                total_phases=total_phases,
                query=query,
                context=context,
                previous_results=previous_results,
            ):
                self._capture_task_event(ev, phase_result)
                yield ev

    def _capture_task_event(self, ev: AgentEvent, phase_result: PhaseResult) -> None:
        if ev.task_id is None:
            return

        if ev.type == AgentEventType.TASK_COMPLETED:
            phase_result.add_completed(ev.task_id, ev.data)

        elif ev.type == AgentEventType.TASK_FAILED:
            error = (
                ev.data.get("error", "Unknown error") if ev.data else "Unknown error"
            )
            phase_result.add_failed(ev.task_id, error)

        elif ev.type == AgentEventType.TASK_SKIPPED:
            reason = (
                ev.data.get("reason", "Unknown reason") if ev.data else "Unknown reason"
            )
            phase_result.add_skipped(ev.task_id, reason)

    def _flatten_phase_results_for_synthesis(
        self, phase_results: Dict[str, PhaseResult]
    ) -> Dict[str, Any]:
        flattened: Dict[str, Any] = {}

        for phase_id, phase_result in phase_results.items():
            phase_data = phase_result.to_synthesis_dict()

            for task_id, data in phase_data.items():
                flattened[f"{phase_id}.{task_id}"] = data

            if not phase_result.is_success:
                flattened[f"{phase_id}._meta"] = {
                    "is_partial": phase_result.is_partial,
                    "completed_count": len(phase_result.completed),
                    "failed_count": len(phase_result.failed),
                    "skipped_count": len(phase_result.skipped),
                }

        return flattened

    async def _create_strategic_plan_with_cancellation(
        self, query: str, context: ConversationContext
    ) -> Optional[StrategicPlan]:
        try:
            if _check_cancelled(context):
                return None
            return await self.strategic_planner.create_strategic_plan(query, context)
        except asyncio.CancelledError:
            log_event(
                "phase_coordinator_strategic_planning_cancelled",
                {"conversation_id": context.conversation_id},
            )
            return None
        except PlanningError as e:
            log_event(
                "phase_coordinator_strategic_planning_failed",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            raise
        except Exception as e:
            log_event(
                "phase_coordinator_strategic_planning_exception",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            raise PlanningError(f"Strategic planning exception: {e}") from e

    async def _execute_phase_streaming(
        self,
        phase: StrategicPhase,
        phase_number: int,
        total_phases: int,
        query: str,
        context: ConversationContext,
        previous_results: Dict[str, PhaseResult],
    ) -> AsyncGenerator[AgentEvent, None]:
        tactical_planner = self.tactical_planner_factory.create()

        phase_query = self._build_phase_query(phase, query, previous_results)

        available_tools = self._filter_tools_for_phase(phase, tactical_planner)

        log_event(
            "phase_coordinator_tactical_planning",
            {
                "phase_id": phase.phase_id,
                "phase_number": phase_number,
                "phase_query": phase_query[:200],
                "available_tools": [t.name for t in available_tools],
            },
        )

        execution_plan = await tactical_planner.create_tactical_plan(
            query=phase_query,
            context=context,
            available_tools=available_tools,
        )

        log_event(
            "================================================ PHASE COORDINATOR EXECUTION PLAN ================================================"
        )
        log_event(
            "phase_coordinator_execution_plan",
            {
                "task_count": len(execution_plan.tasks),
                "tasks": [t.task_id for t in execution_plan.tasks],
            },
        )
        log_event(
            "phase_coordinator_execution_plan_details",
            execution_plan.to_dict(),
        )

        execution_plan.reasoning = (
            f"Phase {phase_number}/{total_phases}: {phase.description}\n"
            f"Tactical: {execution_plan.reasoning}"
        )

        yield AgentEvent(
            type=AgentEventType.PLAN_CREATED,
            data={
                "type": "tactical",
                "phase_id": phase.phase_id,
                "phase_number": phase_number,
                "total_phases": total_phases,
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "tool": t.tool_name,
                        "description": t.description,
                    }
                    for t in execution_plan.tasks
                ],
                "reasoning": execution_plan.reasoning,
            },
        )

        async for ev in tactical_planner.executor.execute_plan(execution_plan, context):
            yield ev

    def _build_phase_query(
        self,
        phase: StrategicPhase,
        original_query: str,
        previous_results: Dict[str, PhaseResult],
    ) -> str:
        query_parts = [phase.description]

        if previous_results:
            document_ids = self._extract_document_ids_from_results(previous_results)

            if document_ids:
                query_parts.append(
                    f"\n\nDOCUMENT IDS FROM PREVIOUS PHASES (use these directly in document_ids parameter):\n"
                    f"{json.dumps(document_ids, indent=2)}"
                )

            summary = self._summarize_previous_results(previous_results)
            if summary:
                query_parts.append(f"\n\nPREVIOUS PHASE SUMMARY:\n{summary}")

        query_parts.append(f"\n\nOriginal user request: {original_query}")

        return "\n".join(query_parts)

    def _extract_document_ids_from_results(
        self, phase_results: Dict[str, PhaseResult]
    ) -> List[str]:
        document_ids: List[str] = []
        seen: set[str] = set()

        for _phase_id, phase_result in phase_results.items():
            for _task_id, result in phase_result.completed.items():
                ids = self._extract_ids_from_value(result)
                for doc_id in ids:
                    if doc_id not in seen:
                        document_ids.append(doc_id)
                        seen.add(doc_id)

        return document_ids

    def _extract_ids_from_value(self, value: Any) -> List[str]:
        ids: List[str] = []

        if isinstance(value, dict):
            if "document_id" in value and isinstance(value["document_id"], str):
                ids.append(value["document_id"])

            if "documents" in value and isinstance(value["documents"], list):
                for doc in value["documents"]:
                    if isinstance(doc, dict) and "document_id" in doc:
                        ids.append(doc["document_id"])

            for v in value.values():
                ids.extend(self._extract_ids_from_value(v))

        elif isinstance(value, list):
            for item in value:
                ids.extend(self._extract_ids_from_value(item))

        return ids

    def _summarize_previous_results(
        self, phase_results: Dict[str, PhaseResult], max_chars: int = 2000
    ) -> Optional[str]:
        if not phase_results:
            return None

        summaries: List[str] = []

        for phase_id, phase_result in phase_results.items():
            if not phase_result.is_success:
                status_parts = []
                if phase_result.failed:
                    status_parts.append(f"{len(phase_result.failed)} failed")
                if phase_result.skipped:
                    status_parts.append(f"{len(phase_result.skipped)} skipped")
                status = ", ".join(status_parts)
                summaries.append(
                    f"- {phase_id}: PARTIAL ({len(phase_result.completed)} completed, {status})"
                )

            for task_id, result in phase_result.completed.items():
                doc_count = self._count_documents(result)
                if doc_count > 0:
                    summaries.append(
                        f"- {phase_id}/{task_id}: Found {doc_count} documents"
                    )

                if isinstance(result, dict):
                    if "text" in result:
                        text_preview = str(result["text"])[:200]
                        summaries.append(
                            f"- {phase_id}/{task_id}: Text output (preview): {text_preview}..."
                        )
                    elif "extractions" in result:
                        ext_count = (
                            len(result["extractions"])
                            if isinstance(result["extractions"], list)
                            else 1
                        )
                        summaries.append(
                            f"- {phase_id}/{task_id}: Extracted {ext_count} items"
                        )

            for task_id, error in phase_result.failed.items():
                summaries.append(f"- {phase_id}/{task_id}: FAILED - {error[:100]}")

        if not summaries:
            return None

        summary = "\n".join(summaries)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        return summary

    def _count_documents(self, value: Any) -> int:
        if isinstance(value, dict):
            if "documents" in value and isinstance(value["documents"], list):
                return len(value["documents"])

            total = 0
            for v in value.values():
                total += self._count_documents(v)
            return total

        return 0

    def _filter_tools_for_phase(
        self, phase: StrategicPhase, tactical_planner: Any
    ) -> List[Any]:
        all_tools: List[Any] = list(tactical_planner.tools.list_tools())

        if not phase.required_tools:
            return all_tools

        return [tool for tool in all_tools if tool.name in phase.required_tools]

    def _create_synthetic_execution_plan(
        self, strategic_plan: StrategicPlan
    ) -> ExecutionPlan:
        return ExecutionPlan(
            tasks=[],
            estimated_time_seconds=strategic_plan.estimated_time_seconds,
            estimated_cost_usd=strategic_plan.estimated_cost_usd,
            reasoning=strategic_plan.strategy,
        )
