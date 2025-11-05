"""Integration tests for agent test endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_chat_endpoint_exists(test_client: TestClient) -> None:
    """Test /agent/chat endpoint registered."""
    openapi = test_client.get("/openapi.json").json()
    assert "/agent/chat" in openapi["paths"]


@patch("app.agent.routes.vault_agent.run")
async def test_chat_success(mock_run: AsyncMock, test_client: TestClient) -> None:
    """Test successful chat interaction."""
    mock_result = MagicMock()
    mock_result.output = "I'm Paddy, an AI assistant."
    mock_usage = MagicMock()
    mock_usage.total_tokens = 45
    mock_usage.request_tokens = 20
    mock_usage.response_tokens = 25
    mock_result.usage.return_value = mock_usage
    mock_run.return_value = mock_result

    response = test_client.post("/agent/chat", json={"message": "Hello"})

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "usage" in data
    assert data["usage"]["total_tokens"] == 45


def test_chat_validation_error(test_client: TestClient) -> None:
    """Test empty message validation."""
    response = test_client.post("/agent/chat", json={"message": ""})
    assert response.status_code == 422


@patch("app.agent.routes.vault_agent.run")
async def test_chat_agent_error(mock_run: AsyncMock, test_client: TestClient) -> None:
    """Test agent error handling."""
    mock_run.side_effect = Exception("API error")
    response = test_client.post("/agent/chat", json={"message": "Hello"})
    assert response.status_code == 500
    assert "Agent execution failed" in response.json()["detail"]
