import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch

from app.main import app
from app.models.experts import Expert, ExpertStatus
from app.models.team import Team, Member, TeamMember, TeamRole
from app.models.users import User
from app.models.services import Service
from app.models.experts import ExpertService
from app.models.common import Environment
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

    # Create expert
    expert = Expert(
        name="Test Expert",
        prompt="Hello {{ input.name }}, today is {{ base.date }}!",
        model_name="gpt-4",
        input_params={"temperature": 0.7},
        status=ExpertStatus.active,
        team_id=team.id,
    )
    db_session.add(expert)
    db_session.commit()
    db_session.refresh(expert)

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

    # Create expert-service link
    expert_service = ExpertService(expert_id=expert.id, service_id=service.id)
    db_session.add(expert_service)
    db_session.commit()

    return {"team": team, "user": user, "expert": expert, "service": service}


@pytest.fixture
def auth_headers(test_data):
    token = create_access_token(test_data["user"].id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def service_headers():
    return {"X-API-Key": "test_key"}


class TestRunExpert:
    def test_run_expert_success_with_user(self, client, test_data, auth_headers):
        """Test successful expert run with user authentication."""
        request_data = {
            "expert_id": test_data["expert"].id,
            "input_params": {"name": "Alice"},
            "base": {"custom": "value"},
        }

        response = client.post(
            "/api/v1/chat/experts:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "run_id" in data
        assert "messages" in data
        assert len(data["messages"]) == 2

        # Check user message (rendered prompt)
        user_message = data["messages"][0]
        assert user_message["role"] == "user"
        assert "Hello Alice" in user_message["content"]
        assert "today is" in user_message["content"]

        # Check assistant message (stubbed)
        assistant_message = data["messages"][1]
        assert assistant_message["role"] == "assistant"
        assert "stubbed response from gpt-4" in assistant_message["content"]

    @patch("app.security.apikeys.hash_api_key")
    def test_run_expert_success_with_service(
        self, mock_hash, client, test_data, service_headers
    ):
        """Test successful expert run with service authentication."""
        mock_hash.return_value = "test_hash"

        request_data = {
            "expert_id": test_data["expert"].id,
            "input_params": {"name": "Bob"},
        }

        response = client.post(
            "/api/v1/chat/experts:run", json=request_data, headers=service_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert "run_id" in data
        assert "messages" in data
        assert "Hello Bob" in data["messages"][0]["content"]

    def test_run_expert_not_found(self, client, auth_headers):
        """Test expert not found error."""
        request_data = {"expert_id": 99999, "input_params": {"name": "Alice"}}

        response = client.post(
            "/api/v1/chat/experts:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 404
        assert "Expert not found" in response.text

    def test_run_expert_no_auth(self, client, test_data):
        """Test authentication required error."""
        request_data = {
            "expert_id": test_data["expert"].id,
            "input_params": {"name": "Alice"},
        }

        response = client.post("/api/v1/chat/experts:run", json=request_data)

        assert response.status_code == 401

    @patch("app.security.apikeys.hash_api_key")
    def test_run_expert_service_not_linked(
        self, mock_hash, client, test_data, db_session
    ):
        """Test service not authorized for expert."""
        mock_hash.return_value = "different_hash"

        # Create another service not linked to the expert
        other_service = Service(
            name="Other Service",
            api_key_hash="different_hash",
            team_id=test_data["team"].id,
        )
        db_session.add(other_service)
        db_session.commit()

        request_data = {
            "expert_id": test_data["expert"].id,
            "input_params": {"name": "Alice"},
        }

        response = client.post(
            "/api/v1/chat/experts:run",
            json=request_data,
            headers={"X-API-Key": "other_key"},
        )

        assert response.status_code == 403
        assert "not authorized to use this expert" in response.text

    def test_run_expert_user_not_team_member(self, client, test_data, db_session):
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
            "expert_id": test_data["expert"].id,
            "input_params": {"name": "Alice"},
        }

        response = client.post(
            "/api/v1/chat/experts:run", json=request_data, headers=headers
        )

        assert response.status_code == 403

    def test_run_expert_prompt_rendering_warnings(
        self, client, test_data, auth_headers
    ):
        """Test expert run with prompt rendering warnings."""
        request_data = {
            "expert_id": test_data["expert"].id,
            "input_params": {"unknown": "value"},  # Missing 'name' field
        }

        response = client.post(
            "/api/v1/chat/experts:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should still work but with placeholder left unresolved
        user_message = data["messages"][0]["content"]
        assert "{{ input.name }}" in user_message  # Unresolved placeholder

    def test_run_expert_minimal_request(self, client, test_data, auth_headers):
        """Test expert run with minimal request data."""
        request_data = {"expert_id": test_data["expert"].id}

        response = client.post(
            "/api/v1/chat/experts:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert "messages" in data

    def test_run_expert_base_overrides(self, client, test_data, auth_headers):
        """Test expert run with base value overrides."""
        request_data = {
            "expert_id": test_data["expert"].id,
            "input_params": {"name": "Charlie"},
            "base": {"date": "2024-01-01"},  # Override default date
        }

        response = client.post(
            "/api/v1/chat/experts:run", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        user_message = data["messages"][0]["content"]
        assert "Hello Charlie" in user_message
        assert "2024-01-01" in user_message
