"""Unit tests for OpenAI endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.mark.unit
def test_authentication_valid_key():
    """Test request with valid API key passes."""
    client = TestClient(app)

    with patch("src.openai.endpoints.run_agent") as mock_run_agent:
        # Mock agent response
        from src.agent.schemas import AgentResponse

        mock_run_agent.return_value = AgentResponse(
            response_text="Hello!",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            finish_reason="stop",
        )

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
            },
            headers={"Authorization": "Bearer dev-key-change-in-production"},
        )

        assert response.status_code == 200


@pytest.mark.unit
def test_authentication_missing_header():
    """Test request without Authorization header fails with 401."""
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


@pytest.mark.unit
def test_authentication_invalid_key():
    """Test request with invalid API key fails with 401."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": "Hello"}],
        },
        headers={"Authorization": "Bearer invalid-key"},
    )

    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]


@pytest.mark.unit
def test_authentication_malformed_header():
    """Test request with malformed Authorization header fails with 401."""
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


@pytest.mark.unit
def test_non_streaming_request():
    """Test non-streaming request with mocked agent service."""
    client = TestClient(app)

    with patch("src.openai.endpoints.run_agent") as mock_run_agent:
        from src.agent.schemas import AgentResponse

        mock_run_agent.return_value = AgentResponse(
            response_text="The answer is 42",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop",
        )

        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "What is the answer?"}],
                "stream": False,
            },
            headers={"Authorization": "Bearer dev-key-change-in-production"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "chat.completion"
        assert data["choices"][0]["message"]["content"] == "The answer is 42"


@pytest.mark.unit
def test_validation_error():
    """Test validation error handling (empty messages)."""
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "gpt-4o-mini",
            "messages": [],
            "stream": False,
        },
        headers={"Authorization": "Bearer dev-key-change-in-production"},
    )

    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "error" in data["detail"]
