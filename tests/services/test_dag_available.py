import pytest
from app.services.dag_available import (
    available_data_map,
    _get_all_predecessors,
    resolve_inputs_for_node,
)
from app.models.workflows import Node, NodeNode
from app.models.common import NodeType


class TestAvailableDataMap:
    def test_empty_workflow(self):
        """Test available data for empty workflow."""
        result = available_data_map([], [])
        assert result == {}

    def test_single_node(self):
        """Test available data for single node."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            )
        ]

        result = available_data_map(nodes, [])

        assert result == {1: {}}  # No predecessors, so no available data

    def test_linear_workflow(self):
        """Test available data for linear workflow."""
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

        result = available_data_map(nodes, edges)

        assert result[1] == {}  # No predecessors
        assert "result" in result[2]  # Has node 1's output
        assert "status" in result[2]
        assert "result" in result[3]  # Has node 1's output
        assert "response" in result[3]  # Has node 2's output

    def test_diamond_pattern(self):
        """Test available data for diamond pattern: A→B, A→C, B→D, C→D."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),  # A
            Node(
                id=2,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),  # B
            Node(
                id=3,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),  # C
            Node(
                id=4,
                workflow_id=1,
                node_type=NodeType.merge,
                node_metadata={},
                structured_output={},
            ),  # D
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label=None),  # A→B
            NodeNode(id=2, parent_id=1, child_id=3, branch_label=None),  # A→C
            NodeNode(id=3, parent_id=2, child_id=4, branch_label=None),  # B→D
            NodeNode(id=4, parent_id=3, child_id=4, branch_label=None),  # C→D
        ]

        result = available_data_map(nodes, edges)

        # Node 1 (A): No predecessors
        assert result[1] == {}

        # Node 2 (B): Has A's output
        assert "result" in result[2]
        assert "status" in result[2]

        # Node 3 (C): Has A's output
        assert "result" in result[3]
        assert "status" in result[3]

        # Node 4 (D): Has A, B, and C outputs
        assert "result" in result[4]  # From A, B, C
        assert "status" in result[4]  # From A, B, C

    def test_complex_workflow(self):
        """Test available data for complex workflow with multiple paths."""
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
                node_type=NodeType.if_else,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=3,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=4,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=5,
                workflow_id=1,
                node_type=NodeType.merge,
                node_metadata={},
                structured_output={},
            ),
            Node(
                id=6,
                workflow_id=1,
                node_type=NodeType.return_,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label=None),
            NodeNode(id=2, parent_id=2, child_id=3, branch_label="true"),
            NodeNode(id=3, parent_id=2, child_id=4, branch_label="false"),
            NodeNode(id=4, parent_id=3, child_id=5, branch_label=None),
            NodeNode(id=5, parent_id=4, child_id=5, branch_label=None),
            NodeNode(id=6, parent_id=5, child_id=6, branch_label=None),
        ]

        result = available_data_map(nodes, edges)

        # Node 6 (return) should have data from all predecessors
        assert "result" in result[6]  # From nodes 1, 3, 4
        assert "condition_result" in result[6]  # From node 2
        assert "merged_data" in result[6]  # From node 5

    def test_cycle_returns_empty(self):
        """Test that workflow with cycle returns empty map."""
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

        result = available_data_map(nodes, edges)

        assert result == {}

    def test_isolated_nodes(self):
        """Test available data for workflow with isolated nodes."""
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

        result = available_data_map(nodes, edges)

        # Isolated nodes have no available data
        assert result[1] == {}
        assert result[2] == {}

        # Merge node has data from both isolated nodes
        assert "result" in result[3]
        assert "status" in result[3]


class TestGetAllPredecessors:
    def test_no_predecessors(self):
        """Test node with no predecessors."""
        incoming = {1: [], 2: [1]}

        result = _get_all_predecessors(1, incoming)

        assert result == set()

    def test_direct_predecessors(self):
        """Test node with direct predecessors only."""
        incoming = {1: [], 2: [1], 3: [1]}

        result = _get_all_predecessors(2, incoming)

        assert result == {1}

    def test_transitive_predecessors(self):
        """Test node with transitive predecessors."""
        incoming = {1: [], 2: [1], 3: [2], 4: [3]}

        result = _get_all_predecessors(4, incoming)

        assert result == {1, 2, 3}

    def test_diamond_predecessors(self):
        """Test diamond pattern predecessors."""
        incoming = {1: [], 2: [1], 3: [1], 4: [2, 3]}

        result = _get_all_predecessors(4, incoming)

        assert result == {1, 2, 3}

    def test_complex_predecessors(self):
        """Test complex graph with multiple paths."""
        incoming = {1: [], 2: [1], 3: [1], 4: [2], 5: [3], 6: [4, 5], 7: [6]}

        result = _get_all_predecessors(7, incoming)

        assert result == {1, 2, 3, 4, 5, 6}

    def test_missing_node(self):
        """Test node not in incoming map."""
        incoming = {1: [], 2: [1]}

        result = _get_all_predecessors(99, incoming)

        assert result == set()

    def test_self_not_included(self):
        """Test that node doesn't include itself in predecessors."""
        incoming = {1: [], 2: [1], 3: [2]}

        result = _get_all_predecessors(3, incoming)

        assert 3 not in result
        assert result == {1, 2}


class TestResolveInputsForNode:
    def test_resolve_inputs_empty_outputs(self):
        outputs_by_node = {}
        result = resolve_inputs_for_node(1, outputs_by_node)
        assert result == {}

    def test_resolve_inputs_single_predecessor(self):
        outputs_by_node = {1: {"data": "value1", "count": 5}}
        result = resolve_inputs_for_node(2, outputs_by_node)
        assert result == {"data": "value1", "count": 5}

    def test_resolve_inputs_multiple_predecessors(self):
        outputs_by_node = {
            1: {"data": "from_node_1", "shared": "first"},
            2: {"result": "from_node_2", "shared": "second"},
            3: {"output": "from_node_3"},
        }
        result = resolve_inputs_for_node(4, outputs_by_node)

        # Should merge all outputs, with later nodes overriding earlier ones
        expected = {
            "data": "from_node_1",
            "result": "from_node_2",
            "output": "from_node_3",
            "shared": "second",  # Last one wins
        }
        assert result == expected

    def test_resolve_inputs_excludes_self(self):
        outputs_by_node = {
            1: {"data": "from_node_1"},
            2: {"data": "from_self"},  # This should be excluded
            3: {"result": "from_node_3"},
        }
        result = resolve_inputs_for_node(2, outputs_by_node)

        # Should not include output from node 2 itself
        expected = {"data": "from_node_1", "result": "from_node_3"}
        assert result == expected

    def test_resolve_inputs_with_empty_outputs(self):
        outputs_by_node = {
            1: {"data": "value1"},
            2: {},  # Empty output
            3: None,  # None output
            4: {"result": "value4"},
        }
        result = resolve_inputs_for_node(5, outputs_by_node)

        # Should only include non-empty outputs
        expected = {"data": "value1", "result": "value4"}
        assert result == expected

    def test_resolve_inputs_diamond_pattern(self):
        """Test diamond pattern where D receives union of A,B,C outputs."""
        outputs_by_node = {
            1: {"source": "A", "step": 1},  # Node A
            2: {"processed": "B", "step": 2},  # Node B (from A)
            3: {"filtered": "C", "step": 3},  # Node C (from A)
        }
        result = resolve_inputs_for_node(4, outputs_by_node)  # Node D

        # D should receive union of all predecessor outputs
        expected = {
            "source": "A",
            "processed": "B",
            "filtered": "C",
            "step": 3,  # Last value wins
        }
        assert result == expected
