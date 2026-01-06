from typing import TYPE_CHECKING, Any, Callable, Mapping, Optional

from .agent_spawner import AgentSpawner
from .complexity_classifier import ComplexityClassifier
from .constants import AgentExecutionDefaults, AgentModelDefaults, AgentToolLimits
from .executor import TaskExecutor
from .plan_validator import PlanValidator
from .tool_registry import AgentToolRegistry

if TYPE_CHECKING:
    from ...llm import LLMProviderManager
    from .tactical_planner import TacticalPlanner


class TacticalPlannerFactory:

    def __init__(
        self,
        llm_provider_manager: "LLMProviderManager",
        tool_registry: AgentToolRegistry,
        complexity_classifier: ComplexityClassifier,
        *,
        on_observe: Optional[Callable[[str, Mapping[str, Any]], None]] = None,
        planning_model: str = AgentModelDefaults.PLANNING_MODEL,
        planning_temperature: float = AgentModelDefaults.PLANNING_TEMPERATURE,
        synthesis_model: str = AgentModelDefaults.SYNTHESIS_MODEL,
        synthesis_temperature: float = AgentModelDefaults.SYNTHESIS_TEMPERATURE,
        max_concurrency: int = AgentExecutionDefaults.MAX_CONCURRENCY,
        per_tool_limits: Optional[dict[str, int]] = None,
        max_tasks: int = AgentExecutionDefaults.MAX_TASKS,
        max_cost_usd: float = AgentExecutionDefaults.MAX_COST_USD,
        max_time_seconds: int = AgentExecutionDefaults.MAX_TIME_SECONDS,
    ):
        self.llm_provider_manager = llm_provider_manager
        self.tool_registry = tool_registry
        self.complexity_classifier = complexity_classifier
        self.on_observe = on_observe
        self.planning_model = planning_model
        self.planning_temperature = planning_temperature
        self.synthesis_model = synthesis_model
        self.synthesis_temperature = synthesis_temperature
        self.max_concurrency = max_concurrency
        self.per_tool_limits = per_tool_limits or AgentToolLimits.get_per_tool_limits()
        self.max_tasks = max_tasks
        self.max_cost_usd = max_cost_usd
        self.max_time_seconds = max_time_seconds

    def create(self) -> "TacticalPlanner":
        from .tactical_planner import TacticalPlanner

        agent_spawner = AgentSpawner(
            llm_provider_manager=self.llm_provider_manager,
            tool_registry=self.tool_registry,
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
            plan_validator=plan_validator,
            on_observe=self.on_observe,
            planning_model=self.planning_model,
            planning_temperature=self.planning_temperature,
            synthesis_model=self.synthesis_model,
            synthesis_temperature=self.synthesis_temperature,
        )
