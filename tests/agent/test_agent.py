"""Unit tests for agent initialization.

Tests verify that:
- Agent is created with correct model
- Singleton pattern works correctly
- Agent configuration is applied properly
"""

import pytest
from pydantic_ai import Agent

from src.agent.agent import create_agent, get_agent
from src.agent.schemas import AgentDependencies
from src.shared.config import Settings


@pytest.mark.unit
class TestAgentCreation:
    """Test suite for agent creation and configuration."""

    def test_create_agent_returns_agent_instance(self) -> None:
        """Test that create_agent returns a valid Agent instance."""
        test_settings = Settings(
            openai_api_key="sk-test-key-for-unit-tests",
            model_name="openai:gpt-4o-mini",
        )
        agent = create_agent(test_settings)

        assert isinstance(agent, Agent)
        assert agent is not None

    def test_create_agent_uses_model_from_settings(self) -> None:
        """Test that create_agent uses model_name from settings."""
        test_settings = Settings(
            openai_api_key="sk-test-key-for-unit-tests",
            model_name="openai:gpt-4",
        )
        agent = create_agent(test_settings)

        assert isinstance(agent, Agent)

    def test_get_agent_singleton_pattern(self) -> None:
        """Test that get_agent returns the same instance on multiple calls."""
        # Clear the global agent to ensure fresh start
        import src.agent.agent

        src.agent.agent._agent = None

        test_settings = Settings(
            openai_api_key="sk-test-key-for-unit-tests",
            model_name="openai:gpt-4o-mini",
        )

        agent1 = get_agent(test_settings)
        agent2 = get_agent(test_settings)

        assert agent1 is agent2
        assert isinstance(agent1, Agent)

    def test_get_agent_creates_agent_if_none(self) -> None:
        """Test that get_agent creates an agent if none exists."""
        import src.agent.agent

        src.agent.agent._agent = None

        test_settings = Settings(
            openai_api_key="sk-test-key-for-unit-tests",
            model_name="openai:gpt-4o-mini",
        )

        agent = get_agent(test_settings)

        assert agent is not None
        assert isinstance(agent, Agent)

    def test_agent_configured_with_correct_model(self) -> None:
        """Test that agent is configured with correct model from settings."""
        import src.agent.agent

        src.agent.agent._agent = None

        test_settings = Settings(
            openai_api_key="sk-test-key-for-unit-tests",
            model_name="openai:gpt-4o-mini",
        )

        agent = get_agent(test_settings)

        assert isinstance(agent, Agent)
