import pytest
import uuid
import hashlib
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from app.database import engine
from app.models.services import Service, ServiceSegment
from app.models.common import Environment


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


def hash_api_key(api_key: str) -> tuple[str, str]:
    """Hash an API key and return (hash, last4)"""
    api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    api_key_last4 = api_key[-4:]
    return api_key_hash, api_key_last4


def test_create_service(db_session):
    api_key = "sk-test123456789abcdef"
    api_key_hash, api_key_last4 = hash_api_key(api_key)

    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    assert service.id is not None
    assert service.name.startswith("Test Service")
    assert service.environment == Environment.dev
    assert service.api_key_hash == api_key_hash
    assert service.api_key_last4 == "cdef"
    # Ensure we're not storing the plaintext API key
    assert api_key not in str(service.__dict__.values())


def test_service_different_environments(db_session):
    api_key = "sk-prod987654321fedcba"
    api_key_hash, api_key_last4 = hash_api_key(api_key)

    # Test all environments
    environments = [Environment.dev, Environment.stage, Environment.prod]
    service_name = f"Service {uuid.uuid4()}"

    for env in environments:
        service = Service(
            name=f"{service_name} {env.value}",
            environment=env,
            api_key_hash=api_key_hash,
            api_key_last4=api_key_last4,
        )
        db_session.add(service)

    db_session.commit()

    # Verify all services were created
    services = db_session.exec(
        select(Service).where(Service.name.like(f"{service_name}%"))
    ).all()
    created_envs = [service.environment for service in services]
    for env in environments:
        assert env in created_envs


def test_unique_service_name_env_constraint(db_session):
    api_key1 = "sk-test111111111111111"
    api_key_hash1, api_key_last4_1 = hash_api_key(api_key1)

    api_key2 = "sk-test222222222222222"
    api_key_hash2, api_key_last4_2 = hash_api_key(api_key2)

    service_name = f"Duplicate Name Service {uuid.uuid4()}"

    # Create first service
    service1 = Service(
        name=service_name,
        environment=Environment.dev,
        api_key_hash=api_key_hash1,
        api_key_last4=api_key_last4_1,
    )
    db_session.add(service1)
    db_session.commit()

    # Try to create service with same name and environment
    service2 = Service(
        name=service_name,
        environment=Environment.dev,  # Same environment
        api_key_hash=api_key_hash2,
        api_key_last4=api_key_last4_2,
    )
    db_session.add(service2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_name_different_env_allowed(db_session):
    api_key1 = "sk-test333333333333333"
    api_key_hash1, api_key_last4_1 = hash_api_key(api_key1)

    api_key2 = "sk-test444444444444444"
    api_key_hash2, api_key_last4_2 = hash_api_key(api_key2)

    service_name = f"Same Name Service {uuid.uuid4()}"

    # Create service in dev
    service1 = Service(
        name=service_name,
        environment=Environment.dev,
        api_key_hash=api_key_hash1,
        api_key_last4=api_key_last4_1,
    )
    db_session.add(service1)
    db_session.commit()

    # Create service with same name but different environment - should be allowed
    service2 = Service(
        name=service_name,
        environment=Environment.prod,  # Different environment
        api_key_hash=api_key_hash2,
        api_key_last4=api_key_last4_2,
    )
    db_session.add(service2)
    db_session.commit()  # Should not raise an exception

    assert service1.id != service2.id
    assert service1.environment != service2.environment


def test_create_service_segment(db_session):
    # Create a service first
    api_key = "sk-segment123456789abc"
    api_key_hash, api_key_last4 = hash_api_key(api_key)

    service = Service(
        name=f"Segment Test Service {uuid.uuid4()}",
        environment=Environment.stage,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create service segment
    segment = ServiceSegment(service_id=service.id, name="user_segment")
    db_session.add(segment)
    db_session.commit()

    assert segment.id is not None
    assert segment.service_id == service.id
    assert segment.name == "user_segment"


def test_unique_service_segment_name_constraint(db_session):
    # Create a service first
    api_key = "sk-unique555555555555555"
    api_key_hash, api_key_last4 = hash_api_key(api_key)

    service = Service(
        name=f"Unique Segment Service {uuid.uuid4()}",
        environment=Environment.prod,
        api_key_hash=api_key_hash,
        api_key_last4=api_key_last4,
    )
    db_session.add(service)
    db_session.commit()

    # Create first segment
    segment1 = ServiceSegment(service_id=service.id, name="duplicate_segment")
    db_session.add(segment1)
    db_session.commit()

    # Try to create segment with same name for same service
    segment2 = ServiceSegment(
        service_id=service.id, name="duplicate_segment"  # Same name
    )
    db_session.add(segment2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_same_segment_name_different_service_allowed(db_session):
    # Create two services
    api_key1 = "sk-service1666666666666"
    api_key_hash1, api_key_last4_1 = hash_api_key(api_key1)

    api_key2 = "sk-service2777777777777"
    api_key_hash2, api_key_last4_2 = hash_api_key(api_key2)

    service1 = Service(
        name=f"Service 1 {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash1,
        api_key_last4=api_key_last4_1,
    )
    service2 = Service(
        name=f"Service 2 {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash2,
        api_key_last4=api_key_last4_2,
    )
    db_session.add(service1)
    db_session.add(service2)
    db_session.commit()

    # Create segments with same name for different services - should be allowed
    segment1 = ServiceSegment(service_id=service1.id, name="common_segment")
    segment2 = ServiceSegment(
        service_id=service2.id, name="common_segment"  # Same name, different service
    )
    db_session.add(segment1)
    db_session.add(segment2)
    db_session.commit()  # Should not raise an exception

    assert segment1.id != segment2.id
    assert segment1.service_id != segment2.service_id
