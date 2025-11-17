import json
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    cast,
)

from ...llm import LLMMessage
from .complexity_classifier import ComplexityClassifier
from .constants import MAX_JSON_CHARS
from .exceptions import PlanningError
from .executor import TaskExecutor
from .models.context import ConversationContext
from .models.events import AgentEvent, AgentEventType
from .models.query import QueryComplexity
from .models.task import AgentTask, ExecutionPlan
from .plan_validator import PlanValidator
from .tool_registry import AgentToolRegistry
from .utils.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from llm import LLMProviderManager


class AgentOrchestrator:
    """
    Orchestrates:
      1) complexity classification
      2) plan creation (LLM)
      3) validation
      4) plan execution (streaming events)
      5) synthesis (streaming chunks)
    Emits only AgentEvents; never tears down the stream with exceptions.
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
        on_observe: Optional[
            Callable[[str, Mapping[str, Any]], None]
        ] = None,  # callable(event_name: str, fields: dict)
        planning_model: str = "gpt-4o",
        planning_temperature: float = 0.2,
        synthesis_model: str = "gpt-4o",
        synthesis_temperature: float = 0.7,
        max_plan_reasoning_chars: int = 2000,  # trim reasoning echoed in events
        max_param_preview_chars: int = 256,  # trim per-param preview in events
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
        High-level pipeline that yields AgentEvents:
        COMPLEXITY_CLASSIFIED -> (maybe ERROR) ->
        PLAN_CREATED -> (TASK_*... -> PLAN_COMPLETED | PLAN_FAILED) ->
        SYNTHESIS_* -> COMPLETE
        """
        # 1) Complexity classification
        try:
            classification = await self.classifier.classify(query, context)
        except Exception as e:
            # If classification itself fails, emit a soft error and end.
            self._observe("classifier_error", error=str(e))
            yield AgentEvent.error(f"Classification failed: {e}")
            yield AgentEvent.complete()
            return

        yield AgentEvent.complexity_classified(classification)

        if classification.complexity == QueryComplexity.SIMPLE:
            # Route-away behavior (upstream router can handle).
            msg = "Simple query detected — should be routed to retrieval/Q&A, not the multi-step agent."
            self._observe("routed_simple_query", reason=msg)
            yield AgentEvent.error(msg)
            yield AgentEvent.complete()
            return

        # 2) Build & validate plan (LLM -> JSON -> ExecutionPlan)
        try:
            plan = await self._create_execution_plan(query, context)
        except PlanningError as e:
            self._observe("planning_error", error=str(e))
            yield AgentEvent.plan_failed(str(e))
            yield AgentEvent.complete()
            return
        except Exception as e:
            self._observe("planning_exception", error=str(e))
            yield AgentEvent.plan_failed(f"Planning exception: {e}")
            yield AgentEvent.complete()
            return

        # Emit a compact, JSON-safe plan summary
        yield AgentEvent(
            type=AgentEventType.PLAN_CREATED,
            data=self._summarize_plan(plan),
        )

        # 3) Execute plan, collect results for synthesis
        task_results: Dict[str, Any] = {}
        plan_failed = False

        async for ev in self.executor.execute_plan(plan, context):
            # Surface execution events
            yield ev

            # Track results for synthesis
            if ev.type == AgentEventType.TASK_COMPLETED and ev.task_id:
                task_results[ev.task_id] = ev.data

            if ev.type == AgentEventType.PLAN_FAILED:
                plan_failed = True

        # 4) Synthesis (only if plan succeeded)
        if not plan_failed:
            yield AgentEvent.synthesis_started()
            try:
                async for chunk in self._synthesize_response(query, plan, task_results):
                    yield AgentEvent.response_chunk(chunk)
            except Exception as e:
                self._observe("synthesis_error", error=str(e))
                yield AgentEvent.error(f"Synthesis failed: {e}")

        # 5) Done
        yield AgentEvent.complete()

    async def _create_execution_plan(
        self, query: str, context: ConversationContext
    ) -> ExecutionPlan:
        prompt = self.prompt_builder.build_planning_prompt(
            query=query, context=context, available_tools=self.tools.list_tools()
        )

        # Ask the LLM to produce JSON
        result = await self.llm.generate(
            messages=[LLMMessage(role="user", content=prompt)],
            model=self.planning_model,
            temperature=self.planning_temperature,
            response_format={"type": "json_object"},
        )

        if result.is_failure():
            raise PlanningError(result.error)

        response = result.unwrap()
        try:
            plan_data = self._json_loads_strict(response.content)
        except Exception as e:
            raise PlanningError(f"Invalid plan JSON: {e}") from e

        # Construct ExecutionPlan
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
        except Exception as e:
            raise PlanningError(f"Plan construction failed: {e}") from e

        # Validate (raises PlanningError on invalid)
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
        async for chunk in self.llm.generate_stream(
            messages=[LLMMessage(role="user", content=prompt)],
            model=self.synthesis_model,
            temperature=self.synthesis_temperature,
        ):
            # Provider chunks typically have .content
            yield getattr(chunk, "content", str(chunk))

    def _summarize_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """
        Compact, JSON-safe plan summary for PLAN_CREATED event.
        Prevents giant or non-serializable payloads.
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
        """
        Produce a shallow, compact preview of parameters for event payloads.
        Strings are trimmed; lists/dicts show sizes.
        """
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

    def _json_loads_strict(self, s: str) -> Dict[str, Any]:
        """
        Strict JSON parse with a helpful error on failure.
        """
        if len(s) > MAX_JSON_CHARS:
            raise ValueError(f"LLM JSON exceeds {MAX_JSON_CHARS} chars")
        try:
            return cast(Dict[str, Any], json.loads(s))
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON decode error at pos {e.pos}: {e.msg}") from e

    def _observe(self, event: str, **fields: Any) -> None:
        if callable(self._obs):
            try:
                self._obs(event, dict(fields))
            except Exception:
                # Never let observability break control flow
                pass
