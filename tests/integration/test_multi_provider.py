"""Integration tests for multi-provider support.

Tests verify that:
- Agents can be created with different provider configurations
- Provider selection works based on model name prefix
- Appropriate error messages are raised when API keys are missing
- Multiple providers can coexist in configuration
"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.exceptions import UserError

from src.agent.agent import create_agent
from src.shared.config import Settings


@pytest.mark.integration
class TestMultiProviderAgentCreation:
    """Test suite for multi-provider agent creation."""

    def test_agent_creation_with_anthropic_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that agent can be created with anthropic: model prefix.

        Args:
            monkeypatch: Pytest monkeypatch fixture for env var manipulation.
        """
        # Set up environment with Anthropic API key
        test_key = "sk-ant-test-key-12345"
        monkeypatch.setenv("ANTHROPIC_API_KEY", test_key)

        # Create settings with anthropic model
        settings = Settings(
            model_name="anthropic:claude-3-5-sonnet-latest",
            anthropic_api_key=test_key,
        )

        # Mock the Agent class to avoid actual API calls
        with patch("src.agent.agent.Agent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance

            agent = create_agent(settings)

            # Verify Agent was called with correct model
            mock_agent.assert_called_once()
            call_kwargs = mock_agent.call_args.kwargs
            assert call_kwargs["model"] == "anthropic:claude-3-5-sonnet-latest"
            assert agent == mock_instance

    def test_agent_creation_with_openrouter_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that agent can be created with openrouter: model prefix.

        Args:
            monkeypatch: Pytest monkeypatch fixture for env var manipulation.
        """
        # Set up environment with OpenRouter API key
        test_key = "sk-or-test-key-12345"
        monkeypatch.setenv("OPENROUTER_API_KEY", test_key)

        # Create settings with openrouter model
        settings = Settings(
            model_name="openrouter:anthropic/claude-3.5-sonnet",
            openrouter_api_key=test_key,
        )

        # Mock the Agent class to avoid actual API calls
        with patch("src.agent.agent.Agent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance

            agent = create_agent(settings)

            # Verify Agent was called with correct model
            mock_agent.assert_called_once()
            call_kwargs = mock_agent.call_args.kwargs
            assert call_kwargs["model"] == "openrouter:anthropic/claude-3.5-sonnet"
            assert agent == mock_instance

    def test_agent_creation_with_openai_provider(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that agent can be created with openai: model prefix.

        Args:
            monkeypatch: Pytest monkeypatch fixture for env var manipulation.
        """
        # Set up environment with OpenAI API key
        test_key = "sk-test-key-12345"
        monkeypatch.setenv("OPENAI_API_KEY", test_key)

        # Create settings with openai model
        settings = Settings(
            model_name="openai:gpt-4o-mini",
            openai_api_key=test_key,
        )

        # Mock the Agent class to avoid actual API calls
        with patch("src.agent.agent.Agent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance

            agent = create_agent(settings)

            # Verify Agent was called with correct model
            mock_agent.assert_called_once()
            call_kwargs = mock_agent.call_args.kwargs
            assert call_kwargs["model"] == "openai:gpt-4o-mini"
            assert agent == mock_instance

    def test_provider_error_without_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that helpful error is raised when provider API key is missing.

        Args:
            monkeypatch: Pytest monkeypatch fixture for env var manipulation.
        """
        # Clear all provider API keys
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create settings with anthropic model but no API key
        settings = Settings(
            model_name="anthropic:claude-3-5-sonnet-latest",
            anthropic_api_key="",  # Empty key
        )

        # Attempt to create agent should raise UserError
        with pytest.raises(UserError, match="ANTHROPIC_API_KEY"):
            create_agent(settings)

    def test_multiple_providers_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that all three providers can coexist in configuration.

        Args:
            monkeypatch: Pytest monkeypatch fixture for env var manipulation.
        """
        # Set up environment with all three API keys
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

        # Create settings with all three keys
        settings = Settings(
            openai_api_key="sk-openai-test",
            anthropic_api_key="sk-ant-test",
            openrouter_api_key="sk-or-test",
        )

        # Test that each provider can be used independently
        with patch("src.agent.agent.Agent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance

            # Test OpenAI
            settings.model_name = "openai:gpt-4o-mini"
            agent_openai = create_agent(settings)
            assert agent_openai == mock_instance

            # Test Anthropic
            mock_agent.reset_mock()
            settings.model_name = "anthropic:claude-3-5-sonnet-latest"
            agent_anthropic = create_agent(settings)
            assert agent_anthropic == mock_instance

            # Test OpenRouter
            mock_agent.reset_mock()
            settings.model_name = "openrouter:anthropic/claude-3.5-sonnet"
            agent_openrouter = create_agent(settings)
            assert agent_openrouter == mock_instance


@pytest.mark.integration
class TestProviderPrefixExtraction:
    """Test suite for provider prefix extraction from model names."""

    def test_provider_prefix_extraction_anthropic(self) -> None:
        """Test that provider prefix is correctly extracted for Anthropic models."""
        settings = Settings(
            model_name="anthropic:claude-3-5-sonnet-latest",
            anthropic_api_key="sk-ant-test",
        )

        with patch("src.agent.agent.Agent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance

            # Create agent and check logging happens
            with patch("src.agent.agent.logger") as mock_logger:
                create_agent(settings)

                # Verify logger.info was called with provider information
                mock_logger.info.assert_any_call(
                    "agent_creation_started",
                    model="anthropic:claude-3-5-sonnet-latest",
                    provider="anthropic",
                )

    def test_provider_prefix_extraction_openrouter(self) -> None:
        """Test that provider prefix is correctly extracted for OpenRouter models."""
        settings = Settings(
            model_name="openrouter:anthropic/claude-3.5-sonnet",
            openrouter_api_key="sk-or-test",
        )

        with patch("src.agent.agent.Agent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance

            with patch("src.agent.agent.logger") as mock_logger:
                create_agent(settings)

                mock_logger.info.assert_any_call(
                    "agent_creation_started",
                    model="openrouter:anthropic/claude-3.5-sonnet",
                    provider="openrouter",
                )

    def test_provider_prefix_extraction_openai(self) -> None:
        """Test that provider prefix is correctly extracted for OpenAI models."""
        settings = Settings(
            model_name="openai:gpt-4o-mini",
            openai_api_key="sk-test",
        )

        with patch("src.agent.agent.Agent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance

            with patch("src.agent.agent.logger") as mock_logger:
                create_agent(settings)

                mock_logger.info.assert_any_call(
                    "agent_creation_started",
                    model="openai:gpt-4o-mini",
                    provider="openai",
                )

    def test_provider_prefix_missing(self) -> None:
        """Test behavior when model name has no provider prefix."""
        settings = Settings(
            model_name="gpt-4o-mini",  # No prefix
            openai_api_key="sk-test",
        )

        with patch("src.agent.agent.Agent") as mock_agent:
            mock_instance = MagicMock()
            mock_agent.return_value = mock_instance

            with patch("src.agent.agent.logger") as mock_logger:
                create_agent(settings)

                # Should log "unknown" as provider when prefix is missing
                mock_logger.info.assert_any_call(
                    "agent_creation_started",
                    model="gpt-4o-mini",
                    provider="unknown",
                )
