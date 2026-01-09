from collections import Counter, deque
from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Mapping, Set, Tuple


@dataclass(frozen=True, slots=True)
class DAGValidationResult:
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    topological_order: Tuple[str, ...]
    roots: FrozenSet[str]
    cyclic_nodes: FrozenSet[str]
    unreachable_nodes: FrozenSet[str]
    isolated_nodes: FrozenSet[str]

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    @classmethod
    def success(
        cls,
        topological_order: List[str],
        roots: Set[str],
        isolated_nodes: Set[str],
        warnings: List[str],
    ) -> "DAGValidationResult":
        return cls(
            errors=(),
            warnings=tuple(warnings),
            topological_order=tuple(topological_order),
            roots=frozenset(roots),
            cyclic_nodes=frozenset(),
            unreachable_nodes=frozenset(),
            isolated_nodes=frozenset(isolated_nodes),
        )

    @classmethod
    def failure(
        cls,
        errors: List[str],
        warnings: List[str],
        cyclic_nodes: Set[str],
        unreachable_nodes: Set[str],
        isolated_nodes: Set[str],
        partial_order: List[str],
        roots: Set[str],
    ) -> "DAGValidationResult":
        return cls(
            errors=tuple(errors),
            warnings=tuple(warnings),
            topological_order=tuple(partial_order),
            roots=frozenset(roots),
            cyclic_nodes=frozenset(cyclic_nodes),
            unreachable_nodes=frozenset(unreachable_nodes),
            isolated_nodes=frozenset(isolated_nodes),
        )


def validate_dag(
    node_ids: Set[str],
    dependencies: Mapping[str, List[str]],
    *,
    node_type_name: str = "node",
    allow_isolated: bool = False,
) -> DAGValidationResult:
    if not node_ids:
        return DAGValidationResult.success(
            topological_order=[],
            roots=set(),
            isolated_nodes=set(),
            warnings=[],
        )

    errors: List[str] = []
    warnings: List[str] = []

    indegree: Dict[str, int] = {nid: 0 for nid in node_ids}
    adjacency: Dict[str, List[str]] = {nid: [] for nid in node_ids}

    for nid in node_ids:
        deps = dependencies.get(nid, [])
        for dep in deps:
            if dep in node_ids:
                adjacency[dep].append(nid)
                indegree[nid] += 1

    roots = {nid for nid, deg in indegree.items() if deg == 0}

    queue: deque[str] = deque(roots)
    visited: List[str] = []

    while queue:
        current = queue.popleft()
        visited.append(current)
        for successor in adjacency[current]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)

    cyclic_nodes: Set[str] = set()
    if len(visited) != len(node_ids):
        cyclic_nodes = node_ids - set(visited)
        errors.append(
            f"Circular dependencies detected among {node_type_name}s: {sorted(cyclic_nodes)}"
        )

    reachable: Set[str] = set()
    reach_queue: deque[str] = deque(roots)
    while reach_queue:
        current = reach_queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        for successor in adjacency[current]:
            reach_queue.append(successor)

    unreachable_nodes = node_ids - reachable - cyclic_nodes
    if roots and unreachable_nodes:
        errors.append(
            f"Unreachable {node_type_name}s detected (no path from any root): {sorted(unreachable_nodes)}"
        )

    isolated_nodes = {
        nid for nid in node_ids if not dependencies.get(nid) and not adjacency[nid]
    }

    if len(node_ids) > 1 and isolated_nodes:
        msg = f"{node_type_name.capitalize()}s with no dependencies or dependents: {sorted(isolated_nodes)}"
        if allow_isolated:
            warnings.append(f"{msg} (verify intent)")
        else:
            warnings.append(f"{msg} (verify intent)")

    if errors:
        return DAGValidationResult.failure(
            errors=errors,
            warnings=warnings,
            cyclic_nodes=cyclic_nodes,
            unreachable_nodes=unreachable_nodes,
            isolated_nodes=isolated_nodes,
            partial_order=visited,
            roots=roots,
        )

    return DAGValidationResult.success(
        topological_order=visited,
        roots=roots,
        isolated_nodes=isolated_nodes,
        warnings=warnings,
    )


def validate_node_structure(
    node_ids: List[str],
    dependencies: Mapping[str, List[str]],
    *,
    node_type_name: str = "node",
    max_nodes: int | None = None,
) -> List[str]:
    errors: List[str] = []

    if not node_ids:
        errors.append(f"Must have at least one {node_type_name}")
        return errors

    if max_nodes is not None and len(node_ids) > max_nodes:
        errors.append(
            f"Exceeds maximum {node_type_name} limit: {len(node_ids)} > {max_nodes}"
        )

    counts = Counter(node_ids)
    duplicates = [nid for nid, count in counts.items() if count > 1]
    if duplicates:
        errors.append(f"Duplicate {node_type_name} IDs found: {sorted(duplicates)}")

    id_set = set(node_ids)
    checked_ids: Set[str] = set()

    for nid in node_ids:
        if nid in checked_ids:
            continue
        checked_ids.add(nid)

        deps = dependencies.get(nid, [])

        if nid in deps:
            errors.append(
                f"{node_type_name.capitalize()} '{nid}' has a self-dependency"
            )

        missing = [d for d in deps if d not in id_set]
        if missing:
            errors.append(
                f"{node_type_name.capitalize()} '{nid}' depends on non-existent {node_type_name}s: {sorted(missing)}"
            )

        dep_counts = Counter(deps)
        dup_deps = [d for d, c in dep_counts.items() if c > 1]
        if dup_deps:
            errors.append(
                f"{node_type_name.capitalize()} '{nid}' lists duplicate dependencies: {sorted(dup_deps)}"
            )

    return errors
