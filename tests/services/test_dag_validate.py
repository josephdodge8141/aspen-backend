import pytest
from app.services.dag_validate import validate_dag, validate_workflow_triggers
from app.models.workflows import Node, NodeNode, Workflow
from app.models.common import NodeType


class TestValidateDag:
    def test_empty_dag(self):
        """Test validation of empty DAG."""
        result = validate_dag([], [])
        assert result.errors == []
        assert result.warnings == []
        assert result.topo_order == []

    def test_single_node(self):
        """Test validation of single node."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            )
        ]
        result = validate_dag(nodes, [])
        assert result.errors == []
        assert result.warnings == []
        assert result.topo_order == [1]

    def test_linear_dag(self):
        """Test validation of linear DAG."""
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

        result = validate_dag(nodes, edges)
        assert result.errors == []
        assert result.warnings == []
        assert result.topo_order == [1, 2, 3]

    def test_cycle_detection(self):
        """Test cycle detection."""
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
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label=None),
            NodeNode(id=2, parent_id=2, child_id=3, branch_label=None),
            NodeNode(id=3, parent_id=3, child_id=1, branch_label=None),  # Creates cycle
        ]

        result = validate_dag(nodes, edges)
        assert len(result.errors) == 1
        assert "Cycle detected" in result.errors[0]
        assert result.topo_order == []

    def test_multi_parent_merge_valid(self):
        """Test valid multi-parent merge node."""
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

        result = validate_dag(nodes, edges)
        assert result.errors == []
        assert len(result.topo_order) == 4

    def test_multi_parent_non_merge_invalid(self):
        """Test invalid multi-parent non-merge node."""
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
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),  # Not merge
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=3, branch_label=None),
            NodeNode(id=2, parent_id=2, child_id=3, branch_label=None),
        ]

        result = validate_dag(nodes, edges)
        assert len(result.errors) == 1
        assert "has multiple parents but is not a merge node" in result.errors[0]

    def test_return_node_valid(self):
        """Test valid return node (indegree ≥ 1, outdegree = 0)."""
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
                node_type=NodeType.return_,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label=None),
        ]

        result = validate_dag(nodes, edges)
        assert result.errors == []

    def test_return_node_no_incoming(self):
        """Test return node with no incoming edges."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.return_,
                node_metadata={},
                structured_output={},
            ),
        ]

        result = validate_dag(nodes, [])
        assert len(result.errors) == 1
        assert "Return node 1 has no incoming edges" in result.errors[0]

    def test_return_node_has_outgoing(self):
        """Test return node with outgoing edges."""
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
                node_type=NodeType.return_,
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
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label=None),
            NodeNode(
                id=2, parent_id=2, child_id=3, branch_label=None
            ),  # Invalid outgoing
        ]

        result = validate_dag(nodes, edges)
        assert len(result.errors) == 1
        assert "Return node 2 has outgoing edges" in result.errors[0]

    def test_return_node_under_for_each(self):
        """Test return node nested under for_each."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.for_each,
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
                node_type=NodeType.return_,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label=None),
            NodeNode(id=2, parent_id=2, child_id=3, branch_label=None),
        ]

        result = validate_dag(nodes, edges)
        assert len(result.errors) == 1
        assert "Return node 3 is nested under for_each node 1" in result.errors[0]

    def test_if_else_branch_labels_valid(self):
        """Test valid if_else node with true/false branch labels."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.if_else,
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
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label="true"),
            NodeNode(id=2, parent_id=1, child_id=3, branch_label="false"),
        ]

        result = validate_dag(nodes, edges)
        assert result.errors == []

    def test_if_else_branch_labels_invalid(self):
        """Test invalid if_else node with wrong branch labels."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.if_else,
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
                node_type=NodeType.job,
                node_metadata={},
                structured_output={},
            ),
        ]
        edges = [
            NodeNode(id=1, parent_id=1, child_id=2, branch_label="yes"),
            NodeNode(id=2, parent_id=1, child_id=3, branch_label="no"),
        ]

        result = validate_dag(nodes, edges)
        assert len(result.errors) == 1
        assert (
            "must have exactly two outgoing edges with branch_label 'true' and 'false'"
            in result.errors[0]
        )

    def test_if_else_no_outgoing_warning(self):
        """Test if_else node with no outgoing edges generates warning."""
        nodes = [
            Node(
                id=1,
                workflow_id=1,
                node_type=NodeType.if_else,
                node_metadata={},
                structured_output={},
            ),
        ]

        result = validate_dag(nodes, [])
        assert len(result.warnings) == 1
        assert "If-else node 1 has no outgoing edges" in result.warnings[0]

    def test_non_if_else_with_branch_label(self):
        """Test non-if_else node with branch label."""
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
            NodeNode(id=1, parent_id=1, child_id=2, branch_label="invalid"),
        ]

        result = validate_dag(nodes, edges)
        assert len(result.errors) == 1
        assert "but only if_else nodes can have branch labels" in result.errors[0]

    def test_complex_valid_dag(self):
        """Test complex but valid DAG."""
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

        result = validate_dag(nodes, edges)
        assert result.errors == []
        assert len(result.topo_order) == 6


class TestValidateWorkflowTriggers:
    def test_valid_cron_trigger(self):
        """Test workflow with valid cron trigger."""
        workflow = Workflow(
            id=1, name="Test", team_id=1, cron_schedule="0 0 * * *", is_api=False
        )

        warnings = validate_workflow_triggers(workflow)
        assert warnings == []

    def test_valid_api_trigger(self):
        """Test workflow with API trigger."""
        workflow = Workflow(
            id=1, name="Test", team_id=1, cron_schedule=None, is_api=True
        )

        warnings = validate_workflow_triggers(workflow)
        assert warnings == []

    def test_both_triggers(self):
        """Test workflow with both triggers."""
        workflow = Workflow(
            id=1, name="Test", team_id=1, cron_schedule="0 0 * * *", is_api=True
        )

        warnings = validate_workflow_triggers(workflow)
        assert warnings == []

    def test_invalid_cron_trigger(self):
        """Test workflow with invalid cron trigger."""
        workflow = Workflow(
            id=1, name="Test", team_id=1, cron_schedule="invalid cron", is_api=False
        )

        warnings = validate_workflow_triggers(workflow)
        assert len(warnings) == 1
        assert "Invalid cron schedule" in warnings[0]

    def test_no_triggers(self):
        """Test workflow with no triggers."""
        workflow = Workflow(
            id=1, name="Test", team_id=1, cron_schedule=None, is_api=False
        )

        warnings = validate_workflow_triggers(workflow)
        assert len(warnings) == 1
        assert "No trigger configured" in warnings[0]
