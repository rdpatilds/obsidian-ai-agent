"""Tests for Obsidian Graph Analyzer service layer."""

import pytest

from src.tools.obsidian_graph_analyzer.schemas import GraphAnalysisRequest
from src.tools.obsidian_graph_analyzer.service import analyze_graph_service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_analysis_depth_1(temp_vault: str) -> None:
    """Test graph analysis with depth 1 (immediate neighbors)."""
    # Create linked notes: center -> note1, center -> note2
    center_path = f"{temp_vault}/center.md"
    with open(center_path, "w") as f:
        f.write("Links to [[note1]] and [[note2]]")

    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("Note 1 content")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("Note 2 content")

    request = GraphAnalysisRequest(
        center_note="center.md",
        depth=1,
    )

    result = await analyze_graph_service(request, temp_vault)

    assert result.center_note == "center.md"
    assert result.total_nodes == 3  # center, note1, note2
    assert result.depth_reached == 1

    # Find center node
    center_node = next(n for n in result.nodes if n.path == "center.md")
    assert len(center_node.outbound_links) == 2
    assert "note1.md" in center_node.outbound_links
    assert "note2.md" in center_node.outbound_links


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_analysis_depth_2(temp_vault: str) -> None:
    """Test graph analysis with depth 2 (extended network)."""
    # Create chain: center -> note1 -> note2
    center_path = f"{temp_vault}/center.md"
    with open(center_path, "w") as f:
        f.write("Links to [[note1]]")

    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("Links to [[note2]]")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("End of chain")

    request = GraphAnalysisRequest(
        center_note="center.md",
        depth=2,
    )

    result = await analyze_graph_service(request, temp_vault)

    assert result.total_nodes == 3  # All three should be found
    assert result.depth_reached == 2

    # Verify depths
    center_node = next(n for n in result.nodes if n.path == "center.md")
    note1_node = next(n for n in result.nodes if n.path == "note1.md")
    note2_node = next(n for n in result.nodes if n.path == "note2.md")

    assert center_node.depth == 0
    assert note1_node.depth == 1
    assert note2_node.depth == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_analysis_backlinks(temp_vault: str) -> None:
    """Test that backlinks (inbound links) are correctly identified."""
    # Create: note1 -> center, note2 -> center
    center_path = f"{temp_vault}/center.md"
    with open(center_path, "w") as f:
        f.write("Central note")

    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("Links to [[center]]")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("Also links to [[center]]")

    # Start from center with depth 1 (won't find backlinks via traversal)
    request = GraphAnalysisRequest(
        center_note="center.md",
        depth=1,
    )

    result = await analyze_graph_service(request, temp_vault)

    # Center should have no outbound links but we won't see backlinks
    # unless we traverse FROM the linking notes

    # Now start from note1 (will see center)
    request2 = GraphAnalysisRequest(
        center_note="note1.md",
        depth=1,
    )

    result2 = await analyze_graph_service(request2, temp_vault)

    note1_node = next(n for n in result2.nodes if n.path == "note1.md")
    center_node = next(n for n in result2.nodes if n.path == "center.md")

    # note1 links to center
    assert "center.md" in note1_node.outbound_links
    # center should show note1 as inbound
    assert "note1.md" in center_node.inbound_links


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_analysis_circular_links(temp_vault: str) -> None:
    """Test handling of circular link relationships."""
    # Create circular: A -> B -> C -> A
    note_a_path = f"{temp_vault}/a.md"
    with open(note_a_path, "w") as f:
        f.write("Links to [[b]]")

    note_b_path = f"{temp_vault}/b.md"
    with open(note_b_path, "w") as f:
        f.write("Links to [[c]]")

    note_c_path = f"{temp_vault}/c.md"
    with open(note_c_path, "w") as f:
        f.write("Links to [[a]]")

    request = GraphAnalysisRequest(
        center_note="a.md",
        depth=3,
    )

    result = await analyze_graph_service(request, temp_vault)

    # Should handle circular reference without infinite loop
    assert result.total_nodes == 3
    assert not result.truncated


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_analysis_tag_filter(temp_vault: str) -> None:
    """Test filtering graph traversal by tags."""
    # Create notes with different tags
    center_path = f"{temp_vault}/center.md"
    with open(center_path, "w") as f:
        f.write("---\ntags: [project]\n---\nLinks to [[tagged]] and [[untagged]]")

    tagged_path = f"{temp_vault}/tagged.md"
    with open(tagged_path, "w") as f:
        f.write("---\ntags: [project]\n---\nTagged content")

    untagged_path = f"{temp_vault}/untagged.md"
    with open(untagged_path, "w") as f:
        f.write("No tags here")

    request = GraphAnalysisRequest(
        center_note="center.md",
        depth=1,
        filter_tags=["project"],
    )

    result = await analyze_graph_service(request, temp_vault)

    # Should only include notes with "project" tag
    assert result.total_nodes == 2  # center and tagged, not untagged
    paths = [n.path for n in result.nodes]
    assert "center.md" in paths
    assert "tagged.md" in paths
    assert "untagged.md" not in paths


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_analysis_content_preview(temp_vault: str) -> None:
    """Test content preview inclusion."""
    center_path = f"{temp_vault}/center.md"
    content = "This is a long note with many words. " * 20  # Long content
    with open(center_path, "w") as f:
        f.write(content)

    # With preview
    request_with_preview = GraphAnalysisRequest(
        center_note="center.md",
        depth=1,
        include_content_preview=True,
    )

    result_with = await analyze_graph_service(request_with_preview, temp_vault)
    center_node_with = result_with.nodes[0]
    assert center_node_with.content_preview is not None
    assert len(center_node_with.content_preview) > 0

    # Without preview
    request_without_preview = GraphAnalysisRequest(
        center_note="center.md",
        depth=1,
        include_content_preview=False,
    )

    result_without = await analyze_graph_service(request_without_preview, temp_vault)
    center_node_without = result_without.nodes[0]
    assert center_node_without.content_preview is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_analysis_center_not_found(temp_vault: str) -> None:
    """Test error when center note doesn't exist."""
    request = GraphAnalysisRequest(
        center_note="nonexistent.md",
        depth=1,
    )

    with pytest.raises(FileNotFoundError):
        await analyze_graph_service(request, temp_vault)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_graph_analysis_wikilink_with_folder(temp_vault: str) -> None:
    """Test resolving wikilinks with folder paths."""
    import os

    # Create subfolder
    subfolder = f"{temp_vault}/subfolder"
    os.makedirs(subfolder, exist_ok=True)

    center_path = f"{temp_vault}/center.md"
    with open(center_path, "w") as f:
        f.write("Links to [[subfolder/nested]]")

    nested_path = f"{subfolder}/nested.md"
    with open(nested_path, "w") as f:
        f.write("Nested content")

    request = GraphAnalysisRequest(
        center_note="center.md",
        depth=1,
    )

    result = await analyze_graph_service(request, temp_vault)

    assert result.total_nodes == 2
    paths = [n.path for n in result.nodes]
    assert "subfolder/nested.md" in paths
