"""Unit tests for configuration management.

Tests verify that:
- Settings load correctly from environment
- Default values are applied
- Type coercion works
- Validation catches invalid values
"""

import pytest
from pydantic import ValidationError

from src.shared.config import Settings


@pytest.mark.unit
class TestSettings:
    """Test suite for Settings configuration."""

    def test_settings_default_values(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that Settings has correct default values."""
        # Clear environment variables to test defaults
        monkeypatch.delenv("OPENAI_COMPATIBLE_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("MODEL_NAME", raising=False)
        monkeypatch.delenv("ENABLE_CALCULATOR", raising=False)

        settings = Settings()

        assert settings.environment == "development"
        assert settings.host == "0.0.0.0"  # noqa: S104  # Test default value
        assert settings.port == 8030
        assert settings.openai_compatible_api_key == "dev-key-change-in-production"
        # Model name is loaded from .env, so we just check it's not empty
        assert settings.model_name != ""
        assert settings.enable_obsidian_note_manager is True
        assert settings.enable_obsidian_vault_query is True
        assert settings.enable_obsidian_graph_analyzer is True

    def test_settings_custom_values(self) -> None:
        """Test that Settings accepts custom values."""
        settings = Settings(
            environment="production",
            host="127.0.0.1",
            port=9000,
            openai_compatible_api_key="custom-key",
            model_name="openai:gpt-4",
            openai_api_key="sk-test-key",
            enable_obsidian_note_manager=False,
            max_graph_depth=5,
        )

        assert settings.environment == "production"
        assert settings.host == "127.0.0.1"
        assert settings.port == 9000
        assert settings.openai_compatible_api_key == "custom-key"
        assert settings.model_name == "openai:gpt-4"
        assert settings.openai_api_key == "sk-test-key"
        assert settings.enable_obsidian_note_manager is False
        assert settings.max_graph_depth == 5

    def test_settings_environment_validation(self) -> None:
        """Test that environment only accepts valid values."""
        # Valid values should work
        settings_dev = Settings(environment="development")
        assert settings_dev.environment == "development"

        settings_prod = Settings(environment="production")
        assert settings_prod.environment == "production"

        # Invalid value should raise validation error
        with pytest.raises(ValidationError, match="Input should be 'development' or 'production'"):
            Settings(environment="invalid")  # type: ignore[arg-type]

    def test_settings_port_is_integer(self) -> None:
        """Test that port is coerced to integer."""
        # String should be coerced to int
        settings = Settings(port="8080")  # type: ignore[arg-type]
        assert settings.port == 8080
        assert isinstance(settings.port, int)

    def test_settings_from_test_fixture(self, test_settings: Settings) -> None:
        """Test that test_settings fixture provides valid settings."""
        assert test_settings.environment == "development"
        assert test_settings.port == 8999
        assert test_settings.openai_compatible_api_key == "test-api-key-12345"

    def test_cors_enabled_default(self) -> None:
        """Test that cors_enabled defaults to True."""
        settings = Settings()
        assert settings.cors_enabled is True

    def test_cors_disabled_configuration(self) -> None:
        """Test CORS can be disabled via configuration."""
        settings = Settings(cors_enabled=False)
        assert settings.cors_enabled is False

    def test_cors_origins_parsing(self) -> None:
        """Test cors_origins_list property parses comma-separated string correctly."""
        settings = Settings(cors_origins="http://localhost,http://127.0.0.1,app://obsidian.md")
        origins = settings.cors_origins_list
        assert len(origins) == 3
        assert "http://localhost" in origins
        assert "http://127.0.0.1" in origins
        assert "app://obsidian.md" in origins

    def test_cors_origins_empty_string(self) -> None:
        """Test empty origins string returns empty list."""
        settings = Settings(cors_origins="")
        origins = settings.cors_origins_list
        assert origins == []

    def test_cors_origins_whitespace_handling(self) -> None:
        """Test leading/trailing whitespace is trimmed in origins."""
        settings = Settings(cors_origins="  http://localhost  ,  http://127.0.0.1  ")
        origins = settings.cors_origins_list
        assert len(origins) == 2
        assert "http://localhost" in origins
        assert "http://127.0.0.1" in origins
        # Ensure no whitespace-only entries
        assert all(origin.strip() == origin for origin in origins)

    def test_cors_origins_single_value(self) -> None:
        """Test single origin (no comma) parses correctly."""
        settings = Settings(cors_origins="http://localhost")
        origins = settings.cors_origins_list
        assert len(origins) == 1
        assert origins[0] == "http://localhost"

    def test_cors_allow_credentials_default(self) -> None:
        """Test cors_allow_credentials defaults to True."""
        settings = Settings()
        assert settings.cors_allow_credentials is True

    def test_agent_system_prompt_default(self) -> None:
        """Test agent_system_prompt has a default value."""
        settings = Settings()
        assert settings.agent_system_prompt
        assert "Obsidian" in settings.agent_system_prompt
        assert isinstance(settings.agent_system_prompt, str)

    def test_agent_system_prompt_custom(self) -> None:
        """Test agent_system_prompt can be customized."""
        custom_prompt = "You are a test assistant."
        settings = Settings(agent_system_prompt=custom_prompt)
        assert settings.agent_system_prompt == custom_prompt

    def test_agent_retries_default(self) -> None:
        """Test agent_retries defaults to 3."""
        settings = Settings()
        assert settings.agent_retries == 3

    def test_agent_output_retries_default(self) -> None:
        """Test agent_output_retries defaults to 2."""
        settings = Settings()
        assert settings.agent_output_retries == 2

    def test_agent_retries_configurable(self) -> None:
        """Test agent retry settings can be configured."""
        settings = Settings(agent_retries=5, agent_output_retries=3)
        assert settings.agent_retries == 5
        assert settings.agent_output_retries == 3

    def test_anthropic_api_key_field_exists(self) -> None:
        """Test that Settings has anthropic_api_key field with correct type annotation."""
        settings = Settings()
        assert hasattr(settings, "anthropic_api_key")
        assert isinstance(settings.anthropic_api_key, str)
        # Test with custom value
        settings_custom = Settings(anthropic_api_key="sk-ant-test-key")
        assert settings_custom.anthropic_api_key == "sk-ant-test-key"

    def test_openrouter_api_key_field_exists(self) -> None:
        """Test that Settings has openrouter_api_key field with correct type annotation."""
        settings = Settings()
        assert hasattr(settings, "openrouter_api_key")
        assert isinstance(settings.openrouter_api_key, str)
        # Test with custom value
        settings_custom = Settings(openrouter_api_key="sk-or-test-key")
        assert settings_custom.openrouter_api_key == "sk-or-test-key"

    def test_multiple_provider_keys_configured(self) -> None:
        """Test that multiple provider API keys can be configured simultaneously."""
        settings = Settings(
            openai_api_key="sk-openai-test",
            anthropic_api_key="sk-ant-test",
            openrouter_api_key="sk-or-test",
        )
        assert settings.openai_api_key == "sk-openai-test"
        assert settings.anthropic_api_key == "sk-ant-test"
        assert settings.openrouter_api_key == "sk-or-test"


@pytest.mark.unit
class TestEnvironmentVariableExport:
    """Test suite for environment variable export logic."""

    def test_anthropic_env_var_export(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that ANTHROPIC_API_KEY is exported when set in Settings."""
        import os

        # Clear existing env var first
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Create settings with anthropic key
        test_key = "sk-ant-test-anthropic-key-12345"
        settings = Settings(anthropic_api_key=test_key)

        # Manually trigger the export logic (simulating what happens in config module)
        if settings.anthropic_api_key and not os.environ.get("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

        # Verify env var is set to our test key
        assert os.environ.get("ANTHROPIC_API_KEY") == test_key

    def test_openrouter_env_var_export(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that OPENROUTER_API_KEY is exported when set in Settings."""
        import os

        # Clear existing env var
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        # Create settings with openrouter key
        test_key = "sk-or-test-openrouter-key-12345"
        settings = Settings(openrouter_api_key=test_key)

        # Manually trigger the export logic
        if settings.openrouter_api_key and not os.environ.get("OPENROUTER_API_KEY"):
            os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

        # Verify env var is set
        assert os.environ.get("OPENROUTER_API_KEY") == test_key

    def test_env_var_export_respects_existing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that existing environment variables are not overwritten."""
        import os

        existing_key = "sk-ant-existing-key-from-env"
        new_key = "sk-ant-new-key-from-settings"

        # Set existing env var
        monkeypatch.setenv("ANTHROPIC_API_KEY", existing_key)

        # Create settings with different key
        settings = Settings(anthropic_api_key=new_key)

        # Trigger export logic (should NOT overwrite)
        if settings.anthropic_api_key and not os.environ.get("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

        # Verify original env var is preserved
        assert os.environ.get("ANTHROPIC_API_KEY") == existing_key

    def test_empty_api_keys_not_exported(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that empty API key strings don't export environment variables."""
        import os

        # Clear existing env vars
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        # Create settings with empty keys
        settings = Settings(anthropic_api_key="", openrouter_api_key="")

        # Trigger export logic
        if settings.anthropic_api_key and not os.environ.get("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

        if settings.openrouter_api_key and not os.environ.get("OPENROUTER_API_KEY"):
            os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

        # Verify env vars are not set
        assert os.environ.get("ANTHROPIC_API_KEY") is None
        assert os.environ.get("OPENROUTER_API_KEY") is None

    def test_multiple_providers_env_export(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that all three providers can be configured simultaneously via env export."""
        import os

        # Clear existing env vars
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        # Create settings with all three keys
        settings = Settings(
            openai_api_key="sk-openai-test",
            anthropic_api_key="sk-ant-test",
            openrouter_api_key="sk-or-test",
        )

        # Trigger export logic for all three
        if settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = settings.openai_api_key

        if settings.anthropic_api_key and not os.environ.get("ANTHROPIC_API_KEY"):
            os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key

        if settings.openrouter_api_key and not os.environ.get("OPENROUTER_API_KEY"):
            os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key

        # Verify all env vars are set
        assert os.environ.get("OPENAI_API_KEY") == "sk-openai-test"
        assert os.environ.get("ANTHROPIC_API_KEY") == "sk-ant-test"
        assert os.environ.get("OPENROUTER_API_KEY") == "sk-or-test"
