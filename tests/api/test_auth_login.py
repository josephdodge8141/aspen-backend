import pytest
import os
import uuid
import time
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models.team import Team, Member
from app.models.users import User
from app.security.passwords import hash_password
from app.security.jwt import decode_access_token
from app.api.deps import get_db_session


@pytest.fixture
def auth_client(db_session: Session):
    def get_test_db():
        return db_session

    app.dependency_overrides[get_db_session] = get_test_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_login_success(db_session: Session, auth_client: TestClient):
    # Set up JWT secret for testing
    os.environ["JWT_SECRET"] = "test-secret-key"

    # Create test data
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

    password = "test_password_123"
    user = User(member_id=member.id, password_hash=hash_password(password))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Test login
    response = auth_client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": password}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Verify token is valid
    token_data = decode_access_token(data["access_token"])
    assert token_data.sub == str(user.id)


def test_login_invalid_email(auth_client: TestClient):
    response = auth_client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "any_password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_invalid_password(db_session: Session, auth_client: TestClient):
    # Create test member without user
    member = Member(
        first_name="Test", last_name="User", email=f"test.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=hash_password("correct_password"))
    db_session.add(user)
    db_session.commit()

    response = auth_client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": "wrong_password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_member_without_user(db_session: Session, auth_client: TestClient):
    # Create member but no corresponding user
    member = Member(
        first_name="Test", last_name="User", email=f"test.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()

    response = auth_client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": "any_password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_user_without_password(db_session: Session, auth_client: TestClient):
    # Create member and user but no password
    member = Member(
        first_name="Test", last_name="User", email=f"test.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)

    user = User(member_id=member.id, password_hash=None)  # No password set
    db_session.add(user)
    db_session.commit()

    response = auth_client.post(
        "/api/v1/auth/login", json={"email": member.email, "password": "any_password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_token_expiry():
    # Test with very short expiry
    os.environ["JWT_SECRET"] = "test-secret-key"
    os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "0"  # Expires immediately

    from app.security.jwt import create_access_token

    token = create_access_token(user_id=1, expires_minutes=0)

    # Wait a moment to ensure expiry
    time.sleep(1)

    with pytest.raises(ValueError, match="Token has expired"):
        decode_access_token(token)

    # Clean up
    os.environ.pop("ACCESS_TOKEN_EXPIRE_MINUTES", None)


def test_login_invalid_email_format(auth_client: TestClient):
    response = auth_client.post(
        "/api/v1/auth/login", json={"email": "not-an-email", "password": "any_password"}
    )

    assert response.status_code == 422  # Validation error
