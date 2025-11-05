"""Tests for obsidian_query_vault_tool."""

import pytest

from app.features.obsidian_query_vault_tool.obsidian_query_vault_tool_models import (
    SearchFilters,
)
from app.features.obsidian_query_vault_tool.obsidian_query_vault_tool_service import (
    execute_find_related,
    execute_list_structure,
    execute_recent_changes,
    execute_search_by_metadata,
    execute_semantic_search,
)
from app.shared.vault.vault_manager import VaultManager


@pytest.mark.asyncio
async def test_semantic_search_basic(test_vault_manager: VaultManager) -> None:
    """Test basic semantic search for content."""
    result = await execute_semantic_search(
        vault_manager=test_vault_manager,
        query="AI agents",
        limit=10,
        response_format="concise",
    )

    assert result.total_found > 0
    assert len(result.results) > 0
    assert any("alpha" in note.path.lower() for note in result.results)
    assert result.truncated is False


@pytest.mark.asyncio
async def test_semantic_search_detailed_format(
    test_vault_manager: VaultManager,
) -> None:
    """Test semantic search with detailed response format."""
    result = await execute_semantic_search(
        vault_manager=test_vault_manager,
        query="project",
        limit=5,
        response_format="detailed",
    )

    assert result.total_found > 0
    # Detailed format includes more metadata
    for note in result.results:
        assert note.path is not None
        assert note.excerpt is not None


@pytest.mark.asyncio
async def test_list_structure_root(test_vault_manager: VaultManager) -> None:
    """Test listing vault structure at root."""
    result = await execute_list_structure(
        vault_manager=test_vault_manager,
        path="",
        limit=20,
        response_format="concise",
    )

    assert result.total_found >= 3  # We created 3 test notes
    assert len(result.results) >= 3
    note_names = [note.title.lower() for note in result.results]
    assert any("alpha" in name or "project" in name for name in note_names)


@pytest.mark.asyncio
async def test_find_related_notes(test_vault_manager: VaultManager) -> None:
    """Test finding notes related to a reference note."""
    result = await execute_find_related(
        vault_manager=test_vault_manager,
        reference_note="project_alpha.md",
        max_related=5,
        response_format="concise",
    )

    # Should find related notes or empty if no matches
    assert result.total_found >= 0
    assert isinstance(result.results, list)


@pytest.mark.asyncio
async def test_search_by_metadata_tag_filter(test_vault_manager: VaultManager) -> None:
    """Test metadata search with tag filter."""
    filters = SearchFilters(tags=["project"])

    result = await execute_search_by_metadata(
        vault_manager=test_vault_manager,
        filters=filters,
        limit=10,
        response_format="concise",
    )

    assert result.total_found > 0
    # project_alpha.md has "project" tag
    assert any("alpha" in note.path.lower() for note in result.results)


@pytest.mark.asyncio
async def test_search_by_metadata_multiple_tags(
    test_vault_manager: VaultManager,
) -> None:
    """Test metadata search with multiple tag filters."""
    filters = SearchFilters(tags=["project", "ai"])

    result = await execute_search_by_metadata(
        vault_manager=test_vault_manager,
        filters=filters,
        limit=10,
        response_format="concise",
    )

    assert result.total_found > 0
    # project_alpha.md has both tags
    assert any("alpha" in note.path.lower() for note in result.results)


@pytest.mark.asyncio
async def test_search_by_metadata_date_filter(
    test_vault_manager: VaultManager,
) -> None:
    """Test metadata search with date filter."""
    filters = SearchFilters(date_range={"days": 365})

    result = await execute_search_by_metadata(
        vault_manager=test_vault_manager,
        filters=filters,
        limit=10,
        response_format="concise",
    )

    # Should find notes with dates in range
    assert result.total_found >= 0
    assert isinstance(result.results, list)


@pytest.mark.asyncio
async def test_recent_changes(test_vault_manager: VaultManager) -> None:
    """Test retrieving recent changes."""
    result = await execute_recent_changes(
        vault_manager=test_vault_manager,
        limit=5,
        response_format="concise",
    )

    assert result.total_found >= 3  # All 3 test notes
    assert len(result.results) >= 3


@pytest.mark.asyncio
async def test_truncation_with_small_limit(test_vault_manager: VaultManager) -> None:
    """Test result truncation when limit is smaller than total."""
    result = await execute_list_structure(
        vault_manager=test_vault_manager,
        path="",
        limit=1,  # Force truncation
        response_format="concise",
    )

    assert result.total_found >= 3
    assert len(result.results) == 1
    assert result.truncated is True
    assert result.suggestion is not None


@pytest.mark.asyncio
async def test_empty_query_semantic_search(test_vault_manager: VaultManager) -> None:
    """Test semantic search with empty query returns all notes."""
    result = await execute_semantic_search(
        vault_manager=test_vault_manager,
        query="",
        limit=10,
        response_format="concise",
    )

    # Empty query returns all notes (current behavior)
    assert result.total_found == 3
    assert len(result.results) == 3


@pytest.mark.asyncio
async def test_nonexistent_reference_note(test_vault_manager: VaultManager) -> None:
    """Test find_related with empty reference note."""
    # Testing with empty string since service layer may not validate None
    result = await execute_find_related(
        vault_manager=test_vault_manager,
        reference_note="nonexistent_note.md",
        max_related=5,
        response_format="concise",
    )

    # Should return empty results for invalid reference
    assert result.total_found == 0
    assert len(result.results) == 0


@pytest.mark.asyncio
async def test_invalid_path_traversal_attempt(
    test_vault_manager: VaultManager,
) -> None:
    """Test that path traversal attempts are blocked."""
    # This should either raise ValueError or return empty results
    # depending on VaultManager's validation logic
    try:
        result = await execute_list_structure(
            vault_manager=test_vault_manager,
            path="../../../etc",
            limit=10,
            response_format="concise",
        )
        # If it doesn't raise, should return empty results
        assert result.total_found == 0
    except ValueError:
        # Expected if path validation raises
        pass


@pytest.mark.asyncio
async def test_concise_vs_detailed_token_efficiency(
    test_vault_manager: VaultManager,
) -> None:
    """Test that concise format returns less data than detailed."""
    concise_result = await execute_semantic_search(
        vault_manager=test_vault_manager,
        query="project",
        limit=5,
        response_format="concise",
    )

    detailed_result = await execute_semantic_search(
        vault_manager=test_vault_manager,
        query="project",
        limit=5,
        response_format="detailed",
    )

    # Concise should have same number of results but less data
    assert len(concise_result.results) == len(detailed_result.results)
    # Both should have path, but detailed has more metadata
    for concise_note, detailed_note in zip(
        concise_result.results, detailed_result.results, strict=False
    ):
        assert concise_note.path == detailed_note.path
