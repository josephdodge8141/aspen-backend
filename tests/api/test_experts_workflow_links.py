import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch
import os

from app.main import app
from app.models.experts import Expert, ExpertStatus, ExpertWorkflow
from app.models.workflows import Workflow
from app.models.team import Team, TeamMember, TeamRole
from app.models.users import User
from app.models.team import Member
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
    """Create test data with teams, users, experts, and workflows."""
    # Create team
    team = Team(name="Test Team")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Create member and user
    member = Member(email="admin@test.com", first_name="Admin", last_name="User")
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash="hashed_password")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create team membership
    team_member = TeamMember(team_id=team.id, member_id=member.id, role=TeamRole.admin)
    db_session.add(team_member)
    db_session.commit()

    # Create expert
    expert = Expert(
        name="Test Expert",
        prompt="Test prompt for the expert",
        model_name="gpt-4",
        input_params={"param1": "value1"},
        team_id=team.id,
        status=ExpertStatus.active,
    )
    db_session.add(expert)
    db_session.commit()
    db_session.refresh(expert)

    # Create workflows
    workflow1 = Workflow(name="Test Workflow 1", team_id=team.id)
    workflow2 = Workflow(name="Test Workflow 2", team_id=team.id)
    workflow3 = Workflow(name="Test Workflow 3", team_id=team.id)
    db_session.add_all([workflow1, workflow2, workflow3])
    db_session.commit()
    db_session.refresh(workflow1)
    db_session.refresh(workflow2)
    db_session.refresh(workflow3)

    return {
        "team": team,
        "member": member,
        "user": user,
        "expert": expert,
        "workflow1": workflow1,
        "workflow2": workflow2,
        "workflow3": workflow3,
    }


@pytest.fixture
def auth_headers(test_data):
    """Create JWT auth headers for testing."""
    os.environ["JWT_SECRET"] = "test-secret-key"
    token = create_access_token(user_id=test_data["user"].id)
    return {"Authorization": f"Bearer {token}"}


class TestAddWorkflowLinks:
    """Test adding workflow links to experts."""

    def test_add_workflows_success(self, client, test_data, auth_headers):
        """Test successfully adding workflow links."""
        workflow_ids = [test_data["workflow1"].id, test_data["workflow2"].id]

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/workflows",
            json={"workflow_ids": workflow_ids},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert "workflows" in data
        assert len(data["workflows"]) == 2

        # Check that workflows are in the response
        workflow_names = [w["name"] for w in data["workflows"]]
        assert "Test Workflow 1" in workflow_names
        assert "Test Workflow 2" in workflow_names

    def test_add_workflows_duplicate_is_noop(
        self, client, test_data, auth_headers, db_session
    ):
        """Test that adding duplicate workflow links is a no-op."""
        # First, add a workflow link directly
        existing_link = ExpertWorkflow(
            expert_id=test_data["expert"].id, workflow_id=test_data["workflow1"].id
        )
        db_session.add(existing_link)
        db_session.commit()

        # Now try to add the same workflow again via API
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/workflows",
            json={"workflow_ids": [test_data["workflow1"].id]},
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["workflows"]) == 1
        assert data["workflows"][0]["name"] == "Test Workflow 1"

    def test_add_workflows_unknown_workflow_id(self, client, test_data, auth_headers):
        """Test adding unknown workflow ID returns 404."""
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/workflows",
            json={"workflow_ids": [99999]},  # Non-existent workflow
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "Workflow with id 99999 not found" in response.text

    def test_add_workflows_unknown_expert(self, client, test_data, auth_headers):
        """Test adding workflows to unknown expert returns 404."""
        response = client.post(
            "/api/v1/experts/99999/workflows",
            json={"workflow_ids": [test_data["workflow1"].id]},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "Expert not found" in response.text

    def test_add_workflows_requires_auth(self, client, test_data):
        """Test that adding workflows requires authentication."""
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/workflows",
            json={"workflow_ids": [test_data["workflow1"].id]},
        )
        assert response.status_code == 401

    @patch("app.api.experts.require_team_admin")
    def test_add_workflows_requires_team_admin(
        self, mock_require_admin, client, test_data, auth_headers
    ):
        """Test that adding workflows requires team admin permissions."""
        from fastapi import HTTPException

        mock_require_admin.side_effect = HTTPException(
            status_code=403, detail="forbidden"
        )

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/workflows",
            json={"workflow_ids": [test_data["workflow1"].id]},
            headers=auth_headers,
        )
        assert response.status_code == 403


class TestRemoveWorkflowLinks:
    """Test removing workflow links from experts."""

    def test_remove_workflow_success(self, client, test_data, auth_headers, db_session):
        """Test successfully removing a workflow link."""
        # First, add a workflow link
        existing_link = ExpertWorkflow(
            expert_id=test_data["expert"].id, workflow_id=test_data["workflow1"].id
        )
        db_session.add(existing_link)
        db_session.commit()

        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/workflows/{test_data['workflow1'].id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_remove_workflow_not_linked(self, client, test_data, auth_headers):
        """Test removing a workflow that's not linked is idempotent (204)."""
        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/workflows/{test_data['workflow1'].id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_remove_workflow_unknown_expert(self, client, test_data, auth_headers):
        """Test removing workflow from unknown expert returns 404."""
        response = client.delete(
            f"/api/v1/experts/99999/workflows/{test_data['workflow1'].id}",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "Expert not found" in response.text

    def test_remove_workflow_requires_auth(self, client, test_data):
        """Test that removing workflows requires authentication."""
        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/workflows/{test_data['workflow1'].id}"
        )
        assert response.status_code == 401

    @patch("app.api.experts.require_team_admin")
    def test_remove_workflow_requires_team_admin(
        self, mock_require_admin, client, test_data, auth_headers
    ):
        """Test that removing workflows requires team admin permissions."""
        from fastapi import HTTPException

        mock_require_admin.side_effect = HTTPException(
            status_code=403, detail="forbidden"
        )

        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/workflows/{test_data['workflow1'].id}",
            headers=auth_headers,
        )
        assert response.status_code == 403


class TestWorkflowLinksIntegration:
    """Integration tests for workflow link management."""

    def test_add_and_remove_workflow_updates_counts(
        self, client, test_data, auth_headers
    ):
        """Test that adding and removing workflows updates the counts in expanded view."""
        # Initially no workflows
        response = client.get(
            f"/api/v1/experts/{test_data['expert'].id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()["workflows"]) == 0

        # Add workflows
        workflow_ids = [test_data["workflow1"].id, test_data["workflow2"].id]
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/workflows",
            json={"workflow_ids": workflow_ids},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert len(response.json()["workflows"]) == 2

        # Remove one workflow
        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/workflows/{test_data['workflow1'].id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Check updated count
        response = client.get(
            f"/api/v1/experts/{test_data['expert'].id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()["workflows"]) == 1
        assert response.json()["workflows"][0]["name"] == "Test Workflow 2"
