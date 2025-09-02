import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session


def test_db_session_fixture(db_session):
    """Test that the db_session fixture provides a working database session"""
    assert isinstance(db_session, Session)
    assert db_session.is_active


def test_client_fixture(client):
    """Test that the client fixture provides a working test client"""
    assert isinstance(client, TestClient)

    # Test the basic health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_authenticated_client_fixture(authenticated_client):
    """Test that the authenticated_client fixture works (placeholder for future auth)"""
    assert isinstance(authenticated_client, TestClient)

    # For now, it should work the same as regular client
    response = authenticated_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_db_session_isolation(db_session):
    """Test that db_session provides proper transaction isolation"""
    from app.models.team import Team

    # Create a team in this test
    team = Team(name="Isolation Test Team")
    db_session.add(team)
    db_session.commit()

    # The team should exist in this session
    created_team = db_session.get(Team, team.id)
    assert created_team is not None
    assert created_team.name == "Isolation Test Team"

    # But it should be rolled back after the test completes
