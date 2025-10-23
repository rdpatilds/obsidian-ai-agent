"""Integration tests for API key authentication flows."""

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.mark.integration
def test_authentication_missing_header():
    """Test request without Authorization header fails."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]


@pytest.mark.integration
def test_authentication_invalid_key():
    """Test request with invalid API key fails."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        },
        headers={"Authorization": "Bearer invalid-key-123"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]


@pytest.mark.integration
def test_authentication_malformed_header():
    """Test request with malformed Authorization header fails."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        },
        headers={"Authorization": "InvalidFormat key"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]
