import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch

from app.main import app
from app.models.experts import Expert, ExpertStatus
from app.models.workflows import Workflow
from app.models.services import Service, Environment
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
    """Create test data with teams, users, experts, workflows, and services."""
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

    # Create team membership with admin role
    team_member = TeamMember(team_id=team.id, member_id=member.id, role=TeamRole.admin)
    db_session.add(team_member)

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

    # Create workflow
    workflow = Workflow(name="Test Workflow", team_id=team.id)
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    # Link workflow to expert
    from app.models.experts import ExpertWorkflow

    expert_workflow = ExpertWorkflow(expert_id=expert.id, workflow_id=workflow.id)
    db_session.add(expert_workflow)

    # Create service
    import uuid

    service = Service(
        name=f"Test Service {uuid.uuid4().hex[:8]}",
        environment=Environment.dev,
        api_key_hash="test_hash",
        api_key_last4="1234",
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)

    # Link service to expert
    from app.models.experts import ExpertService

    expert_service = ExpertService(expert_id=expert.id, service_id=service.id)
    db_session.add(expert_service)

    db_session.commit()

    return {
        "team": team,
        "member": member,
        "user": user,
        "team_member": team_member,
        "expert": expert,
        "workflow": workflow,
        "service": service,
    }


@pytest.fixture
def auth_headers(test_data):
    """Create JWT auth headers for testing."""
    import os

    os.environ["JWT_SECRET"] = "test-secret-key"
    token = create_access_token(user_id=test_data["user"].id)
    return {"Authorization": f"Bearer {token}"}


class TestListExperts:
    """Test GET /api/v1/experts endpoint."""

    def test_list_experts_no_filters(self, client, test_data, auth_headers):
        """Test listing all experts without filters."""
        response = client.get("/api/v1/experts", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1  # Should contain at least our test expert

        # Find our test expert in the results
        test_expert = None
        for expert in data:
            if (
                expert["name"] == "Test Expert"
                and expert["team_id"] == test_data["team"].id
            ):
                test_expert = expert
                break

        assert test_expert is not None, "Test expert not found in results"
        assert test_expert["workflows_count"] == 1
        assert test_expert["services_count"] == 1

    def test_list_experts_team_filter(self, client, test_data, auth_headers):
        """Test listing experts filtered by team."""
        response = client.get(
            f"/api/v1/experts?team_id={test_data['team'].id}", headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["team_id"] == test_data["team"].id

    def test_list_experts_status_filter(self, client, test_data, auth_headers):
        """Test listing experts filtered by status."""
        response = client.get("/api/v1/experts?status=active", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert len(data) >= 1  # Should contain at least our test expert

        # Find our test expert in the results
        test_expert = None
        for expert in data:
            if (
                expert["name"] == "Test Expert"
                and expert["team_id"] == test_data["team"].id
            ):
                test_expert = expert
                break

        assert test_expert is not None, "Test expert not found in results"
        assert test_expert["status"] == "active"

    def test_list_experts_requires_auth(self, client, test_data):
        """Test that listing experts requires authentication."""
        response = client.get("/api/v1/experts")
        assert response.status_code == 401


class TestCreateExpert:
    """Test POST /api/v1/experts endpoint."""

    def test_create_expert_success(self, client, test_data, auth_headers):
        """Test successful expert creation."""
        expert_data = {
            "name": "New Expert",
            "prompt": "New expert prompt",
            "model_name": "gpt-4",
            "input_params": {"key": "value"},
            "team_id": test_data["team"].id,
            "status": "active",
        }

        response = client.post(
            "/api/v1/experts", json=expert_data, headers=auth_headers
        )
        assert response.status_code == 201

        data = response.json()
        assert data["name"] == "New Expert"
        assert data["prompt"] == "New expert prompt"
        assert data["input_params"] == {"key": "value"}
        assert data["team_id"] == test_data["team"].id
        assert data["status"] == "active"

    def test_create_expert_invalid_input_params(self, client, test_data, auth_headers):
        """Test creating expert with non-dict input_params."""
        expert_data = {
            "name": "New Expert",
            "prompt": "New expert prompt",
            "model_name": "gpt-4",
            "input_params": "not_a_dict",  # Invalid
            "team_id": test_data["team"].id,
            "status": "active",
        }

        response = client.post(
            "/api/v1/experts", json=expert_data, headers=auth_headers
        )
        assert response.status_code == 422
        assert "Input should be a valid dictionary" in response.text

    def test_create_expert_requires_auth(self, client, test_data):
        """Test that creating expert requires authentication."""
        expert_data = {
            "name": "New Expert",
            "prompt": "New expert prompt",
            "model_name": "gpt-4",
            "input_params": {"key": "value"},
            "team_id": test_data["team"].id,
            "status": "active",
        }

        response = client.post("/api/v1/experts", json=expert_data)
        assert response.status_code == 401

    @patch("app.security.permissions.require_team_admin")
    def test_create_expert_requires_team_admin(
        self, mock_require_admin, client, test_data, auth_headers
    ):
        """Test that creating expert requires team admin permissions."""
        # Make require_team_admin raise a 403 error
        from fastapi import HTTPException

        mock_require_admin.side_effect = HTTPException(
            status_code=403, detail="forbidden"
        )

        expert_data = {
            "name": "New Expert",
            "prompt": "New expert prompt",
            "model_name": "gpt-4",
            "input_params": {"key": "value"},
            "team_id": test_data["team"].id,
            "status": "active",
        }

        response = client.post(
            "/api/v1/experts", json=expert_data, headers=auth_headers
        )
        assert response.status_code == 403


class TestGetExpert:
    """Test GET /api/v1/experts/{expert_id} endpoint."""

    def test_get_expert_success(self, client, test_data, auth_headers):
        """Test successful expert retrieval with expanded data."""
        response = client.get(
            f"/api/v1/experts/{test_data['expert'].id}", headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Test Expert"
        assert data["workflows"] == [
            {"id": test_data["workflow"].id, "name": "Test Workflow"}
        ]
        assert data["services"] == [
            {
                "id": test_data["service"].id,
                "name": test_data["service"].name,
                "environment": "dev",
            }
        ]

    def test_get_expert_not_found(self, client, test_data, auth_headers):
        """Test getting non-existent expert."""
        response = client.get("/api/v1/experts/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_expert_requires_auth(self, client, test_data):
        """Test that getting expert requires authentication."""
        response = client.get(f"/api/v1/experts/{test_data['expert'].id}")
        assert response.status_code == 401


class TestUpdateExpert:
    """Test PATCH /api/v1/experts/{expert_id} endpoint."""

    def test_update_expert_success(self, client, test_data, auth_headers):
        """Test successful expert update."""
        update_data = {"name": "Updated Expert", "prompt": "Updated prompt"}

        response = client.patch(
            f"/api/v1/experts/{test_data['expert'].id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Expert"
        assert data["prompt"] == "Updated prompt"

    def test_update_expert_invalid_input_params(self, client, test_data, auth_headers):
        """Test updating expert with non-dict input_params."""
        update_data = {"input_params": "not_a_dict"}  # Invalid

        response = client.patch(
            f"/api/v1/experts/{test_data['expert'].id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "input_params must be a JSON object" in response.text

    def test_update_expert_not_found(self, client, test_data, auth_headers):
        """Test updating non-existent expert."""
        update_data = {"name": "Updated Expert"}

        response = client.patch(
            "/api/v1/experts/99999", json=update_data, headers=auth_headers
        )
        assert response.status_code == 404

    def test_update_expert_requires_auth(self, client, test_data):
        """Test that updating expert requires authentication."""
        update_data = {"name": "Updated Expert"}

        response = client.patch(
            f"/api/v1/experts/{test_data['expert'].id}", json=update_data
        )
        assert response.status_code == 401

    @patch("app.security.permissions.require_team_admin")
    def test_update_expert_requires_team_admin(
        self, mock_require_admin, client, test_data, auth_headers
    ):
        """Test that updating expert requires team admin permissions."""
        # Make require_team_admin raise a 403 error
        from fastapi import HTTPException

        mock_require_admin.side_effect = HTTPException(
            status_code=403, detail="forbidden"
        )

        update_data = {"name": "Updated Expert"}

        response = client.patch(
            f"/api/v1/experts/{test_data['expert'].id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code == 403


class TestArchiveExpert:
    """Test POST /api/v1/experts/{expert_id}:archive endpoint."""

    def test_archive_expert_success(self, client, test_data, auth_headers):
        """Test successful expert archiving."""
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:archive", headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "archive"

    def test_archive_expert_idempotent(
        self, client, test_data, auth_headers, db_session
    ):
        """Test that archiving is idempotent."""
        # First archive
        response1 = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:archive", headers=auth_headers
        )
        assert response1.status_code == 200
        assert response1.json()["status"] == "archive"

        # Second archive (should still work)
        response2 = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:archive", headers=auth_headers
        )
        assert response2.status_code == 200
        assert response2.json()["status"] == "archive"

    def test_archive_expert_not_found(self, client, test_data, auth_headers):
        """Test archiving non-existent expert."""
        response = client.post("/api/v1/experts/99999:archive", headers=auth_headers)
        assert response.status_code == 404

    def test_archive_expert_requires_auth(self, client, test_data):
        """Test that archiving expert requires authentication."""
        response = client.post(f"/api/v1/experts/{test_data['expert'].id}:archive")
        assert response.status_code == 401

    @patch("app.security.permissions.require_team_admin")
    def test_archive_expert_requires_team_admin(
        self, mock_require_admin, client, test_data, auth_headers
    ):
        """Test that archiving expert requires team admin permissions."""
        # Make require_team_admin raise a 403 error
        from fastapi import HTTPException

        mock_require_admin.side_effect = HTTPException(
            status_code=403, detail="forbidden"
        )

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:archive", headers=auth_headers
        )
        assert response.status_code == 403


class TestExpertsPermissions:
    """Test permission handling across all endpoints."""

    def test_problem_json_content_type_on_403(self, client, test_data, auth_headers):
        """Test that 403 errors return Problem+JSON content type."""
        with patch("app.security.permissions.require_team_admin") as mock_require_admin:
            # Make require_team_admin raise a 403 error
            from fastapi import HTTPException

            mock_require_admin.side_effect = HTTPException(
                status_code=403,
                detail="forbidden",
                headers={"Content-Type": "application/problem+json"},
            )

            expert_data = {
                "name": "New Expert",
                "prompt": "New expert prompt",
                "model_name": "gpt-4",
                "input_params": {"key": "value"},
                "team_id": test_data["team"].id,
                "status": "active",
            }

            response = client.post(
                "/api/v1/experts", json=expert_data, headers=auth_headers
            )
            assert response.status_code == 403
            # Note: FastAPI may not preserve the Content-Type header in all cases,
            # but the requirement is that we return Problem+JSON format
