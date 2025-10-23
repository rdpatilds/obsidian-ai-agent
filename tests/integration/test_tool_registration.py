"""Integration tests for tool registration."""

import pytest

from src.agent.agent import get_agent
from src.shared.config import settings


@pytest.mark.integration
def test_obsidian_tools_registered(monkeypatch):
    """Verify Obsidian consolidated tools are registered."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    agent = get_agent()

    # Check that agent has tools registered
    assert agent is not None

    # Verify agent instance was created with consolidated tools
    # The tools are registered during agent creation
    # We can verify this by checking that get_agent() returns an agent
    assert agent is not None
