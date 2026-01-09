import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List

from ...llm import LLMMessage
from ...utils.logx import log_event
from .constants import AgentExecutionDefaults, AgentModelDefaults
from .exceptions import PlanningError
from .models.context import ConversationContext
from .models.strategic_plan import PhaseComplexity, StrategicPhase, StrategicPlan
from .prompts import StrategicPromptBuilder
from .strategic_plan_validator import StrategicPlanValidator
from .tool_registry import AgentToolRegistry
from .utils.parsing import json_loads_strict

if TYPE_CHECKING:
    from llm import LLMProviderManager


class StrategicPlanner:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        *,
        planning_model: str = AgentModelDefaults.PLANNING_MODEL,
        planning_temperature: float = AgentModelDefaults.PLANNING_TEMPERATURE,
        max_phases: int = AgentExecutionDefaults.MAX_PHASES,
        max_cost_usd: float = AgentExecutionDefaults.MAX_COST_USD,
        max_time_seconds: int = AgentExecutionDefaults.MAX_TIME_SECONDS,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry
        self.planning_model = planning_model
        self.planning_temperature = planning_temperature
        self.max_phases = max_phases
        self.validator = StrategicPlanValidator(
            tool_registry=tool_registry,
            max_phases=max_phases,
            max_cost_usd=max_cost_usd,
            max_time_seconds=max_time_seconds,
        )

    async def create_strategic_plan(
        self, query: str, context: ConversationContext
    ) -> StrategicPlan:
        log_event(
            "================================================ STRATEGIC PLANNING ================================================"
        )
        log_event("")

        prompt = StrategicPromptBuilder.build(
            query=query,
            context=context,
            available_tools=self.tools.list_tools(),
            max_phases=self.max_phases,
        )

        log_event(
            "------------------------------------------------ STRATEGIC PLAN REQUEST ------------------------------------------------"
        )
        log_event(prompt)

        result = await self.llm.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model=self.planning_model,
            temperature=self.planning_temperature,
            response_format={"type": "json_object"},
        )

        if result.is_failure():
            log_event(
                "strategic_planner_llm_failed",
                {
                    "conversation_id": context.conversation_id,
                    "error": result.error,
                },
                level=logging.ERROR,
            )
            raise PlanningError(f"Strategic planning LLM call failed: {result.error}")

        response = result.unwrap()

        log_event(
            "-------------------------------------- STRATEGIC PLAN LLM RESPONSE --------------------------------------"
        )

        try:
            plan_data = json_loads_strict(response.content, allow_list=False)
            log_event(json.dumps(plan_data, indent=4))
        except Exception as e:
            log_event(
                "strategic_planner_json_parse_failed",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                    "content_preview": response.content[:5000],
                },
                level=logging.ERROR,
            )
            raise PlanningError(f"Invalid strategic plan JSON: {e}") from e

        try:
            strategic_plan = self._build_strategic_plan(plan_data)

            log_event(
                "strategic_plan_created",
                {
                    "strategy": strategic_plan.strategy,
                    "phase_count": len(strategic_plan.phases),
                    "phases": [p.to_dict() for p in strategic_plan.phases],
                },
            )

            return strategic_plan

        except Exception as e:
            log_event(
                "strategic_plan_construction_failed",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            raise PlanningError(f"Strategic plan construction failed: {e}") from e

    def _build_strategic_plan(self, plan_data: Dict[str, Any]) -> StrategicPlan:
        if "phases" not in plan_data:
            raise PlanningError("Strategic plan must include 'phases' key")

        raw_phases = plan_data["phases"]
        if not isinstance(raw_phases, list) or len(raw_phases) == 0:
            raise PlanningError("Strategic plan must have at least one phase")

        phases: List[StrategicPhase] = []
        for p in raw_phases:
            phase_id = p.get("phase_id")
            if not isinstance(phase_id, str) or not phase_id.strip():
                raise PlanningError("Each phase must have a non-empty 'phase_id'")

            description = p.get("description", "")
            if not description:
                raise PlanningError(f"Phase '{phase_id}' must have a description")

            required_tools = p.get("required_tools", [])
            if not isinstance(required_tools, list):
                raise PlanningError(f"Phase '{phase_id}' required_tools must be a list")

            depends_on = p.get("depends_on", [])
            if not isinstance(depends_on, list):
                raise PlanningError(f"Phase '{phase_id}' depends_on must be a list")

            complexity_str = p.get("estimated_complexity", "medium")
            try:
                complexity = PhaseComplexity(complexity_str)
            except ValueError:
                log_event(
                    "strategic_planner_invalid_complexity",
                    {
                        "phase_id": phase_id,
                        "complexity": complexity_str,
                        "defaulting_to": "medium",
                    },
                    level=logging.WARNING,
                )
                complexity = PhaseComplexity.MEDIUM

            phases.append(
                StrategicPhase(
                    phase_id=phase_id.strip(),
                    description=description,
                    required_tools=required_tools,
                    depends_on=depends_on,
                    estimated_complexity=complexity,
                )
            )

        strategy = plan_data.get("strategy", "")
        estimated_time = int(plan_data.get("estimated_time_seconds", 0))
        estimated_cost = float(plan_data.get("estimated_cost_usd", 0.0))

        plan = StrategicPlan(
            strategy=strategy,
            phases=phases,
            estimated_time_seconds=estimated_time,
            estimated_cost_usd=estimated_cost,
        )

        self.validator.validate(plan)

        return plan
