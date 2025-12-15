import json
import logging
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
)

from ...llm import LLMMessage
from ...utils.logx import log_event
from .complexity_classifier import ComplexityClassifier
from .exceptions import PlanningError
from .executor import TaskExecutor
from .models.context import ConversationContext
from .models.events import AgentEvent, AgentEventType
from .models.task import AgentTask, ExecutionPlan
from .plan_validator import PlanValidator
from .tool_registry import AgentToolRegistry
from .utils import PromptBuilder, json_loads_strict

if TYPE_CHECKING:
    from llm import LLMProviderManager


class TacticalPlanner:
    """
    Tactical Planner: Creates detailed task DAGs from goals.

    Responsibilities:
    - Convert goals (user queries or phase descriptions) into task DAGs
    - Validate plans
    - Execute tasks via executor
    - Synthesize final responses

    Can be used standalone (direct planning) or as part of hierarchical system
    (tactical planning for phases).
    """

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        complexity_classifier: ComplexityClassifier,
        executor: TaskExecutor,
        prompt_builder: PromptBuilder,
        plan_validator: PlanValidator,
        *,
        on_observe: Optional[Callable[[str, Mapping[str, Any]], None]] = None,
        planning_model: str = "qwen2.5:7b",
        planning_temperature: float = 0.2,
        synthesis_model: str = "qwen2.5:7b",
        synthesis_temperature: float = 0.7,
        max_plan_reasoning_chars: int = 2000,
        max_param_preview_chars: int = 256,
    ):
        self.llm = llm_provider_manager
        self.tools = tool_registry
        self.classifier = complexity_classifier
        self.executor = executor
        self.prompt_builder = prompt_builder
        self.validator = plan_validator

        self._obs = on_observe
        self.planning_model = planning_model
        self.planning_temperature = planning_temperature
        self.synthesis_model = synthesis_model
        self.synthesis_temperature = synthesis_temperature
        self.max_plan_reasoning_chars = max_plan_reasoning_chars
        self.max_param_preview_chars = max_param_preview_chars

    async def process_query(
        self, query: str, context: ConversationContext
    ) -> AsyncGenerator[AgentEvent, None]:
        """
        Process query end-to-end: plan → execute → synthesize.
        """
        try:
            plan = await self.create_tactical_plan(query, context)
        except PlanningError as e:
            log_event(
                "tactical_planner_planning_error",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                },
                level=logging.ERROR,
            )
            self._observe("planning_error", error=str(e))
            yield AgentEvent.plan_failed(str(e))
            yield AgentEvent.complete()
            return
        except Exception as e:
            log_event(
                "tactical_planner_planning_exception",
                {
                    "conversation_id": context.conversation_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                level=logging.ERROR,
            )
            self._observe("planning_exception", error=str(e))
            yield AgentEvent.plan_failed(f"Planning exception: {e}")
            yield AgentEvent.complete()
            return

        yield AgentEvent(
            type=AgentEventType.PLAN_CREATED,
            data=self._summarize_plan(plan),
        )

        task_results: Dict[str, Any] = {}
        plan_failed = False

        async for ev in self.executor.execute_plan(plan, context):
            yield ev

            if ev.type == AgentEventType.TASK_COMPLETED and ev.task_id:
                task_results[ev.task_id] = ev.data

            if ev.type == AgentEventType.PLAN_FAILED:
                plan_failed = True

        if plan_failed:
            log_event(
                "tactical_planner_execution_failed",
                {
                    "conversation_id": context.conversation_id,
                    "completed_tasks": len(task_results),
                    "total_tasks": len(plan.tasks),
                },
                level=logging.ERROR,
            )
        else:
            log_event(
                "------------------------------------------------ TASK RESULTS ------------------------------------------------"
            )
            log_event(json.dumps(task_results, indent=2))

        if not plan_failed:
            log_event(
                "------------------------------------------------ STARTING TACTICAL PLANNER SYNTHESIS ------------------------------------------------"
            )
            yield AgentEvent.synthesis_started()
            try:
                chunks = ""
                async for chunk in self._synthesize_response(query, plan, task_results):
                    chunks += chunk
                    yield AgentEvent.response_chunk(chunk)

                log_event(
                    "------------------------------------------------ FINISHED TACTICAL PLANNER SYNTHESIS ------------------------------------------------"
                )
                log_event(json.dumps({"Synthesized": chunks}, indent=2))
            except Exception as e:
                log_event(
                    "tactical_planner_synthesis_failed",
                    {
                        "conversation_id": context.conversation_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    level=logging.ERROR,
                )
                self._observe("synthesis_error", error=str(e))
                yield AgentEvent.error(f"Synthesis failed: {e}")

        yield AgentEvent.complete()

    async def create_tactical_plan(
        self,
        query: str,
        context: ConversationContext,
        available_tools: Optional[List[Any]] = None,
    ) -> ExecutionPlan:
        """
        Create detailed task DAG from a goal (query or phase description).

        Args:
            query: Goal to accomplish
            context: Conversation context
            available_tools: Tools to use (defaults to all tools)

        Returns:
            ExecutionPlan with validated task DAG
        """
        log_event(
            "================================================ TACTICAL PLANNING ================================================"
        )
        log_event("")

        tools_to_use = (
            available_tools if available_tools is not None else self.tools.list_tools()
        )

        prompt = self.prompt_builder.build_planning_prompt(
            query=query, context=context, available_tools=tools_to_use
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
        self, query: str, plan: ExecutionPlan, task_results: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Streams final answer text (already chunked by provider).
        """
        prompt = self.prompt_builder.build_synthesis_prompt(
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
            yield getattr(chunk, "content", str(chunk))

    def _summarize_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Compact, JSON-safe plan summary for PLAN_CREATED event.
        """
        return {
            "estimated_time_seconds": int(plan.estimated_time_seconds),
            "estimated_cost_usd": float(plan.estimated_cost_usd),
            "reasoning": (plan.reasoning or "")[: self.max_plan_reasoning_chars],
            "tasks": [
                {
                    "task_id": t.task_id,
                    "tool": t.tool_name,
                    "requires_llm": bool(t.requires_llm),
                    "depends_on": list(t.depends_on or []),
                    "parameters_preview": self._preview_params(t.parameters or {}),
                }
                for t in plan.tasks
            ],
        }

    def _preview_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        preview: Dict[str, Any] = {}
        for k, v in params.items():
            if isinstance(v, str):
                preview[k] = v[: self.max_param_preview_chars]
            elif isinstance(v, (int, float, bool)) or v is None:
                preview[k] = v
            elif isinstance(v, list):
                preview[k] = {"type": "list", "len": len(v)}
            elif isinstance(v, dict):
                preview[k] = {"type": "object", "keys": list(v.keys())[:10]}
            else:
                preview[k] = {"type": type(v).__name__}
        return preview

    def _observe(self, event: str, **fields: Any) -> None:
        if callable(self._obs):
            try:
                self._obs(event, dict(fields))
            except Exception:
                pass
