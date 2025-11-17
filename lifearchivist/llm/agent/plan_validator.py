from collections import Counter, deque
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import ValidationError

from .exceptions import PlanningError
from .models.task import AgentTask, ExecutionPlan
from .models.validation import ValidationResult
from .tool_registry import AgentToolRegistry


class PlanValidator:
    """
    Validates a plan for structural correctness, semantics, and graph soundness.

    Improvements:
      - O(n) duplicate detection (Counter)
      - Self-dependency detection
      - Per-tool existence checks
      - Parameter type and presence checks against tool.input_schema
      - Budget checks (time & cost)
      - Graph checks using Kahn's algorithm (cycles) and reachability from roots
      - Clear warnings for isolated tasks
    """

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

    # Public API
    def validate(self, plan: ExecutionPlan) -> None:
        result = self._validate_plan(plan)
        if not result.is_valid:
            msg = "Plan validation failed:\n" + "\n".join(
                f"  - {e}" for e in result.errors
            )
            raise PlanningError(msg)
        # You may want to surface warnings upstream as events/logs
        # (e.g., AgentEvent of type PLAN_VALIDATED with warnings)

    # Internal
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

        if len(tasks) > self.max_tasks:
            errors.append(
                f"Plan exceeds maximum task limit: {len(tasks)} > {self.max_tasks}"
            )

        # task_id presence and format
        ids = []
        for t in tasks:
            if not getattr(t, "task_id", None):
                errors.append("Each task must include a non-empty 'task_id'")
            else:
                ids.append(t.task_id)

        # Duplicate IDs (O(n))
        counts = Counter(ids)
        dups = [tid for tid, c in counts.items() if c > 1]
        if dups:
            errors.append(f"Duplicate task IDs found: {sorted(dups)}")

        # Tool existence and dependency checks
        id_set = set(ids)
        for t in tasks:
            if not self.tools.has_tool(t.tool_name):
                errors.append(
                    f"Task '{t.task_id}' references unknown tool: '{t.tool_name}'"
                )

            # Self-dependency
            if t.task_id in t.depends_on:
                errors.append(f"Task '{t.task_id}' has a self-dependency")

            # Non-existent dependencies
            missing = [d for d in t.depends_on if d not in id_set]
            if missing:
                errors.append(
                    f"Task '{t.task_id}' depends on non-existent tasks: {sorted(missing)}"
                )

            # Duplicate dependencies within a task
            dep_counts = Counter(t.depends_on)
            dup_deps = [d for d, c in dep_counts.items() if c > 1]
            if dup_deps:
                errors.append(
                    f"Task '{t.task_id}' lists duplicate dependencies: {sorted(dup_deps)}"
                )

        return errors

    def _validate_tools_and_params(self, plan: ExecutionPlan) -> List[str]:
        errors: List[str] = []
        for t in plan.tasks:
            tool = self.tools.get_tool(t.tool_name)
            if not tool:
                errors.append(
                    f"Task '{t.task_id}' references unknown tool: '{t.tool_name}'"
                )
                continue
            if tool.input_model is None:
                errors.append(
                    f"Tool '{tool.name}' missing input_model (Pydantic BaseModel)"
                )
                continue

            model = tool.input_model
            try:
                # This also normalizes types (e.g., str->int coercion if allowed)
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

        # Budget checks
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
        """
        Uses Kahn's algorithm to detect cycles and computes reachability from roots.
        """
        errors: List[str] = []
        warnings: List[str] = []

        if not tasks:
            return errors, warnings

        # Build graph: edge dep -> task
        id_to_task = {t.task_id: t for t in tasks}
        all_ids = set(id_to_task.keys())

        indeg: Dict[str, int] = {tid: 0 for tid in all_ids}
        adj: Dict[str, List[str]] = {tid: [] for tid in all_ids}

        for t in tasks:
            for dep in t.depends_on:
                if dep in all_ids:
                    adj[dep].append(t.task_id)
                    indeg[t.task_id] += 1

        roots = [tid for tid, d in indeg.items() if d == 0]
        if not roots:
            # If there are no roots and there are tasks, either a cycle exists or non-existent deps already reported.
            # Kahn's will report cycles precisely below.
            pass

        # Kahn's algorithm for cycle detection & topological order
        q = deque(roots)
        visited: List[str] = []

        while q:
            u = q.popleft()
            visited.append(u)
            for v in adj[u]:
                indeg[v] -= 1
                if indeg[v] == 0:
                    q.append(v)

        if len(visited) != len(all_ids):
            cyclic = sorted(all_ids - set(visited))
            errors.append(f"Plan contains circular dependencies among: {cyclic}")

        # Reachability from roots (ignoring cycles already flagged)
        reachable: Set[str] = set()
        rq = deque(roots)
        while rq:
            u = rq.popleft()
            if u in reachable:
                continue
            reachable.add(u)
            for v in adj[u]:
                rq.append(v)

        unreachable = sorted(all_ids - reachable)
        if roots and unreachable:
            errors.append(
                f"Unreachable tasks detected (no path from any root): {unreachable}"
            )

        # Isolated tasks (no deps and no dependents) are likely dangling work
        isolated = sorted(
            t.task_id for t in tasks if not t.depends_on and not adj[t.task_id]
        )
        if len(tasks) > 1 and isolated:
            warnings.append(
                f"Tasks with no dependencies or dependents: {isolated} (verify intent)"
            )

        return errors, warnings
