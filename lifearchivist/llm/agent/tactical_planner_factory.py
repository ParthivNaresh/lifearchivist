from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional

from .agent_spawner import AgentSpawner
from .complexity_classifier import ComplexityClassifier
from .executor import TaskExecutor
from .plan_validator import PlanValidator
from .tool_registry import AgentToolRegistry
from .utils.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from ...llm import LLMProviderManager
    from .tactical_planner import TacticalPlanner


class TacticalPlannerFactory:
    """
    Factory for creating TacticalPlanner (AgentOrchestrator) instances.

    Each phase gets its own isolated TacticalPlanner with its own:
    - Executor (with independent concurrency limits)
    - Agent spawner
    - Plan validator

    This ensures phase isolation and enables parallel execution.
    """

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        prompt_builder: PromptBuilder,
        complexity_classifier: ComplexityClassifier,
        *,
        on_observe: Optional[Callable[[str, Mapping[str, Any]], None]] = None,
        planning_model: str = "qwen2.5:7b",
        planning_temperature: float = 0.2,
        synthesis_model: str = "qwen2.5:7b",
        synthesis_temperature: float = 0.7,
        max_concurrency: int = 32,
        per_tool_limits: Optional[dict[str, int]] = None,
        max_tasks: int = 20,
        max_cost_usd: float = 1.0,
        max_time_seconds: int = 300,
    ):
        self.llm_provider_manager = llm_provider_manager
        self.tool_registry = tool_registry
        self.prompt_builder = prompt_builder
        self.complexity_classifier = complexity_classifier
        self.on_observe = on_observe
        self.planning_model = planning_model
        self.planning_temperature = planning_temperature
        self.synthesis_model = synthesis_model
        self.synthesis_temperature = synthesis_temperature
        self.max_concurrency = max_concurrency
        self.per_tool_limits = per_tool_limits or {"structured_extraction": 8}
        self.max_tasks = max_tasks
        self.max_cost_usd = max_cost_usd
        self.max_time_seconds = max_time_seconds

    def create(self) -> "TacticalPlanner":
        """
        Create a new TacticalPlanner instance with isolated resources.

        Returns:
            Fresh TacticalPlanner instance
        """
        from .tactical_planner import TacticalPlanner

        agent_spawner = AgentSpawner(
            llm_provider_manager=self.llm_provider_manager,
            tool_registry=self.tool_registry,
            prompt_builder=self.prompt_builder,
            task_timeout_s=60.0,
            max_retries=2,
            max_history_messages=50,
            max_dependent_bytes=256 * 1024,
        )

        executor = TaskExecutor(
            agent_spawner,
            max_concurrency=self.max_concurrency,
            per_tool_limits=self.per_tool_limits,
            fail_fast=True,
            on_observe=self.on_observe,
        )

        plan_validator = PlanValidator(
            tool_registry=self.tool_registry,
            max_tasks=self.max_tasks,
            max_cost_usd=self.max_cost_usd,
            max_time_seconds=self.max_time_seconds,
        )

        return TacticalPlanner(
            llm_provider_manager=self.llm_provider_manager,
            tool_registry=self.tool_registry,
            complexity_classifier=self.complexity_classifier,
            executor=executor,
            prompt_builder=self.prompt_builder,
            plan_validator=plan_validator,
            on_observe=self.on_observe,
            planning_model=self.planning_model,
            planning_temperature=self.planning_temperature,
            synthesis_model=self.synthesis_model,
            synthesis_temperature=self.synthesis_temperature,
        )
