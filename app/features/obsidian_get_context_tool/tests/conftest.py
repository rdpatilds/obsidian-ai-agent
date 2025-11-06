"""Test fixtures for obsidian_get_context_tool - reuse from query tool."""

from app.features.obsidian_query_vault_tool.tests.conftest import (
    test_agent_deps,
    test_vault_manager,
    test_vault_path,
)

__all__ = ["test_agent_deps", "test_vault_manager", "test_vault_path"]
