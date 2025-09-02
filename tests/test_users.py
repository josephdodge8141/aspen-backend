import pytest
import uuid
import hashlib
import json
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from app.database import engine
from app.models.users import User, ServiceUser
from app.models.team import Team, Member
from app.models.services import Service
from app.models.common import Environment


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


def hash_password(password: str) -> str:
    """Hash a password for testing"""
    return hashlib.sha256(password.encode()).hexdigest()


def hash_segment_key(segment_key: dict) -> bytes:
    """Create a canonical hash for segment key"""
    # Sort keys for consistent hashing
    canonical = json.dumps(segment_key, sort_keys=True)
    return hashlib.sha256(canonical.encode()).digest()


def test_create_internal_user(db_session):
    # Create a member first
    member = Member(
        first_name="John", last_name="Doe", email=f"john.doe.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()

    # Create internal user with password
    password_hash = hash_password("secure_password_123")
    user = User(member_id=member.id, password_hash=password_hash, service_user_id=None)
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.member_id == member.id
    assert user.password_hash == password_hash
    assert user.service_user_id is None


def test_create_service_user_and_external_user(db_session):
    # Create a service first
    api_key = "sk-test123456789abcdef"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create external user first (without service_user_id)
    user = User(member_id=None, password_hash=None, service_user_id=None)
    db_session.add(user)
    db_session.commit()

    # Create service user with unique segment key
    test_id = str(uuid.uuid4())
    segment_key = {
        "version": 1,
        "properties": {
            "user_id": f"abc123_{test_id}",
            "client_id": f"client_456_{test_id}",
        },
    }
    segment_hash = hash_segment_key(segment_key)

    service_user = ServiceUser(
        user_id=user.id,
        segment_key=segment_key,
        segment_hash=segment_hash,
        service_id=service.id,
        version=1,
    )
    db_session.add(service_user)
    db_session.commit()

    # Update user to link to service_user
    user.service_user_id = service_user.id
    db_session.commit()

    assert service_user.id is not None
    assert service_user.user_id == user.id
    assert service_user.segment_key == segment_key
    assert service_user.segment_hash == segment_hash
    assert service_user.service_id == service.id
    assert service_user.version == 1

    assert user.service_user_id == service_user.id
    assert user.member_id is None
    assert user.password_hash is None


def test_segment_key_json_storage(db_session):
    # Create a service first
    api_key = "sk-json123456789abcdef"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"JSON Test Service {uuid.uuid4()}",
        environment=Environment.stage,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create user
    user = User(member_id=None, password_hash=None, service_user_id=None)
    db_session.add(user)
    db_session.commit()

    # Create service user with complex JSON segment key
    test_id = str(uuid.uuid4())
    segment_key = {
        "version": 2,
        "properties": {
            "user_id": f"complex_user_789_{test_id}",
            "client_id": f"client_complex_{test_id}",
            "metadata": {
                "plan": "premium",
                "features": ["feature_a", "feature_b"],
                "settings": {"notifications": True, "theme": "dark"},
            },
        },
    }
    segment_hash = hash_segment_key(segment_key)

    service_user = ServiceUser(
        user_id=user.id,
        segment_key=segment_key,
        segment_hash=segment_hash,
        service_id=service.id,
        version=2,
    )
    db_session.add(service_user)
    db_session.commit()

    # Verify JSON was stored correctly
    retrieved_service_user = db_session.get(ServiceUser, service_user.id)
    assert retrieved_service_user.segment_key == segment_key
    assert (
        retrieved_service_user.segment_key["properties"]["metadata"]["plan"]
        == "premium"
    )
    assert retrieved_service_user.segment_key["properties"]["metadata"]["features"] == [
        "feature_a",
        "feature_b",
    ]


def test_unique_segment_hash_constraint(db_session):
    # Create a service first
    api_key = "sk-unique123456789abc"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"Unique Test Service {uuid.uuid4()}",
        environment=Environment.prod,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create two users
    user1 = User(member_id=None, password_hash=None, service_user_id=None)
    user2 = User(member_id=None, password_hash=None, service_user_id=None)
    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()

    # Create identical segment keys (should have same hash)
    test_id = str(uuid.uuid4())
    segment_key = {
        "version": 1,
        "properties": {
            "user_id": f"duplicate_test_{test_id}",
            "client_id": f"same_client_{test_id}",
        },
    }
    segment_hash = hash_segment_key(segment_key)

    # Create first service user
    service_user1 = ServiceUser(
        user_id=user1.id,
        segment_key=segment_key,
        segment_hash=segment_hash,
        service_id=service.id,
        version=1,
    )
    db_session.add(service_user1)
    db_session.commit()

    # Try to create second service user with same segment hash
    service_user2 = ServiceUser(
        user_id=user2.id,
        segment_key=segment_key,  # Same segment key
        segment_hash=segment_hash,  # Same hash
        service_id=service.id,
        version=1,
    )
    db_session.add(service_user2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_different_segment_keys_allowed(db_session):
    # Create a service first
    api_key = "sk-different123456789"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"Different Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create two users
    user1 = User(member_id=None, password_hash=None, service_user_id=None)
    user2 = User(member_id=None, password_hash=None, service_user_id=None)
    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()

    # Create different segment keys
    test_id1 = str(uuid.uuid4())
    test_id2 = str(uuid.uuid4())

    segment_key1 = {
        "version": 1,
        "properties": {
            "user_id": f"user_one_{test_id1}",
            "client_id": f"client_1_{test_id1}",
        },
    }
    segment_key2 = {
        "version": 1,
        "properties": {
            "user_id": f"user_two_{test_id2}",
            "client_id": f"client_2_{test_id2}",
        },
    }

    segment_hash1 = hash_segment_key(segment_key1)
    segment_hash2 = hash_segment_key(segment_key2)

    # Create both service users - should be allowed
    service_user1 = ServiceUser(
        user_id=user1.id,
        segment_key=segment_key1,
        segment_hash=segment_hash1,
        service_id=service.id,
        version=1,
    )
    service_user2 = ServiceUser(
        user_id=user2.id,
        segment_key=segment_key2,
        segment_hash=segment_hash2,
        service_id=service.id,
        version=1,
    )
    db_session.add(service_user1)
    db_session.add(service_user2)
    db_session.commit()  # Should not raise an exception

    assert service_user1.id != service_user2.id
    assert service_user1.segment_hash != service_user2.segment_hash


def test_foreign_key_integrity(db_session):
    # Create member, team, and service
    member = Member(
        first_name="FK", last_name="Test", email=f"fk.test.{uuid.uuid4()}@example.com"
    )
    db_session.add(member)
    db_session.commit()

    api_key = "sk-fk123456789abcdef"
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]

    service = Service(
        name=f"FK Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Test internal user with member FK
    internal_user = User(
        member_id=member.id,
        password_hash=hash_password("test123"),
        service_user_id=None,
    )
    db_session.add(internal_user)
    db_session.commit()

    # Test external user with service FK
    external_user = User(member_id=None, password_hash=None, service_user_id=None)
    db_session.add(external_user)
    db_session.commit()

    test_id = str(uuid.uuid4())
    segment_key = {
        "version": 1,
        "properties": {
            "user_id": f"fk_test_user_{test_id}",
            "client_id": f"fk_client_{test_id}",
        },
    }
    segment_hash = hash_segment_key(segment_key)

    service_user = ServiceUser(
        user_id=external_user.id,
        segment_key=segment_key,
        segment_hash=segment_hash,
        service_id=service.id,
        version=1,
    )
    db_session.add(service_user)
    db_session.commit()

    # Update external user to link to service user
    external_user.service_user_id = service_user.id
    db_session.commit()

    # Verify all relationships
    assert internal_user.member_id == member.id
    assert external_user.service_user_id == service_user.id
    assert service_user.user_id == external_user.id
    assert service_user.service_id == service.id
