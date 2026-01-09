import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import ValidationError

from ...utils.logx import log_event
from .exceptions import PlanningError
from .models.task import AgentTask, ExecutionPlan
from .models.validation import ValidationResult
from .tool_registry import AgentToolRegistry
from .utils.dag_validator import validate_dag, validate_node_structure


class PlanValidator:

    def __init__(
        self,
        tool_registry: AgentToolRegistry,
        max_tasks: int = 20,
        max_cost_usd: float = 1.0,
        max_time_seconds: int = 300,
    ):
        self.tools = tool_registry
        self.max_tasks = max_tasks
        self.max_cost_usd = max_cost_usd
        self.max_time_seconds = max_time_seconds

    def validate(self, plan: ExecutionPlan) -> None:
        result = self._validate_plan(plan)

        if result.warnings:
            log_event(
                "validator_warnings",
                {
                    "warning_count": len(result.warnings),
                    "warnings": result.warnings,
                },
                level=logging.WARNING,
            )

        if not result.is_valid:
            log_event(
                "validator_validation_failed",
                {
                    "error_count": len(result.errors),
                    "errors": result.errors,
                },
                level=logging.ERROR,
            )
            msg = "Plan validation failed:\n" + "\n".join(
                f"  - {e}" for e in result.errors
            )
            raise PlanningError(msg)

    def _validate_plan(self, plan: ExecutionPlan) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        errors.extend(self._validate_structure(plan.tasks))
        errors.extend(self._validate_tools_and_params(plan))
        errors.extend(self._validate_semantics(plan))
        g_errors, g_warnings = self._validate_graph(plan.tasks)
        errors.extend(g_errors)
        warnings.extend(g_warnings)

        if errors:
            return ValidationResult.failure(errors)
        return ValidationResult.success(warnings)

    def _validate_structure(self, tasks: List[AgentTask]) -> List[str]:
        errors: List[str] = []

        if not tasks:
            return ["Plan contains no tasks"]

        task_ids = []
        for t in tasks:
            if not getattr(t, "task_id", None):
                errors.append("Each task must include a non-empty 'task_id'")
            else:
                task_ids.append(t.task_id)

        dependencies = {t.task_id: t.depends_on for t in tasks if t.task_id}

        structure_errors = validate_node_structure(
            node_ids=task_ids,
            dependencies=dependencies,
            node_type_name="task",
            max_nodes=self.max_tasks,
        )

        for err in structure_errors:
            if "Must have at least one" not in err:
                errors.append(err)

        for t in tasks:
            if not self.tools.has_tool(t.tool_name):
                errors.append(
                    f"Task '{t.task_id}' references unknown tool: '{t.tool_name}'"
                )

        return errors

    def _validate_tools_and_params(self, plan: ExecutionPlan) -> List[str]:
        errors: List[str] = []
        for t in plan.tasks:
            tool = self.tools.get_tool(t.tool_name)
            if not tool:
                continue
            if tool.input_model is None:
                errors.append(
                    f"Tool '{tool.name}' missing input_model (Pydantic BaseModel)"
                )
                continue

            model = tool.input_model
            try:
                model.model_validate(t.parameters)
            except ValidationError as ve:
                for err in ve.errors():
                    loc = ".".join(map(str, err.get("loc", []))) or "<root>"
                    msg = err.get("msg", "invalid parameter")
                    errors.append(
                        f"Task '{t.task_id}' params invalid for '{tool.name}' at {loc}: {msg}"
                    )
        return errors

    def _validate_semantics(self, plan: ExecutionPlan) -> List[str]:
        errors: List[str] = []

        if plan.estimated_cost_usd > self.max_cost_usd:
            errors.append(
                f"Plan exceeds cost budget: ${plan.estimated_cost_usd:.4f} > ${self.max_cost_usd:.4f}"
            )
        if plan.estimated_time_seconds > self.max_time_seconds:
            errors.append(
                f"Plan exceeds time budget: {plan.estimated_time_seconds}s > {self.max_time_seconds}s"
            )

        return errors

    def _validate_parameter_type(
        self, value: Any, schema: Dict[str, Any]
    ) -> Optional[str]:
        expected_type = schema.get("type")
        if not expected_type:
            return None

        py_map: Dict[str, Union[type, tuple[type, ...]]] = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        py_t: Union[type, tuple[type, ...], None] = py_map.get(expected_type)
        if py_t is not None and not isinstance(value, py_t):
            return f"expected {expected_type}, got {type(value).__name__}"

        if expected_type == "array" and "items" in schema:
            subtype = schema["items"].get("type")
            if subtype and isinstance(value, list):
                sub_py: Union[type, tuple[type, ...], None] = py_map.get(subtype)
                if sub_py is not None and not all(
                    isinstance(it, sub_py) for it in value
                ):
                    return f"array items must be {subtype}"
        return None

    def _validate_graph(self, tasks: List[AgentTask]) -> Tuple[List[str], List[str]]:
        if not tasks:
            return [], []

        node_ids = {t.task_id for t in tasks if t.task_id}
        dependencies = {t.task_id: t.depends_on for t in tasks if t.task_id}

        result = validate_dag(
            node_ids=node_ids,
            dependencies=dependencies,
            node_type_name="task",
            allow_isolated=True,
        )

        return list(result.errors), list(result.warnings)
