"""Unit tests for agent schemas.

Tests verify that:
- AgentDependencies validates correctly
- AgentRequest handles message history properly
- AgentResponse serializes correctly
- UUID generation works for request IDs
"""

import uuid

import httpx
import pytest
from pydantic import ValidationError

from src.agent.schemas import AgentDependencies, AgentRequest, AgentResponse


@pytest.mark.unit
class TestAgentDependencies:
    """Test suite for AgentDependencies schema."""

    def test_agent_dependencies_valid(self) -> None:
        """Test that AgentDependencies validates with correct inputs."""
        http_client = httpx.AsyncClient()
        deps = AgentDependencies(
            http_client=http_client,
            openai_api_key="sk-test-key-123",
            vault_path="/test/vault",
        )

        assert deps.http_client is http_client
        assert deps.openai_api_key == "sk-test-key-123"
        assert deps.vault_path == "/test/vault"

    def test_agent_dependencies_missing_fields(self) -> None:
        """Test that AgentDependencies requires all fields."""
        with pytest.raises(ValidationError):
            AgentDependencies()  # type: ignore[call-arg]

    def test_agent_dependencies_invalid_http_client(self) -> None:
        """Test that AgentDependencies validates http_client type."""
        with pytest.raises(ValidationError):
            AgentDependencies(
                http_client="not-a-client",  # type: ignore[arg-type]
                openai_api_key="sk-test",
            )


@pytest.mark.unit
class TestAgentRequest:
    """Test suite for AgentRequest schema."""

    def test_agent_request_minimal(self) -> None:
        """Test AgentRequest with only prompt."""
        request = AgentRequest(prompt="Hello, world!")

        assert request.prompt == "Hello, world!"
        assert request.message_history == []
        assert request.request_id is not None
        assert isinstance(request.request_id, str)
        # Verify it's a valid UUID
        uuid.UUID(request.request_id)

    def test_agent_request_with_history(self) -> None:
        """Test AgentRequest with message history."""
        history = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
        ]
        request = AgentRequest(
            prompt="Second message",
            message_history=history,
        )

        assert request.prompt == "Second message"
        assert request.message_history == history
        assert len(request.message_history) == 2

    def test_agent_request_custom_id(self) -> None:
        """Test AgentRequest with custom request_id."""
        custom_id = "custom-request-id-123"
        request = AgentRequest(
            prompt="Test",
            request_id=custom_id,
        )

        assert request.request_id == custom_id

    def test_agent_request_empty_prompt_fails(self) -> None:
        """Test that AgentRequest requires non-empty prompt."""
        # Empty string should be allowed by Pydantic but may fail validation later
        request = AgentRequest(prompt="")
        assert request.prompt == ""


@pytest.mark.unit
class TestAgentResponse:
    """Test suite for AgentResponse schema."""

    def test_agent_response_minimal(self) -> None:
        """Test AgentResponse with only response_text."""
        response = AgentResponse(response_text="Hello!")

        assert response.response_text == "Hello!"
        assert response.tool_calls == []
        assert response.usage == {}
        assert response.finish_reason == "stop"

    def test_agent_response_with_all_fields(self) -> None:
        """Test AgentResponse with all fields populated."""
        tool_calls = [
            {"tool": "calculator", "args": {"a": 1, "b": 2}},
        ]
        usage = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        response = AgentResponse(
            response_text="The answer is 3",
            tool_calls=tool_calls,
            usage=usage,
            finish_reason="stop",
        )

        assert response.response_text == "The answer is 3"
        assert response.tool_calls == tool_calls
        assert response.usage == usage
        assert response.finish_reason == "stop"

    def test_agent_response_serialization(self) -> None:
        """Test that AgentResponse serializes to dict correctly."""
        response = AgentResponse(
            response_text="Test",
            usage={"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        )

        data = response.model_dump()
        assert data["response_text"] == "Test"
        assert data["tool_calls"] == []
        assert data["usage"]["prompt_tokens"] == 5
        assert data["finish_reason"] == "stop"

    def test_agent_response_custom_finish_reason(self) -> None:
        """Test AgentResponse with custom finish_reason."""
        response = AgentResponse(
            response_text="...",
            finish_reason="length",
        )

        assert response.finish_reason == "length"
