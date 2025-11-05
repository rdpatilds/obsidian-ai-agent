"""Unit tests for Pydantic AI agent."""

from dataclasses import is_dataclass

from app.core.agents import AgentDeps, vault_agent


def test_agent_initialization() -> None:
    """Test agent is properly initialized."""
    assert vault_agent is not None
    assert "anthropic" in str(vault_agent.model).lower()


def test_agent_deps_initialization() -> None:
    """Test AgentDeps instantiation."""
    deps = AgentDeps()
    assert deps is not None


def test_agent_deps_is_dataclass() -> None:
    """Test AgentDeps is dataclass."""
    assert is_dataclass(AgentDeps)
