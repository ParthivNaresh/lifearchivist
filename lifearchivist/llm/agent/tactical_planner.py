import json
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
)

from ...llm import LLMMessage
from ...utils.logx import log_event
from .complexity_classifier import ComplexityClassifier
from .constants import AgentModelDefaults
from .exceptions import PlanningError
from .executor import TaskExecutor
from .models.context import ConversationContext
from .models.task import AgentTask, ExecutionPlan
from .plan_validator import PlanValidator
from .prompts import SynthesisPromptBuilder, TacticalPromptBuilder
from .tool_registry import AgentToolRegistry
from .utils.parsing import json_loads_strict

if TYPE_CHECKING:
    from llm import LLMProviderManager


class TacticalPlanner:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        complexity_classifier: ComplexityClassifier,
        executor: TaskExecutor,
        plan_validator: PlanValidator,
        *,
        planning_model: str = AgentModelDefaults.PLANNING_MODEL,
        planning_temperature: float = AgentModelDefaults.PLANNING_TEMPERATURE,
        synthesis_model: str = AgentModelDefaults.SYNTHESIS_MODEL,
        synthesis_temperature: float = AgentModelDefaults.SYNTHESIS_TEMPERATURE,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry
        self.classifier = complexity_classifier
        self.executor = executor
        self.validator = plan_validator

        self.planning_model = planning_model
        self.planning_temperature = planning_temperature
        self.synthesis_model = synthesis_model
        self.synthesis_temperature = synthesis_temperature

    async def create_tactical_plan(
        self,
        query: str,
        context: ConversationContext,
        available_tools: Optional[List[Any]] = None,
    ) -> ExecutionPlan:
        log_event(
            "================================================ TACTICAL PLANNING ================================================"
        )
        log_event("")

        tools_to_use = (
            available_tools if available_tools is not None else self.tools.list_tools()
        )

        prompt = TacticalPromptBuilder.build(
            query=query,
            context=context,
            available_tools=tools_to_use,
        )

        log_event(
            "------------------------------------------------ TACTICAL PLAN REQUEST ------------------------------------------------"
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
                "tactical_planner_llm_failed",
                {
                    "conversation_id": context.conversation_id,
                    "error": result.error,
                },
                level=logging.ERROR,
            )
            raise PlanningError(result.error)

        response = result.unwrap()

        log_event(
            "-------------------------------------- TACTICAL PLAN LLM RESPONSE --------------------------------------"
        )

        try:
            plan_data = json_loads_strict(
                response.content, allow_list=True, list_wrapper_key="tasks"
            )
            log_event(json.dumps(plan_data, indent=4))
        except Exception as e:
            log_event(
                "tactical_planner_json_parse_failed",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                    "content_preview": response.content[:5000],
                },
                level=logging.ERROR,
            )
            raise PlanningError(f"Invalid tactical plan JSON: {e}") from e

        try:
            raw_tasks = plan_data["tasks"]
            tasks: List[AgentTask] = []
            for t in raw_tasks:
                task_id = t.get("task_id")
                if not isinstance(task_id, str) or not task_id.strip():
                    raise PlanningError("Each task must include a non-empty 'task_id'")
                tasks.append(
                    AgentTask(
                        task_id=task_id.strip(),
                        tool_name=t["tool_name"],
                        description=t["description"],
                        requires_llm=bool(t.get("requires_llm", False)),
                        parameters=dict(t.get("parameters", {})),
                        depends_on=list(t.get("depends_on", [])),
                    )
                )
            plan = ExecutionPlan(
                tasks=tasks,
                estimated_time_seconds=int(plan_data.get("estimated_time_seconds", 0)),
                estimated_cost_usd=float(plan_data.get("estimated_cost_usd", 0.0)),
                reasoning=str(plan_data.get("reasoning", "")),
            )
            log_event(
                "tactical_plan_created",
                {
                    "tasks": [t.to_dict() for t in tasks],
                },
            )
        except Exception as e:
            log_event(
                "tactical_plan_construction_failed",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            raise PlanningError(f"Tactical plan construction failed: {e}") from e

        self.validator.validate(plan)

        return plan

    async def _synthesize_response(
        self,
        query: str,
        plan: ExecutionPlan,
        task_results: Dict[str, Any],
        context: Optional[ConversationContext] = None,
    ) -> AsyncGenerator[str, None]:
        prompt = SynthesisPromptBuilder.build(
            query=query, plan=plan, results=task_results
        )

        log_event(
            "-------------------------------------- SYNTHESIS PROMPT --------------------------------------"
        )
        log_event(prompt)

        async for chunk in self.llm.generate_stream(
            messages=[LLMMessage(role="user", content=prompt)],
            model=self.synthesis_model,
            temperature=self.synthesis_temperature,
        ):
            if context is not None and context.is_cancelled:
                log_event(
                    "synthesis_cancelled_during_stream",
                    {"conversation_id": context.conversation_id},
                )
                return
            yield getattr(chunk, "content", str(chunk))
