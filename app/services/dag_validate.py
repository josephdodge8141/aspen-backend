from typing import List, Set, Dict, Optional
from collections import defaultdict, deque
from pydantic import BaseModel

from app.models.workflows import Node, NodeNode, Workflow
from app.models.common import NodeType
from app.lib.cron import is_valid_cron


class DagValidationResult(BaseModel):
    errors: List[str]
    warnings: List[str]
    topo_order: List[int]  # node ids if valid


def validate_dag(nodes: List[Node], edges: List[NodeNode]) -> DagValidationResult:
    """
    Validate a DAG according to workflow rules.

    Rules:
    - Acyclic (no cycles)
    - Multi-parent rule: Only nodes of type merge may have indegree > 1
    - Return rule: return nodes must have indegree ≥ 1 and outdegree == 0
    - Return nodes cannot be nested under for_each (any ancestor is for_each)
    - Branch labels: if parent is if_else, outgoing edges must have branch_label in {"true","false"}
    - Other parents must have branch_label is None
    """
    errors = []
    warnings = []
    topo_order = []

    if not nodes:
        return DagValidationResult(errors=[], warnings=[], topo_order=[])

    # Build adjacency lists and node maps
    node_map = {node.id: node for node in nodes}
    outgoing = defaultdict(list)  # parent_id -> [(child_id, branch_label), ...]
    incoming = defaultdict(list)  # child_id -> [parent_id, ...]

    for edge in edges:
        outgoing[edge.parent_id].append((edge.child_id, edge.branch_label))
        incoming[edge.child_id].append(edge.parent_id)

    # 1. Check for cycles using Kahn's algorithm
    indegree = {node.id: len(incoming[node.id]) for node in nodes}
    queue = deque([node_id for node_id, degree in indegree.items() if degree == 0])
    processed = []

    while queue:
        current = queue.popleft()
        processed.append(current)

        for child_id, _ in outgoing[current]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                queue.append(child_id)

    if len(processed) != len(nodes):
        # Find a cycle path
        unprocessed = [node.id for node in nodes if node.id not in processed]
        cycle_path = _find_cycle_path(unprocessed, outgoing)
        errors.append(f"Cycle detected in graph: {' -> '.join(map(str, cycle_path))}")
    else:
        topo_order = processed

    # 2. Multi-parent rule: Only merge nodes can have indegree > 1
    for node in nodes:
        indegree_count = len(incoming[node.id])
        if indegree_count > 1 and node.node_type != NodeType.merge:
            errors.append(
                f"Node {node.id} (type: {node.node_type.value}) has multiple parents but is not a merge node"
            )

    # 3. Return rule: return nodes must have indegree ≥ 1 and outdegree == 0
    # Also check for for_each ancestors
    for node in nodes:
        if node.node_type == NodeType.return_:
            indegree_count = len(incoming[node.id])
            outdegree_count = len(outgoing[node.id])

            if indegree_count == 0:
                errors.append(f"Return node {node.id} has no incoming edges")

            if outdegree_count > 0:
                errors.append(f"Return node {node.id} has outgoing edges")

            # Check for for_each ancestors
            ancestors = _get_ancestors(node.id, incoming, node_map)
            for ancestor_id in ancestors:
                ancestor_node = node_map[ancestor_id]
                if ancestor_node.node_type == NodeType.for_each:
                    errors.append(
                        f"Return node {node.id} is nested under for_each node {ancestor_id}"
                    )
                    break

    # 4. Branch labels validation
    for node in nodes:
        children = outgoing[node.id]

        if node.node_type == NodeType.if_else:
            # Must have branch labels "true" and "false"
            branch_labels = {label for _, label in children}

            if len(children) == 0:
                warnings.append(f"If-else node {node.id} has no outgoing edges")
            elif branch_labels != {"true", "false"}:
                errors.append(
                    f"If-else node {node.id} must have exactly two outgoing edges with branch_label 'true' and 'false', "
                    f"got: {sorted(branch_labels)}"
                )
        else:
            # Non-if_else nodes must have branch_label None
            for child_id, branch_label in children:
                if branch_label is not None:
                    errors.append(
                        f"Node {node.id} (type: {node.node_type.value}) has edge to {child_id} with branch_label '{branch_label}', "
                        f"but only if_else nodes can have branch labels"
                    )

    return DagValidationResult(errors=errors, warnings=warnings, topo_order=topo_order)


def validate_workflow_triggers(workflow: Workflow) -> List[str]:
    """
    Validate workflow triggers (cron_schedule and is_api).

    Returns list of warnings.
    """
    warnings = []

    if workflow.cron_schedule:
        if not is_valid_cron(workflow.cron_schedule):
            # This should be caught at API level, but double-check
            warnings.append(f"Invalid cron schedule: {workflow.cron_schedule}")

    if not workflow.cron_schedule and not workflow.is_api:
        warnings.append(
            "No trigger configured (neither cron_schedule nor is_api is set)"
        )

    return warnings


def _find_cycle_path(
    unprocessed_nodes: List[int], outgoing: Dict[int, List[tuple]]
) -> List[int]:
    """Find a cycle path in the graph for error reporting."""
    if not unprocessed_nodes:
        return []

    # Simple DFS to find a cycle
    visited = set()
    rec_stack = set()
    path = []

    def dfs(node_id: int) -> bool:
        if node_id in rec_stack:
            # Found cycle, return the path from this node
            cycle_start = path.index(node_id)
            return path[cycle_start:] + [node_id]

        if node_id in visited:
            return False

        visited.add(node_id)
        rec_stack.add(node_id)
        path.append(node_id)

        for child_id, _ in outgoing.get(node_id, []):
            result = dfs(child_id)
            if result:
                return result

        rec_stack.remove(node_id)
        path.pop()
        return False

    for node_id in unprocessed_nodes:
        if node_id not in visited:
            cycle = dfs(node_id)
            if cycle:
                return cycle

    # Fallback: just return first few unprocessed nodes
    return unprocessed_nodes[:3]


def _get_ancestors(
    node_id: int, incoming: Dict[int, List[int]], node_map: Dict[int, Node]
) -> Set[int]:
    """Get all ancestors of a node using BFS."""
    ancestors = set()
    queue = deque([node_id])
    visited = {node_id}

    while queue:
        current = queue.popleft()

        for parent_id in incoming.get(current, []):
            if parent_id not in visited:
                ancestors.add(parent_id)
                visited.add(parent_id)
                queue.append(parent_id)

    return ancestors
