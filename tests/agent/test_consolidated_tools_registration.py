"""Tests for consolidated tools registration."""

import pytest

from src.agent.agent import create_agent
from src.shared.config import Settings


@pytest.mark.unit
def test_agent_creation_with_consolidated_tools() -> None:
    """Test that agent can be created with consolidated tools enabled."""
    settings = Settings(
        model_name="openai:gpt-4o-mini",
        openai_api_key="test-key",
        obsidian_vault_path="/tmp/test_vault",
        enable_obsidian_note_manager=True,
        enable_obsidian_vault_query=True,
        enable_obsidian_graph_analyzer=True,
    )

    agent = create_agent(settings)

    assert agent is not None
    # Verify system prompt includes new tools
    prompt = settings.agent_system_prompt
    assert "obsidian_note_manage" in prompt
    assert "obsidian_vault_query" in prompt
    assert "obsidian_graph_analyze" in prompt


@pytest.mark.unit
def test_agent_creation_minimal_config() -> None:
    """Test that agent can be created with minimal configuration."""
    settings = Settings(
        model_name="openai:gpt-4o-mini",
        openai_api_key="test-key",
        obsidian_vault_path="/tmp/test_vault",
        enable_obsidian_note_manager=True,
        enable_obsidian_vault_query=True,
        enable_obsidian_graph_analyzer=True,
    )

    agent = create_agent(settings)

    # Agent should be created successfully
    assert agent is not None


@pytest.mark.unit
def test_consolidated_tools_system_prompt() -> None:
    """Test that system prompt includes consolidated tool descriptions."""
    settings = Settings(
        model_name="openai:gpt-4o-mini",
        openai_api_key="test-key",
        enable_obsidian_note_manager=True,
        enable_obsidian_vault_query=True,
        enable_obsidian_graph_analyzer=True,
    )

    agent = create_agent(settings)

    prompt = settings.agent_system_prompt
    assert "obsidian_note_manage" in prompt
    assert "obsidian_vault_query" in prompt
    assert "obsidian_graph_analyze" in prompt
    assert "Token Efficiency" in prompt
    assert "minimal" in prompt and "concise" in prompt and "detailed" in prompt
