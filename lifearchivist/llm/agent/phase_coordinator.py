import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from ...utils.logx import log_event
from .exceptions import PlanningError
from .models.context import ConversationContext
from .models.events import AgentEvent, AgentEventType
from .models.strategic_plan import StrategicPhase, StrategicPlan
from .strategic_planner import StrategicPlanner
from .tactical_planner_factory import TacticalPlannerFactory


class PhaseCoordinator:
    """
    Coordinates multi-phase query execution using hierarchical planning.

    Responsibilities:
    - Create strategic plan (high-level phases)
    - Execute each phase using isolated tactical planner instances
    - Manage phase dependencies and result passing
    - Aggregate results across phases
    - Synthesize final response

    Architecture:
        User Query → Strategic Planner → Phases
        For each phase:
            Phase → NEW Tactical Planner → Tasks → Executor → Results
        All Results → Synthesizer → Final Answer

    Each phase gets its own TacticalPlanner instance for complete isolation.
    This enables parallel execution and prevents state pollution.
    """

    def __init__(
        self,
        strategic_planner: StrategicPlanner,
        tactical_planner_factory: TacticalPlannerFactory,
    ):
        self.strategic_planner = strategic_planner
        self.tactical_planner_factory = tactical_planner_factory

    async def execute_query(
        self, query: str, context: ConversationContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Execute query using hierarchical planning.

        Sequential execution of all phases with isolated tactical planners.

        Args:
            query: User's query
            context: Conversation context

        Yields:
            AgentEvent objects for streaming progress
        """
        log_event(
            "================================================ PHASE COORDINATOR STARTS ================================================"
        )
        log_event("")
        try:
            strategic_plan = await self.strategic_planner.create_strategic_plan(
                query, context
            )
        except PlanningError as e:
            log_event(
                "phase_coordinator_strategic_planning_failed",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            yield AgentEvent.plan_failed(f"Strategic planning failed: {e}")
            yield AgentEvent.complete()
            return
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
            yield AgentEvent.plan_failed(f"Strategic planning exception: {e}")
            yield AgentEvent.complete()
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

        phase_results: Dict[str, Any] = {}
        completed_phases: set[str] = set()

        for phase_idx, phase in enumerate(strategic_plan.phases, 1):
            log_event(
                "phase_coordinator_executing_phase",
                {
                    "phase_id": phase.phase_id,
                    "phase_number": phase_idx,
                    "total_phases": len(strategic_plan.phases),
                    "description": phase.description,
                },
            )

            if not phase.is_ready(completed_phases):
                missing = phase.missing_deps(completed_phases)
                error_msg = f"Phase {phase.phase_id} dependencies not met: {missing}"
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

            try:
                phase_task_results: Dict[str, Any] = {}
                async for ev in self._execute_phase_streaming(
                    phase=phase,
                    phase_number=phase_idx,
                    total_phases=len(strategic_plan.phases),
                    query=query,
                    context=context,
                    previous_results=phase_results,
                ):
                    yield ev
                    if ev.type == AgentEventType.TASK_COMPLETED and ev.task_id:
                        phase_task_results[ev.task_id] = ev.data
                    if ev.type == AgentEventType.PLAN_FAILED:
                        raise PlanningError(f"Phase {phase.phase_id} execution failed")

                phase_results[phase.phase_id] = phase_task_results
                completed_phases.add(phase.phase_id)

                yield AgentEvent.phase_completed(phase.phase_id)

                log_event(
                    "phase_coordinator_phase_completed",
                    {
                        "phase_id": phase.phase_id,
                        "phase_number": phase_idx,
                        "total_phases": len(strategic_plan.phases),
                    },
                )

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

        log_event(
            "phase_coordinator_all_phases_completed",
            {
                "total_phases": len(strategic_plan.phases),
                "completed_phases": len(completed_phases),
            },
        )

        log_event(
            "------------------------------------------------ STARTING PHASE COORDINATOR SYNTHESIS ------------------------------------------------"
        )
        yield AgentEvent.synthesis_started()

        try:
            synthesis_planner = self.tactical_planner_factory.create()

            async for chunk in synthesis_planner._synthesize_response(
                query=query,
                plan=self._create_synthetic_execution_plan(strategic_plan),
                task_results=phase_results,
            ):
                yield AgentEvent.response_chunk(chunk)

            log_event(
                "------------------------------------------------ FINISHED PHASE COORDINATOR SYNTHESIS ------------------------------------------------"
            )
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

    async def _execute_phase_streaming(
        self,
        phase: StrategicPhase,
        phase_number: int,
        total_phases: int,
        query: str,
        context: ConversationContext,
        previous_results: Dict[str, Any],
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
        log_event(execution_plan.tasks)
        log_event(execution_plan.to_dict())

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
        previous_results: Dict[str, Any],
    ) -> str:
        """
        Build query for tactical planner based on phase description and context.

        When previous phases have produced document IDs, we inject them directly
        so the tactical planner can use them in parameters without needing
        cross-phase dependency references.
        """
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
        self, phase_results: Dict[str, Any]
    ) -> List[str]:
        """
        Extract document IDs from previous phase results.

        Searches through phase results for document search outputs and extracts
        the document_id values for use in downstream phases.
        """
        document_ids: List[str] = []
        seen: set[str] = set()

        for _phase_id, result in phase_results.items():
            ids = self._extract_ids_from_value(result)
            for doc_id in ids:
                if doc_id not in seen:
                    document_ids.append(doc_id)
                    seen.add(doc_id)

        return document_ids

    def _extract_ids_from_value(self, value: Any) -> List[str]:
        """
        Recursively extract document_id values from a nested structure.
        """
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
        self, phase_results: Dict[str, Any], max_chars: int = 2000
    ) -> Optional[str]:
        """
        Create a compact summary of previous phase results for context.
        """
        if not phase_results:
            return None

        summaries: List[str] = []

        for phase_id, result in phase_results.items():
            doc_count = self._count_documents(result)
            if doc_count > 0:
                summaries.append(f"- {phase_id}: Found {doc_count} documents")

            if isinstance(result, dict):
                if "text" in result:
                    text_preview = str(result["text"])[:200]
                    summaries.append(
                        f"- {phase_id}: Text output (preview): {text_preview}..."
                    )
                elif "extractions" in result:
                    ext_count = (
                        len(result["extractions"])
                        if isinstance(result["extractions"], list)
                        else 1
                    )
                    summaries.append(f"- {phase_id}: Extracted {ext_count} items")

        if not summaries:
            return None

        summary = "\n".join(summaries)
        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."

        return summary

    def _count_documents(self, value: Any) -> int:
        """
        Count documents in a result structure.
        """
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
        """
        Filter available tools based on phase requirements.
        """
        all_tools = tactical_planner.tools.list_tools()

        if not phase.required_tools:
            return all_tools

        return [tool for tool in all_tools if tool.name in phase.required_tools]

    def _create_synthetic_execution_plan(self, strategic_plan: StrategicPlan) -> Any:
        """
        Create a synthetic execution plan for synthesis that represents the strategic plan.
        """
        from .models.task import ExecutionPlan

        return ExecutionPlan(
            tasks=[],
            estimated_time_seconds=strategic_plan.estimated_time_seconds,
            estimated_cost_usd=strategic_plan.estimated_cost_usd,
            reasoning=strategic_plan.strategy,
        )
