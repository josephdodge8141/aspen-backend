from typing import Dict, Any, Set, List
from collections import defaultdict, deque

from app.models.workflows import Node, NodeNode
from app.services.dag_plan import _compute_node_output_shape


def available_data_map(
    nodes: List[Node], edges: List[NodeNode]
) -> Dict[int, Dict[str, Any]]:
    """
    Compute available data for each node based on all predecessor outputs.

    For each node, this returns the merged outputs of all predecessors transitively.
    This is useful for node configuration UI to show what data is available.

    Args:
        nodes: List of workflow nodes
        edges: List of workflow edges

    Returns:
        Dictionary mapping node_id to available data shape
    """
    if not nodes:
        return {}

    # Build adjacency lists and node maps
    node_map = {node.id: node for node in nodes}
    outgoing = defaultdict(list)  # parent_id -> [child_id, ...]
    incoming = defaultdict(list)  # child_id -> [parent_id, ...]

    for edge in edges:
        outgoing[edge.parent_id].append(edge.child_id)
        incoming[edge.child_id].append(edge.parent_id)

    # Compute topological order
    indegree = {node.id: len(incoming[node.id]) for node in nodes}
    queue = deque([node_id for node_id, degree in indegree.items() if degree == 0])
    topo_order = []

    while queue:
        current = queue.popleft()
        topo_order.append(current)

        for child_id in outgoing[current]:
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                queue.append(child_id)

    # If there's a cycle, return empty map
    if len(topo_order) != len(nodes):
        return {}

    # Compute available data for each node
    node_outputs = {}  # node_id -> output_shape
    available_data = {}  # node_id -> available_data_shape

    for node_id in topo_order:
        node = node_map[node_id]

        # Get all predecessors transitively
        predecessors = _get_all_predecessors(node_id, incoming)

        # Merge outputs from all predecessors
        merged_data = {}

        for pred_id in predecessors:
            if pred_id in node_outputs:
                pred_output = node_outputs[pred_id]
                for key, value in pred_output.items():
                    # Simple merge - later values overwrite earlier ones
                    # In a real system, you might want more sophisticated conflict resolution
                    merged_data[key] = value

        # Store available data for this node
        available_data[node_id] = merged_data

        # Compute this node's output for next iteration
        # Use empty input shape since we're just computing outputs
        node_output = _compute_node_output_shape(node, {}, [])
        node_outputs[node_id] = node_output

    return available_data


def _get_all_predecessors(node_id: int, incoming: Dict[int, List[int]]) -> Set[int]:
    """
    Get all predecessors of a node transitively using BFS.

    Args:
        node_id: The target node ID
        incoming: Dictionary mapping node_id to list of parent node IDs

    Returns:
        Set of all predecessor node IDs
    """
    predecessors = set()
    queue = deque([node_id])
    visited = {node_id}

    while queue:
        current = queue.popleft()

        for parent_id in incoming.get(current, []):
            if parent_id not in visited:
                predecessors.add(parent_id)
                visited.add(parent_id)
                queue.append(parent_id)

    return predecessors


def resolve_inputs_for_node(node_id: int, outputs_by_node: Dict[int, Dict]) -> Dict:
    """
    Resolve the inputs for a node by merging all predecessor outputs.

    Args:
        node_id: The node to resolve inputs for
        outputs_by_node: Dictionary mapping node_id to their output data

    Returns:
        Dictionary containing merged inputs from all predecessors
    """
    # For now, we'll do a simple merge of all available outputs
    # In a real implementation, you might want to be more sophisticated
    # about handling conflicts or namespacing

    merged_inputs = {}

    for predecessor_id, output_data in outputs_by_node.items():
        if predecessor_id != node_id and output_data:
            # Merge the output data, with later nodes potentially overriding earlier ones
            merged_inputs.update(output_data)

    return merged_inputs
