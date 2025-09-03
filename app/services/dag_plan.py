from typing import List, Dict, Any, Set
from collections import defaultdict, deque
from pydantic import BaseModel

from app.models.workflows import Node, NodeNode
from app.models.common import NodeType


class PlannedNode(BaseModel):
    node_id: int
    node_type: NodeType
    input_shape: Dict[str, Any]
    output_shape: Dict[str, Any]
    notes: List[str] = []


def plan_workflow(
    nodes: List[Node], edges: List[NodeNode], *, starting_inputs: Dict[str, Any]
) -> List[PlannedNode]:
    """
    Plan workflow execution by computing topological order and propagating data shapes.

    Args:
        nodes: List of workflow nodes
        edges: List of workflow edges
        starting_inputs: Initial input data shape for the workflow

    Returns:
        List of PlannedNode objects in topological execution order
    """
    if not nodes:
        return []

    # Build adjacency lists and node maps
    node_map = {node.id: node for node in nodes}
    outgoing = defaultdict(list)  # parent_id -> [child_id, ...]
    incoming = defaultdict(list)  # child_id -> [parent_id, ...]

    for edge in edges:
        outgoing[edge.parent_id].append(edge.child_id)
        incoming[edge.child_id].append(edge.parent_id)

    # Compute topological order using Kahn's algorithm
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

    # If we couldn't process all nodes, there's a cycle - return empty plan
    if len(topo_order) != len(nodes):
        return []

    # Propagate shapes through the DAG
    node_shapes = {}  # node_id -> output_shape
    planned_nodes = []

    for node_id in topo_order:
        node = node_map[node_id]
        notes = []

        # Compute input shape for this node
        if not incoming[node_id]:
            # Entry point - use starting inputs
            input_shape = starting_inputs.copy()
        else:
            # Merge inputs from all parents
            input_shape = {}
            parent_outputs = []

            for parent_id in incoming[node_id]:
                parent_output = node_shapes.get(parent_id, {})
                parent_outputs.append(parent_output)

            if node.node_type == NodeType.merge:
                # For merge nodes, union all parent outputs
                for parent_output in parent_outputs:
                    for key, value in parent_output.items():
                        if key in input_shape and input_shape[key] != value:
                            notes.append(
                                f"Field '{key}' has conflicting types from multiple parents"
                            )
                        input_shape[key] = value
            else:
                # For non-merge nodes, union with collision detection
                for parent_output in parent_outputs:
                    for key, value in parent_output.items():
                        if key in input_shape and input_shape[key] != value:
                            notes.append(
                                f"Field '{key}' collision from multiple parents (non-merge node)"
                            )
                        input_shape[key] = value

        # Compute output shape for this node
        output_shape = _compute_node_output_shape(node, input_shape, notes)

        # Store for next iteration
        node_shapes[node_id] = output_shape

        # Create planned node
        planned_node = PlannedNode(
            node_id=node_id,
            node_type=node.node_type,
            input_shape=input_shape,
            output_shape=output_shape,
            notes=notes,
        )
        planned_nodes.append(planned_node)

    return planned_nodes


def _compute_node_output_shape(
    node: Node, input_shape: Dict[str, Any], notes: List[str]
) -> Dict[str, Any]:
    """
    Compute the output shape for a node based on its type and structured_output.

    This is a mock implementation - in E5 this would call the node service's plan() method.
    """
    # If node has structured_output defined, use that
    if node.structured_output:
        return _extract_shape_from_schema(node.structured_output)

    # Otherwise, provide mock shapes based on node type
    mock_shapes = {
        NodeType.job: {
            "result": {"type": "object"},
            "status": {"type": "string"},
            "timestamp": {"type": "string"},
        },
        NodeType.guru: {
            "response": {"type": "string"},
            "confidence": {"type": "number"},
            "tokens_used": {"type": "integer"},
        },
        NodeType.if_else: {
            "condition_result": {"type": "boolean"},
            "branch_taken": {"type": "string"},
        },
        NodeType.for_each: {
            "items_processed": {"type": "integer"},
            "results": {"type": "array", "items": {"type": "object"}},
        },
        NodeType.merge: {
            "merged_data": {"type": "object"},
            "source_count": {"type": "integer"},
        },
        NodeType.return_: input_shape,  # Return nodes pass through their input
    }

    base_shape = mock_shapes.get(node.node_type, {"output": {"type": "object"}})

    # For non-return nodes, include input data as well
    if node.node_type != NodeType.return_:
        output_shape = input_shape.copy()
        output_shape.update(base_shape)
        return output_shape
    else:
        return base_shape


def _extract_shape_from_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a simplified shape from a JSON schema.

    This converts JSON schema format to a simpler shape format for planning.
    """
    if not isinstance(schema, dict):
        return {"value": {"type": "unknown"}}

    if schema.get("type") == "object" and "properties" in schema:
        # Extract properties from object schema
        shape = {}
        for prop_name, prop_schema in schema["properties"].items():
            if isinstance(prop_schema, dict) and "type" in prop_schema:
                shape[prop_name] = {"type": prop_schema["type"]}
            else:
                shape[prop_name] = {"type": "unknown"}
        return shape
    elif "type" in schema:
        # Simple type schema
        return {"value": {"type": schema["type"]}}
    else:
        # Unknown schema format
        return {"value": {"type": "unknown"}}
