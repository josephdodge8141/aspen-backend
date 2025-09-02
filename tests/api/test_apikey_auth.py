import pytest
import uuid
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models.services import Service
from app.models.team import Team, Member
from app.models.users import User
from app.models.common import Environment
from app.security.apikeys import generate_api_key, hash_api_key
from app.security.passwords import hash_password
from app.api.deps import get_db_session, get_caller


@pytest.fixture
def auth_client(db_session: Session):
    def get_test_db():
        return db_session

    app.dependency_overrides[get_db_session] = get_test_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_valid_api_key(db_session: Session, auth_client: TestClient):
    # Create a service with API key
    plaintext_key, api_key_hash, last4 = generate_api_key()

    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=last4,
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)

    # Create a simple endpoint that uses get_caller
    from fastapi import Depends
    from app.api.deps import CallerContext

    @app.get("/test-api-key")
    async def test_endpoint(caller: CallerContext = Depends(get_caller)):
        if caller.service:
            return {
                "service_id": caller.service.id,
                "service_name": caller.service.name,
            }
        return {"user_id": caller.user.id}

    # Test with valid API key
    response = auth_client.get("/test-api-key", headers={"X-API-Key": plaintext_key})

    assert response.status_code == 200
    data = response.json()
    assert data["service_id"] == service.id
    assert data["service_name"] == service.name


def test_invalid_api_key(auth_client: TestClient):
    # Test with invalid API key
    response = auth_client.get("/test-api-key", headers={"X-API-Key": "invalid-key"})

    assert response.status_code == 401
    assert response.headers.get("Content-Type") == "application/problem+json"
    assert response.json()["detail"] == "Invalid API key"


def test_valid_jwt_token(db_session: Session, auth_client: TestClient):
    import os

    os.environ["JWT_SECRET"] = "test-secret-key"

    # Create test user data
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    member = Member(
        first_name="Test", last_name="User", email=f"test.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=hash_password("test_password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Login to get JWT token
    login_response = auth_client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": "test_password"}
    )

    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    # Test with valid JWT token
    response = auth_client.get(
        "/test-api-key", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user.id


def test_no_authentication(auth_client: TestClient):
    # Test with no authentication headers
    response = auth_client.get("/test-api-key")

    assert response.status_code == 401
    assert response.headers.get("Content-Type") == "application/problem+json"
    assert response.json()["detail"] == "Authentication required"


def test_invalid_jwt_token(auth_client: TestClient):
    # Test with invalid JWT token
    response = auth_client.get(
        "/test-api-key", headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401
    assert response.headers.get("Content-Type") == "application/problem+json"
    assert (
        "Invalid token" in response.json()["detail"]
        or "JWT_SECRET" in response.json()["detail"]
    )


def test_malformed_authorization_header(auth_client: TestClient):
    # Test with malformed Authorization header
    response = auth_client.get(
        "/test-api-key", headers={"Authorization": "NotBearer token"}
    )

    assert response.status_code == 401
    assert response.headers.get("Content-Type") == "application/problem+json"
    assert response.json()["detail"] == "Authentication required"


def test_both_api_key_and_jwt_prefers_jwt(db_session: Session, auth_client: TestClient):
    # According to the spec: "if both provided, prefer JWT for admin endpoints"
    import os

    os.environ["JWT_SECRET"] = "test-secret-key"

    # Create service with API key
    plaintext_key, api_key_hash, last4 = generate_api_key()
    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create user with JWT
    team = Team(name=f"Test Team {uuid.uuid4()}")
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    member = Member(
        first_name="Test", last_name="User", email=f"test.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=hash_password("test_password"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Get JWT token
    login_response = auth_client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": "test_password"}
    )
    token = login_response.json()["access_token"]

    # Test with both headers - should use JWT (user takes precedence)
    response = auth_client.get(
        "/test-api-key",
        headers={"X-API-Key": plaintext_key, "Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    # Should get user_id, not service_id (JWT takes precedence)
    assert "user_id" in data
    assert data["user_id"] == user.id
