import pytest
from app.services.dag_plan import plan_workflow, _extract_shape_from_schema
from app.models.workflows import Node, NodeNode
from app.models.common import NodeType


class TestPlanWorkflow:
    def test_empty_workflow(self):
        """Test planning empty workflow."""
        result = plan_workflow([], [], starting_inputs={})
        assert result == []

    def test_single_node(self):
        """Test planning single node workflow."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            )
        ]
        starting_inputs = {"user_input": {"type": "string"}}

        result = plan_workflow(nodes, [], starting_inputs=starting_inputs)

        assert len(result) == 1
        assert result[0].node_id == 1
        assert result[0].node_type == NodeType.job
        assert result[0].input_shape == starting_inputs
        assert "result" in result[0].output_shape
        assert "user_input" in result[0].output_shape  # Input passed through

    def test_linear_workflow(self):
        """Test planning linear workflow with shape propagation."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=2,
                workflow_id=1,
                node_type=NodeType.guru,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=3,
                workflow_id=1,
                node_type=NodeType.return_,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label=None),
            NodeNode(id=2, parent_id=2, child_id=3, branch_label=None),
        ]
        starting_inputs = {"query": {"type": "string"}}

        result = plan_workflow(nodes, edges, starting_inputs=starting_inputs)

        assert len(result) == 3

        # Check topological order
        assert [step.node_id for step in result] == [1, 2, 3]

        # Check shape propagation
        assert result[0].input_shape == starting_inputs
        assert "query" in result[1].input_shape  # From node 1 output
        assert "result" in result[1].input_shape  # From node 1 output
        assert "response" in result[2].input_shape  # From node 2 output

    def test_merge_node_workflow(self):
        """Test workflow with merge node."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=2,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=3,
                workflow_id=1,
                node_type=NodeType.merge,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=4,
                workflow_id=1,
                node_type=NodeType.return_,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=3, branch_label=None),
            NodeNode(id=2, parent_id=2, child_id=3, branch_label=None),
            NodeNode(id=3, parent_id=3, child_id=4, branch_label=None),
        ]
        starting_inputs = {"input": {"type": "string"}}

        result = plan_workflow(nodes, edges, starting_inputs=starting_inputs)

        assert len(result) == 4

        # Check that merge node gets inputs from both parents
        merge_step = next(step for step in result if step.node_id == 3)
        assert "input" in merge_step.input_shape  # From starting inputs
        assert "result" in merge_step.input_shape  # From both job nodes

    def test_structured_output_schema(self):
        """Test node with structured output schema."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={
                    "type": "object",
                    "properties": {
                        "custom_field": {"type": "string"},
                        "count": {"type": "integer"},
                    },
                },
            )
        ]
        starting_inputs = {"input": {"type": "string"}}

        result = plan_workflow(nodes, [], starting_inputs=starting_inputs)

        assert len(result) == 1
        assert "custom_field" in result[0].output_shape
        assert "count" in result[0].output_shape
        assert result[0].output_shape["custom_field"]["type"] == "string"
        assert result[0].output_shape["count"]["type"] == "integer"

    def test_cycle_returns_empty(self):
        """Test that workflow with cycle returns empty plan."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=2,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label=None),
            NodeNode(id=2, parent_id=2, child_id=1, branch_label=None),  # Creates cycle
        ]
        starting_inputs = {"input": {"type": "string"}}

        result = plan_workflow(nodes, edges, starting_inputs=starting_inputs)

        assert result == []

    def test_isolated_nodes(self):
        """Test workflow with isolated nodes (multiple entry points)."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=2,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=3,
                workflow_id=1,
                node_type=NodeType.merge,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=3, branch_label=None),
            NodeNode(id=2, parent_id=2, child_id=3, branch_label=None),
        ]
        starting_inputs = {"shared_input": {"type": "string"}}

        result = plan_workflow(nodes, edges, starting_inputs=starting_inputs)

        assert len(result) == 3

        # Both isolated nodes should get starting inputs
        node1_step = next(step for step in result if step.node_id == 1)
        node2_step = next(step for step in result if step.node_id == 2)

        assert node1_step.input_shape == starting_inputs
        assert node2_step.input_shape == starting_inputs


class TestExtractShapeFromSchema:
    def test_object_schema(self):
        """Test extracting shape from object schema."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "active": {"type": "boolean"},
            },
        }

        result = _extract_shape_from_schema(schema)

        assert result == {
            "name": {"type": "string"},
            "age": {"type": "integer"},
            "active": {"type": "boolean"},
        }

    def test_simple_type_schema(self):
        """Test extracting shape from simple type schema."""
        schema = {"type": "string"}

        result = _extract_shape_from_schema(schema)

        assert result == {"value": {"type": "string"}}

    def test_unknown_schema(self):
        """Test extracting shape from unknown schema format."""
        schema = {"some": "unknown", "format": True}

        result = _extract_shape_from_schema(schema)

        assert result == {"value": {"type": "unknown"}}

    def test_non_dict_schema(self):
        """Test extracting shape from non-dictionary schema."""
        schema = "not a dict"

        result = _extract_shape_from_schema(schema)

        assert result == {"value": {"type": "unknown"}}

    def test_object_with_unknown_properties(self):
        """Test object schema with unknown property formats."""
        schema = {
            "type": "object",
            "properties": {
                "known": {"type": "string"},
                "unknown": {"some": "weird", "format": True},
            },
        }

        result = _extract_shape_from_schema(schema)

        assert result == {"known": {"type": "string"}, "unknown": {"type": "unknown"}}
