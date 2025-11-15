from typing import Dict, List, Optional, Set

from .exceptions import PlanningError
from .models.task import AgentTask, ExecutionPlan
from .models.validation import ValidationResult
from .tool_registry import AgentToolRegistry


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

        if not result.is_valid:
            error_msg = "Plan validation failed:\n" + "\n".join(
                f"  - {error}" for error in result.errors
            )
            raise PlanningError(error_msg)

    def _validate_plan(self, plan: ExecutionPlan) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        structural_errors = self._validate_structure(plan.tasks)
        errors.extend(structural_errors)

        semantic_errors = self._validate_semantics(plan)
        errors.extend(semantic_errors)

        graph_errors, graph_warnings = self._validate_graph(plan.tasks)
        errors.extend(graph_errors)
        warnings.extend(graph_warnings)

        if errors:
            return ValidationResult.failure(errors)

        return ValidationResult.success(warnings)

    def _validate_structure(self, tasks: List[AgentTask]) -> List[str]:
        errors: List[str] = []

        if not tasks:
            errors.append("Plan contains no tasks")
            return errors

        if len(tasks) > self.max_tasks:
            errors.append(
                f"Plan exceeds maximum task limit: {len(tasks)} > {self.max_tasks}"
            )

        task_ids = [task.task_id for task in tasks]
        if len(task_ids) != len(set(task_ids)):
            duplicates = [tid for tid in task_ids if task_ids.count(tid) > 1]
            errors.append(f"Duplicate task IDs found: {set(duplicates)}")

        task_id_set = set(task_ids)
        for task in tasks:
            if not self.tools.has_tool(task.tool_name):
                errors.append(
                    f"Task '{task.task_id}' references unknown tool: '{task.tool_name}'"
                )

            for dep_id in task.depends_on:
                if dep_id not in task_id_set:
                    errors.append(
                        f"Task '{task.task_id}' depends on non-existent task: '{dep_id}'"
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

        for task in plan.tasks:
            tool = self.tools.get_tool(task.tool_name)
            if not tool:
                continue

            param_errors = self._validate_task_parameters(task, tool)
            errors.extend(param_errors)

        return errors

    def _validate_task_parameters(self, task: AgentTask, tool) -> List[str]:
        errors: List[str] = []

        try:
            schema = tool.input_schema
            if not schema:
                return errors

            required_params = schema.get("required", [])
            provided_params = set(task.parameters.keys())

            missing = set(required_params) - provided_params
            if missing:
                errors.append(
                    f"Task '{task.task_id}' missing required parameters: {missing}"
                )

            properties = schema.get("properties", {})
            for param_name, param_value in task.parameters.items():
                if param_name not in properties:
                    continue

                param_schema = properties[param_name]
                type_error = self._validate_parameter_type(param_value, param_schema)
                if type_error:
                    errors.append(
                        f"Task '{task.task_id}' parameter '{param_name}': {type_error}"
                    )

        except Exception:
            pass

        return errors

    def _validate_parameter_type(self, value, schema: Dict) -> Optional[str]:
        expected_type = schema.get("type")
        if not expected_type:
            return None

        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        expected_python_type = type_map.get(expected_type)
        if not expected_python_type:
            return None

        if not isinstance(value, expected_python_type):
            return f"expected {expected_type}, got {type(value).__name__}"

        if expected_type == "array" and "items" in schema:
            item_type = schema["items"].get("type")
            if item_type and value:
                item_python_type = type_map.get(item_type)
                if item_python_type and not all(
                    isinstance(item, item_python_type) for item in value
                ):
                    return f"array items must be {item_type}"

        return None

    def _validate_graph(self, tasks: List[AgentTask]) -> tuple[List[str], List[str]]:
        errors: List[str] = []
        warnings: List[str] = []

        if self._has_circular_dependency(tasks):
            errors.append("Plan contains circular dependencies")

        unreachable = self._find_unreachable_tasks(tasks)
        if unreachable:
            errors.append(f"Unreachable tasks detected: {unreachable}")

        isolated = self._find_isolated_tasks(tasks)
        if isolated:
            warnings.append(
                f"Tasks with no dependencies or dependents: {isolated} (may be intentional)"
            )

        return errors, warnings

    def _has_circular_dependency(self, tasks: List[AgentTask]) -> bool:
        task_map = {task.task_id: task for task in tasks}

        def has_cycle(task_id: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = task_map.get(task_id)
            if not task:
                return False

            for dep_id in task.depends_on:
                if dep_id not in visited:
                    if has_cycle(dep_id, visited, rec_stack):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        visited: Set[str] = set()
        for task in tasks:
            if task.task_id not in visited:
                if has_cycle(task.task_id, visited, set()):
                    return True

        return False

    def _find_unreachable_tasks(self, tasks: List[AgentTask]) -> List[str]:
        if not tasks:
            return []

        task_map = {task.task_id: task for task in tasks}
        all_task_ids = set(task_map.keys())

        root_tasks = [task for task in tasks if not task.depends_on]
        if not root_tasks:
            return []

        reachable: Set[str] = set()

        def mark_reachable(task_id: str) -> None:
            if task_id in reachable:
                return
            reachable.add(task_id)

            for task in tasks:
                if task_id in task.depends_on:
                    mark_reachable(task.task_id)

        for root_task in root_tasks:
            mark_reachable(root_task.task_id)

        unreachable = all_task_ids - reachable
        return sorted(unreachable)

    def _find_isolated_tasks(self, tasks: List[AgentTask]) -> List[str]:
        isolated = []

        for task in tasks:
            has_dependencies = bool(task.depends_on)

            is_dependency = any(task.task_id in t.depends_on for t in tasks)

            if not has_dependencies and not is_dependency and len(tasks) > 1:
                isolated.append(task.task_id)

        return isolated
