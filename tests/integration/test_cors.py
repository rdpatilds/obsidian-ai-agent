"""Integration tests for CORS functionality."""

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.shared.config import Settings, get_settings


def override_get_settings(**overrides: bool | str) -> Settings:
    """Override settings for testing.

    Args:
        **overrides: Key-value pairs to override in settings.

    Returns:
        Settings instance with overrides applied.
    """
    current_settings = get_settings()
    return Settings(**{**current_settings.model_dump(), **overrides})


@pytest.mark.integration
def test_cors_headers_present_on_chat_endpoint() -> None:
    """Test CORS headers present in /v1/chat/completions response."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        },
        headers={
            "Authorization": "Bearer dev-key-change-in-production",
            "Origin": "app://obsidian.md",
        },
    )

    # Should have CORS headers
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-credentials" in response.headers


@pytest.mark.integration
def test_cors_headers_present_on_health_endpoint() -> None:
    """Test CORS headers present in /health response."""
    client = TestClient(app)

    response = client.get(
        "/health",
        headers={"Origin": "app://obsidian.md"},
    )

    # Should have CORS headers
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-credentials" in response.headers


@pytest.mark.integration
def test_cors_preflight_request() -> None:
    """Test OPTIONS preflight request returns correct CORS headers."""
    client = TestClient(app)

    response = client.options(
        "/v1/chat/completions",
        headers={
            "Origin": "app://obsidian.md",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )

    # Preflight should succeed
    assert response.status_code == 200
    # Should have CORS headers
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers
    assert "access-control-allow-credentials" in response.headers


@pytest.mark.integration
def test_cors_with_valid_origin() -> None:
    """Test request with app://obsidian.md origin succeeds."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Test"}],
            "stream": False,
        },
        headers={
            "Authorization": "Bearer dev-key-change-in-production",
            "Origin": "app://obsidian.md",
        },
    )

    # Request should succeed
    assert response.status_code == 200
    # Should have CORS headers with correct origin
    assert response.headers.get("access-control-allow-origin") in [
        "app://obsidian.md",
        "*",
    ]


@pytest.mark.integration
def test_cors_with_authentication() -> None:
    """Test CORS works with Bearer token authentication."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Calculate 2+2"}],
            "stream": False,
        },
        headers={
            "Authorization": "Bearer dev-key-change-in-production",
            "Origin": "http://localhost",
        },
    )

    # Should succeed with valid authentication and CORS
    assert response.status_code == 200
    # Should have CORS headers
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-credentials" in response.headers
    # Response should be valid OpenAI format
    data = response.json()
    assert "choices" in data
    assert "id" in data
    assert "model" in data


@pytest.mark.integration
def test_cors_allows_required_methods() -> None:
    """Test GET, POST, OPTIONS methods are allowed."""
    client = TestClient(app)

    # Test OPTIONS
    response = client.options(
        "/v1/chat/completions",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    allow_methods = response.headers.get("access-control-allow-methods", "")
    assert "POST" in allow_methods
    assert "GET" in allow_methods
    assert "OPTIONS" in allow_methods


@pytest.mark.integration
def test_cors_allows_required_headers() -> None:
    """Test Authorization and Content-Type headers are allowed."""
    client = TestClient(app)

    response = client.options(
        "/v1/chat/completions",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )

    assert response.status_code == 200
    allow_headers = response.headers.get("access-control-allow-headers", "")
    assert "authorization" in allow_headers.lower()
    assert "content-type" in allow_headers.lower()


@pytest.mark.integration
def test_cors_credentials_allowed() -> None:
    """Test Access-Control-Allow-Credentials: true is present."""
    client = TestClient(app)

    response = client.get(
        "/health",
        headers={"Origin": "http://localhost"},
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-credentials") == "true"
