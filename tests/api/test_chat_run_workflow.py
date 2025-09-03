import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch

from app.main import app
from app.models.workflows import Workflow, Node, NodeNode
from app.models.team import Team, Member, TeamMember, TeamRole
from app.models.users import User
from app.models.services import Service
from app.models.workflow_services import WorkflowService
from app.models.common import Environment
from app.models.common import NodeType
from app.security.jwt import create_access_token
from app.api.deps import get_db_session


@pytest.fixture
def client(db_session: Session):
    def get_test_db():
        return db_session

    app.dependency_overrides[get_db_session] = get_test_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_data(db_session: Session):
    # Create team
    team = Team(name="Test Team")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Create member
    import uuid
    unique_email = f"test-{uuid.uuid4()}@example.com"
    member = Member(
        first_name="Test",
        last_name="User",
        email=unique_email
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    # Create user
    user = User(
        email=unique_email, username=f"testuser-{uuid.uuid4()}", hashed_password="hashed_password"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create team membership
    membership = TeamMember(team_id=team.id, member_id=member.id, role=TeamRole.member)
    db_session.add(membership)
    db_session.commit()

    # Create workflow
    workflow = Workflow(
        name="Test Workflow",
        description="Test workflow for chat execution",
        team_id=team.id,
    )
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    # Create nodes (simple linear workflow: job -> filter)
    node1 = Node(
        workflow_id=workflow.id,
        node_type=NodeType.job,
        node_metadata={"prompt": "Test prompt", "model_name": "gpt-4"},
        structured_output={},
    )
    db_session.add(node1)
    db_session.commit()
    db_session.refresh(node1)

    node2 = Node(
        workflow_id=workflow.id,
        node_type=NodeType.filter,
        node_metadata={"condition": "true"},
        structured_output={},
    )
    db_session.add(node2)
    db_session.commit()
    db_session.refresh(node2)

    # Create edge
    edge = NodeNode(
        workflow_id=workflow.id, parent_node_id=node1.id, child_node_id=node2.id
    )
    db_session.add(edge)
    db_session.commit()

    # Create service
    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash="test_hash",
        api_key_last4="hash"
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)

    # Create workflow-service link
    workflow_service = WorkflowService(workflow_id=workflow.id, service_id=service.id)
    db_session.add(workflow_service)
    db_session.commit()

    return {
        "team": team,
        "user": user,
        "workflow": workflow,
        "nodes": [node1, node2],
        "service": service,
    }


@pytest.fixture
def auth_headers(test_data):
    token = create_access_token(test_data["user"].id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def service_headers():
    return {"X-API-Key": "test_key"}


class TestRunWorkflow:
    def test_run_workflow_success_with_user(self, client, test_data, auth_headers):
        """Test successful workflow run with user authentication."""
        request_data = {
            "workflow_id": test_data["workflow"].id,
            "starting_inputs": {"input": "test data"},
        }

        response = client.post(
            "/api/v1/chat/workflows:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "run_id" in data
        assert "steps" in data
        assert len(data["steps"]) == 2  # Two nodes executed

        # Check first step (job node)
        step1 = data["steps"][0]
        assert step1["node_type"] == "job"
        assert "output" in step1

        # Check second step (filter node)
        step2 = data["steps"][1]
        assert step2["node_type"] == "filter"
        assert "output" in step2

    @patch("app.security.apikeys.hash_api_key")
    def test_run_workflow_success_with_service(
        self, mock_hash, client, test_data, service_headers
    ):
        """Test successful workflow run with service authentication."""
        mock_hash.return_value = "test_hash"

        request_data = {
            "workflow_id": test_data["workflow"].id,
            "starting_inputs": {"data": "service input"},
        }

        response = client.post(
            "/api/v1/chat/workflows:run", json=request_data, headers=service_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "run_id" in data
        assert "steps" in data
        assert len(data["steps"]) == 2

    def test_run_workflow_not_found(self, client, auth_headers):
        """Test workflow not found error."""
        request_data = {"workflow_id": 99999, "starting_inputs": {"input": "test"}}

        response = client.post(
            "/api/v1/chat/workflows:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 404
        assert "Workflow not found" in response.text

    def test_run_workflow_no_auth(self, client, test_data):
        """Test authentication required error."""
        request_data = {
            "workflow_id": test_data["workflow"].id,
            "starting_inputs": {"input": "test"},
        }

        response = client.post("/api/v1/chat/workflows:run", json=request_data)

        assert response.status_code == 401

    @patch("app.security.apikeys.hash_api_key")
    def test_run_workflow_service_not_linked(
        self, mock_hash, client, test_data, db_session
    ):
        """Test service not authorized for workflow."""
        mock_hash.return_value = "different_hash"

        # Create another service not linked to the workflow
        other_service = Service(
            name="Other Service",
            api_key_hash="different_hash",
            team_id=test_data["team"].id,
        )
        db_session.add(other_service)
        db_session.commit()

        request_data = {
            "workflow_id": test_data["workflow"].id,
            "starting_inputs": {"input": "test"},
        }

        response = client.post(
            "/api/v1/chat/workflows:run",
            json=request_data,
            headers={"X-API-Key": "other_key"},
        )

        assert response.status_code == 403
        assert "not authorized to use this workflow" in response.text

    def test_run_workflow_user_not_team_member(self, client, test_data, db_session):
        """Test user not team member error."""
        # Create another user not in the team
        other_user = User(
            email="other@example.com",
            username="otheruser",
            hashed_password="hashed_password",
        )
        db_session.add(other_user)
        db_session.commit()
        db_session.refresh(other_user)

        token = create_access_token(other_user.id)
        headers = {"Authorization": f"Bearer {token}"}

        request_data = {
            "workflow_id": test_data["workflow"].id,
            "starting_inputs": {"input": "test"},
        }

        response = client.post(
            "/api/v1/chat/workflows:run", json=request_data, headers=headers
        )

        assert response.status_code == 403

    def test_run_workflow_minimal_request(self, client, test_data, auth_headers):
        """Test workflow run with minimal request data."""
        request_data = {"workflow_id": test_data["workflow"].id}

        response = client.post(
            "/api/v1/chat/workflows:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "steps" in data

    def test_run_workflow_invalid_dag(
        self, client, test_data, auth_headers, db_session
    ):
        """Test workflow with invalid DAG (cycle)."""
        # Create a cycle by adding edge from node2 back to node1
        cycle_edge = NodeNode(
            workflow_id=test_data["workflow"].id,
            parent_node_id=test_data["nodes"][1].id,  # node2
            child_node_id=test_data["nodes"][0].id,  # node1
        )
        db_session.add(cycle_edge)
        db_session.commit()

        request_data = {
            "workflow_id": test_data["workflow"].id,
            "starting_inputs": {"input": "test"},
        }

        response = client.post(
            "/api/v1/chat/workflows:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 400
        assert "Invalid workflow DAG" in response.text

    def test_run_workflow_empty_workflow(
        self, client, test_data, auth_headers, db_session
    ):
        """Test workflow with no nodes."""
        # Create empty workflow
        empty_workflow = Workflow(
            name="Empty Workflow",
            description="Workflow with no nodes",
            team_id=test_data["team"].id,
        )
        db_session.add(empty_workflow)
        db_session.commit()
        db_session.refresh(empty_workflow)

        request_data = {
            "workflow_id": empty_workflow.id,
            "starting_inputs": {"input": "test"},
        }

        response = client.post(
            "/api/v1/chat/workflows:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "steps" in data
        assert len(data["steps"]) == 0  # No steps for empty workflow

    def test_run_workflow_with_starting_inputs(self, client, test_data, auth_headers):
        """Test workflow run with starting inputs."""
        request_data = {
            "workflow_id": test_data["workflow"].id,
            "starting_inputs": {
                "user_input": "Hello world",
                "config": {"mode": "test"},
            },
        }

        response = client.post(
            "/api/v1/chat/workflows:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "run_id" in data
        assert "steps" in data
        # Starting inputs should be available to nodes during execution
