"""Unit tests for Obsidian Vault Organizer tool registration."""

import pytest
from pydantic_ai import Agent

from src.agent.schemas import AgentDependencies
from src.tools.obsidian_vault_organizer.tool import register_obsidian_vault_organizer_tool


@pytest.mark.unit
def test_tool_registration() -> None:
    """Test that the vault organizer tool can be registered."""
    agent: Agent[AgentDependencies, str] = Agent(
        "openai:gpt-4o-mini",
        deps_type=AgentDependencies,
    )

    # Should not raise an exception
    register_obsidian_vault_organizer_tool(agent)

    # Tool registration successful if no exception raised
    assert True
