"""Tests for Obsidian Graph Analyzer schemas."""

import pytest

from src.tools.obsidian_graph_analyzer.schemas import (
    GraphAnalysisRequest,
    GraphNode,
)


@pytest.mark.unit
def test_graph_node() -> None:
    """Test GraphNode creation."""
    node = GraphNode(
        path="test.md",
        title="Test Note",
        tags=["project", "active"],
        outbound_links=["other.md"],
        inbound_links=["source.md"],
        content_preview="Preview content...",
        depth=1,
    )

    assert node.path == "test.md"
    assert node.title == "Test Note"
    assert node.tags == ["project", "active"]
    assert node.outbound_links == ["other.md"]
    assert node.inbound_links == ["source.md"]
    assert node.content_preview == "Preview content..."
    assert node.depth == 1


@pytest.mark.unit
def test_graph_analysis_request_defaults() -> None:
    """Test GraphAnalysisRequest defaults."""
    request = GraphAnalysisRequest(center_note="test.md")

    assert request.center_note == "test.md"
    assert request.depth == 1
    assert request.include_content_preview is True
    assert request.filter_tags is None


@pytest.mark.unit
def test_graph_analysis_request_with_depth() -> None:
    """Test GraphAnalysisRequest with custom depth."""
    request = GraphAnalysisRequest(
        center_note="test.md",
        depth=2,
        include_content_preview=False,
    )

    assert request.depth == 2
    assert request.include_content_preview is False


@pytest.mark.unit
def test_graph_analysis_request_depth_validation() -> None:
    """Test depth validation (1-3)."""
    # Valid depths
    for depth in [1, 2, 3]:
        request = GraphAnalysisRequest(center_note="test.md", depth=depth)
        assert request.depth == depth

    # Invalid depths should raise validation error
    with pytest.raises(Exception):  # Pydantic validation error
        GraphAnalysisRequest(center_note="test.md", depth=0)

    with pytest.raises(Exception):
        GraphAnalysisRequest(center_note="test.md", depth=4)
