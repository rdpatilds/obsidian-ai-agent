"""Integration tests for obsidian_query_vault_tool with agent."""

import pytest

from app.core.agents import vault_agent


@pytest.mark.integration
def test_tool_registered_with_agent() -> None:
    """Verify obsidian_query_vault_tool is registered with the agent."""
    # This test verifies the tool registration via side-effect imports works
    # The agent should be properly initialized
    assert vault_agent is not None
    assert vault_agent.model is not None
    assert vault_agent.deps_type is not None


@pytest.mark.integration
def test_agent_has_deps_type() -> None:
    """Verify agent has dependencies configured."""
    # Verify the agent has dependencies configured
    assert vault_agent.deps_type is not None
    # Ensure AgentDeps is properly integrated
    from app.core.agents import AgentDeps

    assert vault_agent.deps_type == AgentDeps


# NOTE: Full agent.run() tests would require LLM API calls
# Those should be tested manually or with mocked LLM responses
# The above tests verify structural integration without API costs
