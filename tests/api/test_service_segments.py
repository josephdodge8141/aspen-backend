import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from app.models.services import Service, ServiceSegment
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

    # Create service
    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash="test_hash",
        api_key_last4="test",
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)

    return {"team": team, "user": user, "member": member, "service": service}


@pytest.fixture
def auth_headers(test_data):
    token = create_access_token(test_data["user"].id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client_with_db(db_session):
    """Create a test client with database session override"""
    from app.api.deps import get_db_session
    from app.main import app

    def get_test_db():
        return db_session

    app.dependency_overrides[get_db_session] = get_test_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up override
    app.dependency_overrides.clear()


class TestServiceSegments:
    def test_create_segment_success(self, client_with_db, test_data, auth_headers):
        """Test successful segment creation."""
        service_id = test_data["service"].id
        request_data = {"name": "Test Segment"}

        response = client_with_db.post(
            f"/api/v1/services/{service_id}/segments",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Test Segment"
        assert data["service_id"] == service_id
        assert "id" in data

    def test_create_segment_duplicate_name(
        self, client_with_db, test_data, auth_headers, db_session
    ):
        """Test that duplicate segment names within a service are rejected."""
        service_id = test_data["service"].id

        # Create first segment
        segment = ServiceSegment(service_id=service_id, name="Duplicate Segment")
        db_session.add(segment)
        db_session.commit()

        # Try to create duplicate
        request_data = {"name": "Duplicate Segment"}

        response = client_with_db.post(
            f"/api/v1/services/{service_id}/segments",
            json=request_data,
            headers=auth_headers,
        )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_segment_service_not_found(
        self, client_with_db, test_data, auth_headers
    ):
        """Test creating segment for non-existent service."""
        request_data = {"name": "Test Segment"}

        response = client_with_db.post(
            "/api/v1/services/99999/segments", json=request_data, headers=auth_headers
        )

        assert response.status_code == 404
        assert "Service not found" in response.json()["detail"]

    def test_list_segments(self, client_with_db, test_data, auth_headers, db_session):
        """Test listing segments for a service."""
        service_id = test_data["service"].id

        # Create test segments
        segment1 = ServiceSegment(service_id=service_id, name="Segment 1")
        segment2 = ServiceSegment(service_id=service_id, name="Segment 2")
        db_session.add_all([segment1, segment2])
        db_session.commit()

        response = client_with_db.get(
            f"/api/v1/services/{service_id}/segments", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        segment_names = {segment["name"] for segment in data}
        assert segment_names == {"Segment 1", "Segment 2"}

    def test_list_segments_service_not_found(
        self, client_with_db, test_data, auth_headers
    ):
        """Test listing segments for non-existent service."""
        response = client_with_db.get(
            "/api/v1/services/99999/segments", headers=auth_headers
        )
        assert response.status_code == 404

    def test_delete_segment_success(
        self, client_with_db, test_data, auth_headers, db_session
    ):
        """Test successful segment deletion."""
        service_id = test_data["service"].id

        segment = ServiceSegment(service_id=service_id, name="Test Segment")
        db_session.add(segment)
        db_session.commit()
        db_session.refresh(segment)

        response = client_with_db.delete(
            f"/api/v1/services/{service_id}/segments/{segment.id}", headers=auth_headers
        )

        assert response.status_code == 204

        # Verify segment is deleted
        deleted_segment = db_session.get(ServiceSegment, segment.id)
        assert deleted_segment is None

    def test_delete_segment_not_found(self, client_with_db, test_data, auth_headers):
        """Test deleting non-existent segment."""
        service_id = test_data["service"].id

        response = client_with_db.delete(
            f"/api/v1/services/{service_id}/segments/99999", headers=auth_headers
        )

        assert response.status_code == 404
        assert "Segment not found" in response.json()["detail"]

    def test_delete_segment_wrong_service(
        self, client_with_db, test_data, auth_headers, db_session
    ):
        """Test deleting segment with wrong service ID."""
        service_id = test_data["service"].id

        # Create another service
        other_service = Service(
            name="Other Service",
            environment=Environment.dev,
            api_key_hash="other_hash",
            api_key_last4="othr",
        )
        db_session.add(other_service)
        db_session.commit()
        db_session.refresh(other_service)

        # Create segment in other service
        segment = ServiceSegment(service_id=other_service.id, name="Other Segment")
        db_session.add(segment)
        db_session.commit()
        db_session.refresh(segment)

        # Try to delete using wrong service ID
        response = client_with_db.delete(
            f"/api/v1/services/{service_id}/segments/{segment.id}", headers=auth_headers
        )

        assert response.status_code == 404
        assert "Segment not found" in response.json()["detail"]

    def test_segments_allow_same_name_different_services(
        self, client_with_db, test_data, auth_headers, db_session
    ):
        """Test that segments with same name are allowed in different services."""
        service1_id = test_data["service"].id

        # Create another service
        service2 = Service(
            name="Second Service",
            environment=Environment.dev,
            api_key_hash="hash2",
            api_key_last4="svc2",
        )
        db_session.add(service2)
        db_session.commit()
        db_session.refresh(service2)

        # Create segment in first service
        request_data = {"name": "Common Segment"}
        response1 = client.post(
            f"/api/v1/services/{service1_id}/segments",
            json=request_data,
            headers=auth_headers,
        )
        assert response1.status_code == 200

        # Create segment with same name in second service (should succeed)
        response2 = client.post(
            f"/api/v1/services/{service2.id}/segments",
            json=request_data,
            headers=auth_headers,
        )
        assert response2.status_code == 200

    def test_unauthorized_access(self, client_with_db):
        """Test that segment endpoints require authentication."""
        # Test create
        response = client_with_db.post(
            "/api/v1/services/1/segments", json={"name": "Test"}
        )
        assert response.status_code == 401

        # Test list
        response = client_with_db.get("/api/v1/services/1/segments")
        assert response.status_code == 401

        # Test delete
        response = client_with_db.delete("/api/v1/services/1/segments/1")
        assert response.status_code == 401
