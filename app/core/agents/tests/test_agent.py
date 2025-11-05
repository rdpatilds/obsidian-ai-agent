"""Unit tests for Pydantic AI agent."""

from dataclasses import is_dataclass
from pathlib import Path
from unittest.mock import MagicMock

from app.core.agents import AgentDeps, vault_agent
from app.core.config import Settings


def test_agent_initialization() -> None:
    """Test agent is properly initialized."""
    assert vault_agent is not None
    assert "anthropic" in str(vault_agent.model).lower()


def test_agent_deps_initialization() -> None:
    """Test AgentDeps instantiation with required parameters."""
    vault_manager = MagicMock()
    settings = Settings(
        app_name="Test",
        version="1.0.0",
        database_url="postgresql://test",
        anthropic_api_key="test-key",
        obsidian_vault_path=str(Path.cwd()),
    )
    deps = AgentDeps(vault_manager=vault_manager, settings=settings)
    assert deps is not None
    assert deps.vault_manager is vault_manager
    assert deps.settings is settings


def test_agent_deps_is_dataclass() -> None:
    """Test AgentDeps is dataclass."""
    assert is_dataclass(AgentDeps)
