"""Tests for Obsidian Vault Query tool registration."""

import pytest

from src.tools.obsidian_vault_query.tool import register_obsidian_vault_query_tool


@pytest.mark.unit
def test_tool_registration() -> None:
    """Test that tool registration doesn't raise errors."""
    from unittest.mock import MagicMock

    mock_agent = MagicMock()

    # Should not raise any exceptions
    register_obsidian_vault_query_tool(mock_agent)

    # Verify tool decorator was called
    assert mock_agent.tool.called
