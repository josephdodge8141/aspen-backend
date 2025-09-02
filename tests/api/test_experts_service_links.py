import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch
import os

from app.main import app
from app.models.experts import Expert, ExpertStatus, ExpertService
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
    """Create test data with teams, users, experts, and services."""
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
        status=ExpertStatus.active
    )
    db_session.add(expert)
    db_session.commit()
    db_session.refresh(expert)

    # Create services
    import uuid
    service1 = Service(
        name=f"Test Service 1 {uuid.uuid4().hex[:8]}",
        environment=Environment.dev,
        api_key_hash="test_hash_1",
        api_key_last4="1234"
    )
    service2 = Service(
        name=f"Test Service 2 {uuid.uuid4().hex[:8]}",
        environment=Environment.stage,
        api_key_hash="test_hash_2",
        api_key_last4="5678"
    )
    service3 = Service(
        name=f"Test Service 3 {uuid.uuid4().hex[:8]}",
        environment=Environment.prod,
        api_key_hash="test_hash_3",
        api_key_last4="9012"
    )
    db_session.add_all([service1, service2, service3])
    db_session.commit()
    db_session.refresh(service1)
    db_session.refresh(service2)
    db_session.refresh(service3)

    return {
        "team": team,
        "member": member,
        "user": user,
        "expert": expert,
        "service1": service1,
        "service2": service2,
        "service3": service3,
    }


@pytest.fixture
def auth_headers(test_data):
    """Create JWT auth headers for testing."""
    os.environ["JWT_SECRET"] = "test-secret-key"
    token = create_access_token(user_id=test_data["user"].id)
    return {"Authorization": f"Bearer {token}"}


class TestAddServiceLinks:
    """Test adding service links to experts."""

    def test_add_services_success(self, client, test_data, auth_headers):
        """Test successfully adding service links."""
        service_ids = [test_data["service1"].id, test_data["service2"].id]
        
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/services",
            json={"service_ids": service_ids},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert "services" in data
        assert len(data["services"]) == 2
        
        # Check that services are in the response
        service_envs = [s["environment"] for s in data["services"]]
        assert "dev" in service_envs
        assert "stage" in service_envs

    def test_add_services_duplicate_is_noop(self, client, test_data, auth_headers, db_session):
        """Test that adding duplicate service links is a no-op."""
        # First, add a service link directly
        existing_link = ExpertService(
            expert_id=test_data["expert"].id,
            service_id=test_data["service1"].id
        )
        db_session.add(existing_link)
        db_session.commit()

        # Now try to add the same service again via API
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/services",
            json={"service_ids": [test_data["service1"].id]},
            headers=auth_headers
        )
        assert response.status_code == 200

        data = response.json()
        assert len(data["services"]) == 1
        assert data["services"][0]["environment"] == "dev"

    def test_add_services_unknown_service_id(self, client, test_data, auth_headers):
        """Test adding unknown service ID returns 404."""
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/services",
            json={"service_ids": [99999]},  # Non-existent service
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "Service with id 99999 not found" in response.text

    def test_add_services_unknown_expert(self, client, test_data, auth_headers):
        """Test adding services to unknown expert returns 404."""
        response = client.post(
            "/api/v1/experts/99999/services",
            json={"service_ids": [test_data["service1"].id]},
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "Expert not found" in response.text

    def test_add_services_requires_auth(self, client, test_data):
        """Test that adding services requires authentication."""
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/services",
            json={"service_ids": [test_data["service1"].id]}
        )
        assert response.status_code == 401

    @patch("app.security.permissions.require_team_admin")
    def test_add_services_requires_team_admin(self, mock_require_admin, client, test_data, auth_headers):
        """Test that adding services requires team admin permissions."""
        from fastapi import HTTPException
        mock_require_admin.side_effect = HTTPException(status_code=403, detail="forbidden")

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/services",
            json={"service_ids": [test_data["service1"].id]},
            headers=auth_headers
        )
        assert response.status_code == 403


class TestRemoveServiceLinks:
    """Test removing service links from experts."""

    def test_remove_service_success(self, client, test_data, auth_headers, db_session):
        """Test successfully removing a service link."""
        # First, add a service link
        existing_link = ExpertService(
            expert_id=test_data["expert"].id,
            service_id=test_data["service1"].id
        )
        db_session.add(existing_link)
        db_session.commit()

        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/services/{test_data['service1'].id}",
            headers=auth_headers
        )
        assert response.status_code == 204

    def test_remove_service_not_linked(self, client, test_data, auth_headers):
        """Test removing a service that's not linked is idempotent (204)."""
        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/services/{test_data['service1'].id}",
            headers=auth_headers
        )
        assert response.status_code == 204

    def test_remove_service_unknown_expert(self, client, test_data, auth_headers):
        """Test removing service from unknown expert returns 404."""
        response = client.delete(
            f"/api/v1/experts/99999/services/{test_data['service1'].id}",
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "Expert not found" in response.text

    def test_remove_service_requires_auth(self, client, test_data):
        """Test that removing services requires authentication."""
        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/services/{test_data['service1'].id}"
        )
        assert response.status_code == 401

    @patch("app.security.permissions.require_team_admin")
    def test_remove_service_requires_team_admin(self, mock_require_admin, client, test_data, auth_headers):
        """Test that removing services requires team admin permissions."""
        from fastapi import HTTPException
        mock_require_admin.side_effect = HTTPException(status_code=403, detail="forbidden")

        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/services/{test_data['service1'].id}",
            headers=auth_headers
        )
        assert response.status_code == 403


class TestServiceLinksIntegration:
    """Integration tests for service link management."""

    def test_add_and_remove_service_updates_counts(self, client, test_data, auth_headers):
        """Test that adding and removing services updates the counts in expanded view."""
        # Initially no services
        response = client.get(f"/api/v1/experts/{test_data['expert'].id}", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["services"]) == 0

        # Add services
        service_ids = [test_data["service1"].id, test_data["service2"].id]
        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}/services",
            json={"service_ids": service_ids},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert len(response.json()["services"]) == 2

        # Remove one service
        response = client.delete(
            f"/api/v1/experts/{test_data['expert'].id}/services/{test_data['service1'].id}",
            headers=auth_headers
        )
        assert response.status_code == 204

        # Check updated count
        response = client.get(f"/api/v1/experts/{test_data['expert'].id}", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["services"]) == 1
        assert response.json()["services"][0]["environment"] == "stage" 