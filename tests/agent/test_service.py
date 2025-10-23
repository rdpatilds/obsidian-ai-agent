"""Unit tests for agent service layer."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.agent.schemas import AgentDependencies, AgentRequest, AgentResponse
from src.agent.service import run_agent, stream_agent


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_agent_success(monkeypatch):
    """Test run_agent with successful agent execution."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create mock usage stats
    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 20
    mock_usage.total_tokens = 30

    # Create mock result
    mock_result = MagicMock()
    mock_result.output = "Test response"
    mock_result.usage.return_value = mock_usage

    # Mock agent.run
    with patch("src.agent.service.get_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_get_agent.return_value = mock_agent

        request = AgentRequest(prompt="Test prompt")
        deps = AgentDependencies(
            http_client=httpx.AsyncClient(), openai_api_key="test-key", vault_path="/test/vault"
        )

        response = await run_agent(request, deps)

        assert isinstance(response, AgentResponse)
        assert response.response_text == "Test response"
        assert response.usage["total_tokens"] == 30
        assert response.finish_reason == "stop"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_agent_failure(monkeypatch):
    """Test run_agent with agent execution failure."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Mock agent.run to raise exception
    with patch("src.agent.service.get_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Agent failed"))
        mock_get_agent.return_value = mock_agent

        request = AgentRequest(prompt="Test prompt")
        deps = AgentDependencies(
            http_client=httpx.AsyncClient(), openai_api_key="test-key", vault_path="/test/vault"
        )

        with pytest.raises(RuntimeError, match="Agent failed"):
            await run_agent(request, deps)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stream_agent_success(monkeypatch):
    """Test stream_agent yields chunks correctly."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    # Create mock streaming events
    from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPartDelta

    mock_text_part = MagicMock()
    mock_text_part.part_kind = "text"
    mock_text_part.content = "Initial"

    mock_start_event = PartStartEvent(part=mock_text_part, index=0)
    mock_delta_event = PartDeltaEvent(delta=TextPartDelta(content_delta=" chunk"), index=0)

    # Create async iterator for streaming events
    async def async_iter_events():
        yield mock_start_event
        yield mock_delta_event

    # Mock the streaming context
    mock_request_stream = MagicMock()
    mock_request_stream.__aenter__ = AsyncMock(return_value=mock_request_stream)
    mock_request_stream.__aexit__ = AsyncMock(return_value=None)
    mock_request_stream.__aiter__ = lambda self: async_iter_events()

    mock_node = MagicMock()
    mock_node.stream = MagicMock(return_value=mock_request_stream)

    # Create async iterator for the run
    async def async_iter_nodes():
        yield mock_node

    mock_run = MagicMock()
    mock_run.ctx = MagicMock()
    mock_run.__aenter__ = AsyncMock(return_value=mock_run)
    mock_run.__aexit__ = AsyncMock(return_value=None)
    mock_run.__aiter__ = lambda self: async_iter_nodes()

    with patch("src.agent.service.get_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.iter = MagicMock(return_value=mock_run)
        mock_agent.is_model_request_node = MagicMock(return_value=True)
        mock_get_agent.return_value = mock_agent

        # Patch Agent.is_model_request_node at the class level
        with patch("src.agent.service.Agent.is_model_request_node", return_value=True):
            request = AgentRequest(prompt="Test prompt")
            deps = AgentDependencies(
                http_client=httpx.AsyncClient(), openai_api_key="test-key", vault_path="/test/vault"
            )

            chunks = []
            async for chunk in stream_agent(request, deps):
                chunks.append(chunk)

            assert len(chunks) == 2
            assert chunks[0] == "Initial"
            assert chunks[1] == " chunk"
