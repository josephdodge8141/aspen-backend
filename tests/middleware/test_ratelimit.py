import pytest
import time
import uuid
import os
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.services import Service
from app.models.common import Environment
from app.security.apikeys import generate_api_key
from app.middleware.ratelimit import RateLimitMiddleware
from app.api.deps import get_db_session, get_caller


@pytest.fixture
def rate_limit_app(db_session: Session):
    """Create test app with rate limiting enabled and low threshold"""
    test_app = FastAPI()
    
    # Add rate limiting with very low threshold for testing
    test_app.add_middleware(RateLimitMiddleware, requests_per_minute=3)
    
    # Override database dependency
    def get_test_db():
        return db_session
    
    test_app.dependency_overrides[get_db_session] = get_test_db
    
    # Add test endpoint
    from fastapi import Depends
    from app.api.deps import CallerContext
    
    @test_app.get("/test-rate-limit")
    async def test_endpoint(caller: CallerContext = Depends(get_caller)):
        if caller.service:
            return {"service_id": caller.service.id}
        return {"user_id": caller.user.id}
    
    return test_app


def test_rate_limit_within_threshold(db_session: Session, rate_limit_app: FastAPI):
    """Test that requests within rate limit succeed"""
    # Create service with API key
    plaintext_key, api_key_hash, last4 = generate_api_key()
    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=last4
    )
    db_session.add(service)
    db_session.commit()
    db_session.refresh(service)
    
    client = TestClient(rate_limit_app)
    
    # Make requests within threshold (3 per minute)
    for i in range(3):
        response = client.get("/test-rate-limit", headers={"X-API-Key": plaintext_key})
        assert response.status_code == 200
        assert response.json()["service_id"] == service.id


def test_rate_limit_exceeded(db_session: Session, rate_limit_app: FastAPI):
    """Test that requests exceeding rate limit return 429"""
    # Create service with API key
    plaintext_key, api_key_hash, last4 = generate_api_key()
    service = Service(
        name=f"Test Service {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=api_key_hash,
        api_key_last4=last4
    )
    db_session.add(service)
    db_session.commit()
    
    client = TestClient(rate_limit_app)
    
    # Make requests up to threshold
    for i in range(3):
        response = client.get("/test-rate-limit", headers={"X-API-Key": plaintext_key})
        assert response.status_code == 200
    
    # Next request should be rate limited
    response = client.get("/test-rate-limit", headers={"X-API-Key": plaintext_key})
    assert response.status_code == 429
    assert response.headers.get("Content-Type") == "application/problem+json"
    assert response.json()["detail"] == "Rate limit exceeded"


def test_rate_limit_different_api_keys(db_session: Session, rate_limit_app: FastAPI):
    """Test that different API keys have separate rate limits"""
    # Create two services with different API keys
    key1, hash1, last4_1 = generate_api_key()
    service1 = Service(
        name=f"Service 1 {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=hash1,
        api_key_last4=last4_1
    )
    
    key2, hash2, last4_2 = generate_api_key()
    service2 = Service(
        name=f"Service 2 {uuid.uuid4()}",
        environment=Environment.dev,
        api_key_hash=hash2,
        api_key_last4=last4_2
    )
    
    db_session.add(service1)
    db_session.add(service2)
    db_session.commit()
    
    client = TestClient(rate_limit_app)
    
    # Use up quota for key1
    for i in range(3):
        response = client.get("/test-rate-limit", headers={"X-API-Key": key1})
        assert response.status_code == 200
    
    # key1 should be rate limited
    response = client.get("/test-rate-limit", headers={"X-API-Key": key1})
    assert response.status_code == 429
    
    # key2 should still work
    response = client.get("/test-rate-limit", headers={"X-API-Key": key2})
    assert response.status_code == 200


def test_rate_limit_skips_jwt_requests():
    """Test that JWT requests are not rate limited"""
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, requests_per_minute=1)  # Very restrictive
    
    @test_app.get("/test-jwt")
    async def test_endpoint():
        return {"message": "JWT request"}
    
    client = TestClient(test_app)
    
    # Make multiple JWT requests - should not be rate limited
    for i in range(5):
        response = client.get("/test-jwt", headers={"Authorization": "Bearer fake-token"})
        # Will get 422 for missing dependency, but not 429 for rate limit
        assert response.status_code != 429


def test_rate_limit_no_api_key():
    """Test that requests without API key are not rate limited"""
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, requests_per_minute=1)  # Very restrictive
    
    @test_app.get("/test-no-auth")
    async def test_endpoint():
        return {"message": "No auth request"}
    
    client = TestClient(test_app)
    
    # Make multiple requests without any auth - should not be rate limited
    for i in range(5):
        response = client.get("/test-no-auth")
        assert response.status_code == 200


def test_token_bucket_refill():
    """Test that token bucket refills over time"""
    from app.middleware.ratelimit import TokenBucket
    
    # Create bucket with 2 tokens, refill at 1 token per second
    bucket = TokenBucket(capacity=2, refill_rate=1.0)
    
    # Consume all tokens
    assert bucket.consume() is True
    assert bucket.consume() is True
    assert bucket.consume() is False  # Should be empty
    
    # Wait a bit and verify refill (using small sleep for test safety)
    time.sleep(0.1)  # Small sleep
    # Manually advance the time to simulate refill for test reliability
    bucket.last_refill -= 1.1  # Simulate 1.1 seconds ago
    
    # Should have refilled at least 1 token
    assert bucket.consume() is True


def test_rate_limit_disabled_by_default():
    """Test that rate limiting is disabled by default in tests"""
    # Ensure ENABLE_RATELIMIT is not set
    old_value = os.environ.get("ENABLE_RATELIMIT")
    if "ENABLE_RATELIMIT" in os.environ:
        del os.environ["ENABLE_RATELIMIT"]
    
    try:
        # Import fresh app instance
        from app.main import app
        
        # Check that rate limit middleware is not registered
        middleware_types = [type(middleware) for middleware in app.user_middleware]
        from app.middleware.ratelimit import RateLimitMiddleware
        assert RateLimitMiddleware not in middleware_types
    
    finally:
        # Restore original value
        if old_value is not None:
            os.environ["ENABLE_RATELIMIT"] = old_value 