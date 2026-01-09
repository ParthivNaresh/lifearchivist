import logging
from typing import List, Tuple

from ...utils.logx import log_event
from .constants import AgentExecutionDefaults
from .exceptions import PlanningError
from .models.strategic_plan import StrategicPhase, StrategicPlan
from .models.validation import ValidationResult
from .tool_registry import AgentToolRegistry
from .utils.dag_validator import validate_dag, validate_node_structure


class StrategicPlanValidator:

    def __init__(
        self,
        tool_registry: AgentToolRegistry,
        *,
        max_phases: int = AgentExecutionDefaults.MAX_PHASES,
        max_cost_usd: float = AgentExecutionDefaults.MAX_COST_USD,
        max_time_seconds: int = AgentExecutionDefaults.MAX_TIME_SECONDS,
    ):
        self.tools = tool_registry
        self.max_phases = max_phases
        self.max_cost_usd = max_cost_usd
        self.max_time_seconds = max_time_seconds

    def validate(self, plan: StrategicPlan) -> None:
        result = self._validate_plan(plan)

        if result.warnings:
            log_event(
                "strategic_validator_warnings",
                {
                    "warning_count": len(result.warnings),
                    "warnings": result.warnings,
                },
                level=logging.WARNING,
            )

        if not result.is_valid:
            log_event(
                "strategic_validator_validation_failed",
                {
                    "error_count": len(result.errors),
                    "errors": result.errors,
                },
                level=logging.ERROR,
            )
            msg = "Strategic plan validation failed:\n" + "\n".join(
                f"  - {e}" for e in result.errors
            )
            raise PlanningError(msg)

    def _validate_plan(self, plan: StrategicPlan) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        errors.extend(self._validate_structure(plan.phases))
        warnings.extend(self._validate_tools(plan.phases))
        errors.extend(self._validate_semantics(plan))
        g_errors, g_warnings = self._validate_graph(plan.phases)
        errors.extend(g_errors)
        warnings.extend(g_warnings)

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success(warnings)

    def _validate_structure(self, phases: List[StrategicPhase]) -> List[str]:
        errors: List[str] = []

        if not phases:
            return ["Strategic plan must have at least one phase"]

        phase_ids = [p.phase_id for p in phases]
        dependencies = {p.phase_id: p.depends_on for p in phases}

        structure_errors = validate_node_structure(
            node_ids=phase_ids,
            dependencies=dependencies,
            node_type_name="phase",
            max_nodes=self.max_phases,
        )

        for err in structure_errors:
            if "Must have at least one" not in err:
                errors.append(err)

        return errors

    def _validate_tools(self, phases: List[StrategicPhase]) -> List[str]:
        warnings: List[str] = []

        for phase in phases:
            for tool_name in phase.required_tools:
                if not self.tools.has_tool(tool_name):
                    warnings.append(
                        f"Phase '{phase.phase_id}' references unknown tool: '{tool_name}'"
                    )

        return warnings

    def _validate_semantics(self, plan: StrategicPlan) -> List[str]:
        errors: List[str] = []

        if plan.estimated_cost_usd > self.max_cost_usd:
            errors.append(
                f"Strategic plan exceeds cost budget: ${plan.estimated_cost_usd:.4f} > ${self.max_cost_usd:.4f}"
            )
        if plan.estimated_time_seconds > self.max_time_seconds:
            errors.append(
                f"Strategic plan exceeds time budget: {plan.estimated_time_seconds}s > {self.max_time_seconds}s"
            )

        return errors

    def _validate_graph(
        self, phases: List[StrategicPhase]
    ) -> Tuple[List[str], List[str]]:
        if not phases:
            return [], []

        node_ids = {p.phase_id for p in phases}
        dependencies = {p.phase_id: p.depends_on for p in phases}

        result = validate_dag(
            node_ids=node_ids,
            dependencies=dependencies,
            node_type_name="phase",
            allow_isolated=True,
        )

        return list(result.errors), list(result.warnings)
