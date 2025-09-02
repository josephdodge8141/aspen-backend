import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import engine


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine that can be shared across tests"""
    # Use the same engine as the main app for integration tests
    return engine


@pytest.fixture
def db_session(test_engine):
    """
    Create a database session for testing with proper transaction isolation.
    Each test gets a fresh session that rolls back after the test completes.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client():
    """
    Create a test client with authentication headers.
    This is a placeholder for future authentication implementation.
    """
    with TestClient(app) as test_client:
        # TODO: Add authentication headers when auth is implemented
        # test_client.headers.update({"Authorization": "Bearer test-token"})
        yield test_client 