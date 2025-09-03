import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session
from unittest.mock import patch

from app.main import app
from app.api.deps import get_db_session
from app.models.services import Service
from app.models.common import Environment
from app.security.jwt import create_access_token
from app.models.team import Team, Member, TeamMember
from app.models.users import User
from app.models.common import TeamRole


client = TestClient(app)


@pytest.fixture
def test_data(db_session: Session):
    import uuid

    # Create team
    team = Team(name="Test Team")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    # Create member
    unique_email = f"test-{uuid.uuid4()}@example.com"
    member = Member(first_name="Test", last_name="User", email=unique_email)
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    # Create user linked to member
    user = User(
        email=unique_email,
        username=f"testuser-{uuid.uuid4()}",
        hashed_password="hashed_password",
        member_id=member.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create team membership
    membership = TeamMember(team_id=team.id, member_id=member.id, role=TeamRole.admin)
    db_session.add(membership)
    db_session.commit()

    return {"team": team, "user": user, "member": member}


@pytest.fixture
def auth_headers(test_data):
    token = create_access_token(test_data["user"].id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_with_db(db_session):
    """Create a test client with database session override"""

    def get_test_db():
        return db_session

    app.dependency_overrides[get_db_session] = get_test_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up override
    app.dependency_overrides.clear()


class TestServiceCRUD:
    def test_create_service_success(self, client_with_db, test_data, auth_headers):
        """Test successful service creation."""
        import uuid

        request_data = {"name": f"Test Service {uuid.uuid4()}", "environment": "dev"}

        response = client_with_db.post(
            "/api/v1/services", json=request_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == request_data["name"]
        assert data["environment"] == "dev"
        assert "api_key_plaintext" in data
        assert "api_key_last4" in data
        assert data["api_key_plaintext"].startswith("sk-")
        assert len(data["api_key_last4"]) == 4

    def test_create_service_duplicate_name_environment(
        self, client_with_db, test_data, auth_headers, db_session
    ):
        """Test that duplicate service name+environment combination is rejected."""
        # Create first service
        service = Service(
            name="Duplicate Service",
            environment=Environment.dev,
            api_key_hash="test_hash",
            api_key_last4="1234",
        )
        db_session.add(service)
        db_session.commit()

        # Try to create duplicate
        request_data = {"name": "Duplicate Service", "environment": "dev"}

        response = client_with_db.post(
            "/api/v1/services", json=request_data, headers=auth_headers
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_list_services(self, client_with_db, test_data, auth_headers, db_session):
        """Test listing services."""
        # Create test services with unique names
        import uuid

        service1_name = f"Service 1 {uuid.uuid4()}"
        service2_name = f"Service 2 {uuid.uuid4()}"

        service1 = Service(
            name=service1_name,
            environment=Environment.dev,
            api_key_hash="hash1",
            api_key_last4="1111",
        )
        service2 = Service(
            name=service2_name,
            environment=Environment.prod,
            api_key_hash="hash2",
            api_key_last4="2222",
        )
        db_session.add_all([service1, service2])
        db_session.commit()

        response = client_with_db.get("/api/v1/services", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Find our specific services in the response
        service_names = {service["name"] for service in data}
        assert service1_name in service_names
        assert service2_name in service_names

        # Check that plaintext keys are not returned
        for service in data:
            assert "api_key_plaintext" not in service
            assert "api_key_last4" in service

    def test_get_service_success(
        self, client_with_db, test_data, auth_headers, db_session
    ):
        """Test getting a specific service."""
        import uuid

        service_name = f"Test Service {uuid.uuid4()}"
        service = Service(
            name=service_name,
            environment=Environment.dev,
            api_key_hash="test_hash",
            api_key_last4="test",
        )
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)

        response = client_with_db.get(
            f"/api/v1/services/{service.id}", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == service.id
        assert data["name"] == service_name
        assert data["environment"] == "dev"
        assert data["api_key_last4"] == "test"
        assert "api_key_plaintext" not in data

    def test_get_service_not_found(self, client_with_db, test_data, auth_headers):
        """Test getting non-existent service."""
        response = client_with_db.get("/api/v1/services/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_service_success(
        self, client_with_db, test_data, auth_headers, db_session
    ):
        """Test successful service deletion."""
        import uuid

        service = Service(
            name=f"Test Service {uuid.uuid4()}",
            environment=Environment.dev,
            api_key_hash="test_hash",
            api_key_last4="test",
        )
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)

        response = client_with_db.delete(
            f"/api/v1/services/{service.id}", headers=auth_headers
        )

        assert response.status_code == 204

        # Verify service is deleted
        deleted_service = db_session.get(Service, service.id)
        assert deleted_service is None

    def test_delete_service_not_found(self, client_with_db, test_data, auth_headers):
        """Test deleting non-existent service."""
        response = client_with_db.delete("/api/v1/services/99999", headers=auth_headers)
        assert response.status_code == 404

    @patch("app.api.services.generate_api_key")
    def test_rotate_service_key_success(
        self, mock_generate, client_with_db, test_data, auth_headers, db_session
    ):
        """Test successful API key rotation."""
        # Mock the API key generation
        mock_generate.return_value = ("sk-new_key", "new_hash", "new4")

        import uuid

        service = Service(
            name=f"Test Service {uuid.uuid4()}",
            environment=Environment.dev,
            api_key_hash="old_hash",
            api_key_last4="old4",
        )
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)

        response = client_with_db.post(
            f"/api/v1/services/{service.id}:rotate-key", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["id"] == service.id
        assert data["api_key_plaintext"] == "sk-new_key"
        assert data["api_key_last4"] == "new4"

        # Verify database was updated
        db_session.refresh(service)
        assert service.api_key_hash == "new_hash"
        assert service.api_key_last4 == "new4"

    def test_rotate_service_key_not_found(
        self, client_with_db, test_data, auth_headers
    ):
        """Test key rotation for non-existent service."""
        response = client_with_db.post(
            "/api/v1/services/99999:rotate-key", headers=auth_headers
        )
        assert response.status_code == 404

    def test_unauthorized_access(self, client_with_db):
        """Test that endpoints require authentication."""
        # Test create
        response = client_with_db.post(
            "/api/v1/services", json={"name": "Test", "environment": "dev"}
        )
        assert response.status_code == 401

        # Test list
        response = client_with_db.get("/api/v1/services")
        assert response.status_code == 401

        # Test get
        response = client_with_db.get("/api/v1/services/1")
        assert response.status_code == 401

        # Test delete
        response = client_with_db.delete("/api/v1/services/1")
        assert response.status_code == 401

        # Test rotate key
        response = client_with_db.post("/api/v1/services/1:rotate-key")
        assert response.status_code == 401
