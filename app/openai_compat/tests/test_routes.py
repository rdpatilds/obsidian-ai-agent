"""Integration tests for OpenAI-compatible chat completions endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def test_chat_completions_endpoint_exists(test_client: TestClient) -> None:
    """Test /v1/chat/completions endpoint is registered."""
    openapi = test_client.get("/openapi.json").json()
    assert "/v1/chat/completions" in openapi["paths"]
    assert "post" in openapi["paths"]["/v1/chat/completions"]


@patch("app.openai_compat.routes.vault_agent.run")
def test_chat_completions_non_streaming(mock_run: AsyncMock, test_client: TestClient) -> None:
    """Test non-streaming chat completion request."""
    # Mock agent response
    mock_result = MagicMock()
    mock_result.output = "Hello! I'm Paddy, your Obsidian assistant."
    mock_usage = MagicMock()
    mock_usage.total_tokens = 50
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 40
    mock_result.usage.return_value = mock_usage
    mock_run.return_value = mock_result

    # Make request
    request_data = {
        "model": "claude-sonnet-4-0",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    response = test_client.post("/v1/chat/completions", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Verify OpenAI response format
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert "created" in data
    assert data["model"] == "claude-sonnet-4-0"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert "Paddy" in data["choices"][0]["message"]["content"]
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["usage"]["total_tokens"] == 50
    assert data["usage"]["prompt_tokens"] == 10
    assert data["usage"]["completion_tokens"] == 40


@pytest.mark.asyncio
@patch("app.openai_compat.routes.vault_agent.iter")
async def test_chat_completions_streaming(mock_iter: AsyncMock, test_client: TestClient) -> None:
    """Test streaming chat completion request."""
    # This test is complex - we'll mock the entire streaming flow
    # For now, just verify the endpoint accepts streaming requests
    request_data = {
        "model": "claude-sonnet-4-0",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True,
    }

    # Use stream=True in test client
    with test_client.stream("POST", "/v1/chat/completions", json=request_data) as response:
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_chat_completions_with_history(test_client: TestClient) -> None:
    """Test chat completion with message history."""
    with patch("app.openai_compat.routes.vault_agent.run") as mock_run:
        mock_result = MagicMock()
        mock_result.output = "Sure! Python is a programming language."
        mock_usage = MagicMock()
        mock_usage.total_tokens = 60
        mock_usage.input_tokens = 30
        mock_usage.output_tokens = 30
        mock_result.usage.return_value = mock_usage
        mock_run.return_value = mock_result

        request_data = {
            "model": "claude-sonnet-4-0",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "What is Python?"},
                {"role": "assistant", "content": "Python is a programming language."},
                {"role": "user", "content": "Tell me more"},
            ],
            "stream": False,
        }
        response = test_client.post("/v1/chat/completions", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["choices"][0]["message"]["content"]


def test_chat_completions_validation_error_empty_messages(test_client: TestClient) -> None:
    """Test validation error for empty messages list."""
    request_data: dict[str, str | bool | list[dict[str, str]]] = {
        "model": "claude-sonnet-4-0",
        "messages": [],
        "stream": False,
    }
    response = test_client.post("/v1/chat/completions", json=request_data)

    # Should return 422 validation error
    assert response.status_code == 422


def test_chat_completions_validation_error_missing_messages(test_client: TestClient) -> None:
    """Test validation error for missing messages field."""
    request_data = {
        "model": "claude-sonnet-4-0",
        "stream": False,
    }
    response = test_client.post("/v1/chat/completions", json=request_data)

    assert response.status_code == 422


def test_chat_completions_content_normalization(test_client: TestClient) -> None:
    """Test array content format is handled correctly."""
    with patch("app.openai_compat.routes.vault_agent.run") as mock_run:
        mock_result = MagicMock()
        mock_result.output = "I can see the text parts."
        mock_usage = MagicMock()
        mock_usage.total_tokens = 20
        mock_usage.input_tokens = 10
        mock_usage.output_tokens = 10
        mock_result.usage.return_value = mock_usage
        mock_run.return_value = mock_result

        request_data = {
            "model": "claude-sonnet-4-0",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hello"},
                        {"type": "text", "text": "World"},
                    ],
                }
            ],
            "stream": False,
        }
        response = test_client.post("/v1/chat/completions", json=request_data)

        assert response.status_code == 200
        # Verify the mock was called (content should be normalized)
        mock_run.assert_called_once()


def test_cors_headers_present(test_client: TestClient) -> None:
    """Test CORS headers are present in response."""
    with patch("app.openai_compat.routes.vault_agent.run") as mock_run:
        mock_result = MagicMock()
        mock_result.output = "Response"
        mock_usage = MagicMock()
        mock_usage.total_tokens = 10
        mock_usage.input_tokens = 5
        mock_usage.output_tokens = 5
        mock_result.usage.return_value = mock_usage
        mock_run.return_value = mock_result

        request_data = {
            "model": "claude-sonnet-4-0",
            "messages": [{"role": "user", "content": "Test"}],
            "stream": False,
        }

        # Make request with Origin header
        response = test_client.post(
            "/v1/chat/completions",
            json=request_data,
            headers={"Origin": "app://obsidian.md"},
        )

        assert response.status_code == 200
        # CORS credentials header should be present (TestClient doesn't trigger all CORS headers)
        assert "access-control-allow-credentials" in response.headers


@patch("app.openai_compat.routes.vault_agent.run")
def test_chat_completions_agent_error(mock_run: AsyncMock, test_client: TestClient) -> None:
    """Test error handling when agent execution fails."""
    mock_run.side_effect = Exception("Agent processing error")

    request_data = {
        "model": "claude-sonnet-4-0",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": False,
    }
    response = test_client.post("/v1/chat/completions", json=request_data)

    assert response.status_code == 500
    assert "Agent execution failed" in response.json()["detail"]


def test_chat_completions_optional_parameters(test_client: TestClient) -> None:
    """Test request with optional parameters."""
    with patch("app.openai_compat.routes.vault_agent.run") as mock_run:
        mock_result = MagicMock()
        mock_result.output = "Response"
        mock_usage = MagicMock()
        mock_usage.total_tokens = 10
        mock_usage.input_tokens = 5
        mock_usage.output_tokens = 5
        mock_result.usage.return_value = mock_usage
        mock_run.return_value = mock_result

        request_data = {
            "model": "claude-sonnet-4-0",
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.7,
            "max_tokens": 1000,
            "top_p": 0.9,
            "stream": False,
        }
        response = test_client.post("/v1/chat/completions", json=request_data)

        assert response.status_code == 200
