import pytest
import uuid
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from app.database import engine
from app.models.workflows import Workflow, Node, NodeNode
from app.models.team import Team
from app.models.common import NodeType


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


def test_create_workflow(db_session):
    # Create a team first
    team = Team(name=f"Workflow Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create workflow
    workflow = Workflow(
        name="Test Workflow",
        description="A test workflow for validation",
        input_params={"param1": "value1", "param2": 123},
        is_api=True,
        cron_schedule="0 */6 * * *",
        team_id=team.id,
    )
    db_session.add(workflow)
    db_session.commit()

    assert workflow.id is not None
    assert workflow.uuid is not None
    assert len(workflow.uuid) == 36  # UUID4 format
    assert workflow.name == "Test Workflow"
    assert workflow.description == "A test workflow for validation"
    assert workflow.input_params == {"param1": "value1", "param2": 123}
    assert workflow.is_api is True
    assert workflow.cron_schedule == "0 */6 * * *"
    assert workflow.team_id == team.id


def test_workflow_uuid_uniqueness(db_session):
    # Create a team first
    team = Team(name=f"UUID Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create first workflow
    workflow1 = Workflow(name="Workflow 1", team_id=team.id)
    db_session.add(workflow1)
    db_session.commit()

    # Try to create another workflow with the same UUID
    workflow2 = Workflow(
        name="Workflow 2", team_id=team.id, uuid=workflow1.uuid  # Same UUID
    )
    db_session.add(workflow2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_create_node(db_session):
    # Create a team and workflow first
    team = Team(name=f"Node Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    workflow = Workflow(name="Node Test Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create node with all node types
    for node_type in NodeType:
        node = Node(
            workflow_id=workflow.id,
            node_type=node_type,
            node_metadata={"config": f"test_{node_type.value}"},
            structured_output={"output_schema": {"type": "object"}},
        )
        db_session.add(node)

    db_session.commit()

    # Verify all nodes were created
    nodes = db_session.exec(select(Node).where(Node.workflow_id == workflow.id)).all()
    assert len(nodes) == len(NodeType)

    # Check a specific node
    job_node = db_session.exec(
        select(Node).where(
            Node.workflow_id == workflow.id, Node.node_type == NodeType.job
        )
    ).first()
    assert job_node is not None
    assert job_node.node_type == NodeType.job
    assert job_node.node_metadata == {"config": "test_job"}
    assert job_node.structured_output == {"output_schema": {"type": "object"}}


def test_create_node_edges(db_session):
    # Create a team and workflow first
    team = Team(name=f"Edge Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    workflow = Workflow(name="Edge Test Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create nodes
    start_node = Node(
        workflow_id=workflow.id, node_type=NodeType.job, node_metadata={"type": "start"}
    )
    middle_node = Node(
        workflow_id=workflow.id,
        node_type=NodeType.filter,
        node_metadata={"type": "middle"},
    )
    end_node = Node(
        workflow_id=workflow.id,
        node_type=NodeType.return_,
        node_metadata={"type": "end"},
    )
    db_session.add(start_node)
    db_session.add(middle_node)
    db_session.add(end_node)
    db_session.commit()

    # Create edges: start -> middle -> end
    edge1 = NodeNode(parent_id=start_node.id, child_id=middle_node.id)
    edge2 = NodeNode(parent_id=middle_node.id, child_id=end_node.id)
    db_session.add(edge1)
    db_session.add(edge2)
    db_session.commit()

    assert edge1.id is not None
    assert edge2.id is not None
    assert edge1.parent_id == start_node.id
    assert edge1.child_id == middle_node.id
    assert edge2.parent_id == middle_node.id
    assert edge2.child_id == end_node.id


def test_duplicate_edge_constraint(db_session):
    # Create a team and workflow first
    team = Team(name=f"Duplicate Edge Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    workflow = Workflow(name="Duplicate Edge Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create nodes
    node1 = Node(workflow_id=workflow.id, node_type=NodeType.job)
    node2 = Node(workflow_id=workflow.id, node_type=NodeType.filter)
    db_session.add(node1)
    db_session.add(node2)
    db_session.commit()

    # Create first edge
    edge1 = NodeNode(parent_id=node1.id, child_id=node2.id)
    db_session.add(edge1)
    db_session.commit()

    # Try to create duplicate edge
    edge2 = NodeNode(parent_id=node1.id, child_id=node2.id)
    db_session.add(edge2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_self_edge_constraint(db_session):
    # Create a team and workflow first
    team = Team(name=f"Self Edge Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    workflow = Workflow(name="Self Edge Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create node
    node = Node(workflow_id=workflow.id, node_type=NodeType.job)
    db_session.add(node)
    db_session.commit()

    # Try to create self-edge (node pointing to itself)
    self_edge = NodeNode(parent_id=node.id, child_id=node.id)
    db_session.add(self_edge)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_workflow_input_params_json(db_session):
    # Create a team first
    team = Team(name=f"JSON Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create workflow with complex input params
    complex_params = {
        "version": 1,
        "inputs": [
            {
                "name": "text_input",
                "type": "string",
                "required": True,
                "description": "Input text to process",
            },
            {
                "name": "options",
                "type": "object",
                "properties": {
                    "model": {"type": "string", "default": "gpt-4"},
                    "temperature": {"type": "number", "default": 0.7},
                },
            },
        ],
    }

    workflow = Workflow(
        name="Complex JSON Workflow", input_params=complex_params, team_id=team.id
    )
    db_session.add(workflow)
    db_session.commit()

    # Verify JSON was stored correctly
    retrieved_workflow = db_session.get(Workflow, workflow.id)
    assert retrieved_workflow.input_params == complex_params
    assert retrieved_workflow.input_params["inputs"][0]["name"] == "text_input"
    assert (
        retrieved_workflow.input_params["inputs"][1]["properties"]["model"]["default"]
        == "gpt-4"
    )


def test_foreign_key_integrity(db_session):
    # Create a team first
    team = Team(name=f"FK Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create workflow
    workflow = Workflow(name="FK Test Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()

    # Create nodes
    node1 = Node(workflow_id=workflow.id, node_type=NodeType.job)
    node2 = Node(workflow_id=workflow.id, node_type=NodeType.filter)
    db_session.add(node1)
    db_session.add(node2)
    db_session.commit()

    # Create edge
    edge = NodeNode(parent_id=node1.id, child_id=node2.id)
    db_session.add(edge)
    db_session.commit()

    # Verify all relationships
    assert workflow.team_id == team.id
    assert node1.workflow_id == workflow.id
    assert node2.workflow_id == workflow.id
    assert edge.parent_id == node1.id
    assert edge.child_id == node2.id


def test_workflow_api_and_cron_flags(db_session):
    # Create a team first
    team = Team(name=f"API Cron Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()

    # Create API workflow
    api_workflow = Workflow(
        name="API Workflow", is_api=True, cron_schedule=None, team_id=team.id
    )
    db_session.add(api_workflow)

    # Create CRON workflow
    cron_workflow = Workflow(
        name="CRON Workflow",
        is_api=False,
        cron_schedule="0 9 * * 1-5",  # 9 AM weekdays
        team_id=team.id,
    )
    db_session.add(cron_workflow)

    # Create both API and CRON workflow
    hybrid_workflow = Workflow(
        name="Hybrid Workflow",
        is_api=True,
        cron_schedule="0 0 * * 0",  # Midnight on Sundays
        team_id=team.id,
    )
    db_session.add(hybrid_workflow)

    db_session.commit()

    assert api_workflow.is_api is True
    assert api_workflow.cron_schedule is None

    assert cron_workflow.is_api is False
    assert cron_workflow.cron_schedule == "0 9 * * 1-5"

    assert hybrid_workflow.is_api is True
    assert hybrid_workflow.cron_schedule == "0 0 * * 0"
