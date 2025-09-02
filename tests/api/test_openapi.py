import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_openapi_json_accessible():
    """Test that OpenAPI schema is accessible"""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "openapi" in schema
    assert schema["info"]["title"] == "Aspen Backend"
    assert schema["info"]["description"] == "Multi-tenant AI workflow platform"


def test_openapi_security_schemes():
    """Test that security schemes are properly configured"""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    # Check that security schemes exist
    assert "components" in schema
    assert "securitySchemes" in schema["components"]

    security_schemes = schema["components"]["securitySchemes"]

    # Check JWT bearer scheme
    assert "HTTPBearer" in security_schemes
    jwt_scheme = security_schemes["HTTPBearer"]
    assert jwt_scheme["type"] == "http"
    assert jwt_scheme["scheme"] == "bearer"
    assert jwt_scheme["bearerFormat"] == "JWT"
    assert "JWT token for internal users" in jwt_scheme["description"]

    # Check API key scheme
    assert "APIKeyHeader" in security_schemes
    api_key_scheme = security_schemes["APIKeyHeader"]
    assert api_key_scheme["type"] == "apiKey"
    assert api_key_scheme["in"] == "header"
    assert api_key_scheme["name"] == "X-API-Key"
    assert "API key for external services" in api_key_scheme["description"]


def test_openapi_tags():
    """Test that OpenAPI tags are properly configured"""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    # Check that tags exist
    assert "tags" in schema
    tags = {tag["name"]: tag for tag in schema["tags"]}

    # Check expected tags
    expected_tags = ["Auth", "Experts", "Workflows", "Services"]
    for tag_name in expected_tags:
        assert tag_name in tags
        assert "description" in tags[tag_name]
        assert len(tags[tag_name]["description"]) > 0

    # Check specific tag descriptions
    assert "Authentication endpoints" in tags["Auth"]["description"]
    assert "AI expert management" in tags["Experts"]["description"]
    assert "Workflow orchestration" in tags["Workflows"]["description"]
    assert "External service integration" in tags["Services"]["description"]


def test_auth_endpoints_use_correct_tags():
    """Test that auth endpoints use the correct tags"""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    # Check that auth login endpoint has correct tag
    assert "paths" in schema
    assert "/api/v1/auth/login" in schema["paths"]
    login_endpoint = schema["paths"]["/api/v1/auth/login"]["post"]
    assert "tags" in login_endpoint
    assert "Auth" in login_endpoint["tags"]


def test_swagger_ui_accessible():
    """Test that Swagger UI is accessible"""
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_redoc_accessible():
    """Test that ReDoc is accessible"""
    client = TestClient(app)
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_login_endpoint_security():
    """Test that login endpoint doesn't require authentication"""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()

    # Login endpoint should not require security
    login_endpoint = schema["paths"]["/api/v1/auth/login"]["post"]
    # Security should either not be present or be an empty array
    security = login_endpoint.get("security", [])
    # Login endpoints typically don't require auth, so security should be empty or not present
    assert len(security) == 0 or "security" not in login_endpoint
