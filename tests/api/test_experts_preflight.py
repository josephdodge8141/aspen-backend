import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
import os

from app.main import app
from app.models.experts import Expert, ExpertStatus
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
    """Create test data with team, user, and expert."""
    # Create team
    team = Team(name="Test Team")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Create member and user
    member = Member(email="user@test.com", first_name="Test", last_name="User")
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create team membership
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

    return {"team": team, "user": user, "expert": expert}


@pytest.fixture
def auth_headers(test_data):
    """Create JWT auth headers for testing."""
    os.environ["JWT_SECRET"] = "test-secret-key"
    token = create_access_token(user_id=test_data["user"].id)
    return {"Authorization": f"Bearer {token}"}


class TestPreflightValidation:
    def test_preflight_valid_template(self, client, test_data, auth_headers):
        """Test preflight validation with a valid template."""
        request_data = {
            "prompt": "Hello {{base.name}}, your score is {{input.score}}",
            "input_params": {"score": 95},
        }

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:preflight",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["placeholders"] == ["base.name", "input.score"]
        assert data["warnings"] == []
        assert data["errors"] == []

    def test_preflight_template_with_warnings(self, client, test_data, auth_headers):
        """Test preflight validation with warnings."""
        request_data = {
            "prompt": "Hello {{custom.name}}, score: {{input.score}}",
            "input_params": {"score": 95},
        }

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:preflight",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["placeholders"] == ["custom.name", "input.score"]
        assert len(data["warnings"]) == 1
        assert "Unknown root in placeholder: {{custom.name}}" in data["warnings"][0]
        assert data["errors"] == []

    def test_preflight_template_with_errors(self, client, test_data, auth_headers):
        """Test preflight validation with errors."""
        request_data = {
            "prompt": "Hello {{}}, score: {{base.items[0}}",
            "input_params": {},
        }

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:preflight",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200  # Returns 200 even with errors
        data = response.json()

        assert data["placeholders"] == ["", "base.items[0"]
        assert data["warnings"] == []
        assert len(data["errors"]) == 2
        assert any("Empty placeholder" in msg for msg in data["errors"])
        assert any("Unclosed brackets" in msg for msg in data["errors"])

    def test_preflight_template_with_warnings_and_errors(
        self, client, test_data, auth_headers
    ):
        """Test preflight validation with both warnings and errors."""
        request_data = {
            "prompt": "Hello {{custom.name}}, empty: {{}}, score: {{input.score}}",
            "input_params": {"score": 95},
        }

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:preflight",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["placeholders"]) == 3
        assert len(data["warnings"]) == 1
        assert len(data["errors"]) == 1
        assert "Unknown root" in data["warnings"][0]
        assert "Empty placeholder" in data["errors"][0]

    def test_preflight_no_placeholders(self, client, test_data, auth_headers):
        """Test preflight validation with no placeholders."""
        request_data = {
            "prompt": "Hello world, no placeholders here",
            "input_params": {},
        }

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:preflight",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["placeholders"] == []
        assert data["warnings"] == []
        assert data["errors"] == []

    def test_preflight_expert_not_found(self, client, auth_headers):
        """Test preflight validation with non-existent expert."""
        request_data = {"prompt": "Hello {{base.name}}", "input_params": {}}

        response = client.post(
            "/api/v1/experts/99999:preflight", json=request_data, headers=auth_headers
        )

        assert response.status_code == 404
        assert "Expert not found" in response.text

    def test_preflight_requires_auth(self, client, test_data):
        """Test that preflight validation requires authentication."""
        request_data = {"prompt": "Hello {{base.name}}", "input_params": {}}

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:preflight", json=request_data
        )

        assert response.status_code == 401

    def test_preflight_complex_jsonata_expressions(
        self, client, test_data, auth_headers
    ):
        """Test preflight validation with complex JSONata expressions."""
        request_data = {
            "prompt": "Results: {{base.items[0].name}} and {{input.data.filter($$.type = 'active').count()}}",
            "input_params": {"data": []},
        }

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:preflight",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["placeholders"]) == 2
        assert "base.items[0].name" in data["placeholders"]
        assert "input.data.filter($$.type = 'active').count()" in data["placeholders"]
        assert data["warnings"] == []
        assert data["errors"] == []

    def test_preflight_malformed_braces(self, client, test_data, auth_headers):
        """Test preflight validation with malformed braces."""
        request_data = {
            "prompt": "Hello {{base.{name}}} and {{input.score}}",
            "input_params": {},
        }

        response = client.post(
            f"/api/v1/experts/{test_data['expert'].id}:preflight",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["errors"]) >= 1
        assert any("Malformed placeholder" in msg for msg in data["errors"])
