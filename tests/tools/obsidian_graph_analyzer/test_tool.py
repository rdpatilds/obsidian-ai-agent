"""Tests for Obsidian Graph Analyzer tool registration."""

import pytest

from src.tools.obsidian_graph_analyzer.tool import register_obsidian_graph_analyzer_tool


@pytest.mark.unit
def test_tool_registration() -> None:
    """Test that tool registration doesn't raise errors."""
    from unittest.mock import MagicMock

    mock_agent = MagicMock()

    # Should not raise any exceptions
    register_obsidian_graph_analyzer_tool(mock_agent)

    # Verify tool decorator was called
    assert mock_agent.tool.called
