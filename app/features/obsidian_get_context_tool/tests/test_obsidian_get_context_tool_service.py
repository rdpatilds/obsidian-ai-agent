"""Tests for obsidian_get_context_tool service layer."""

import pytest

from app.features.obsidian_get_context_tool.obsidian_get_context_tool_service import (
    execute_daily_note,
    execute_gather_related,
    execute_note_with_backlinks,
    execute_read_multiple,
    execute_read_note,
)
from app.shared.vault.vault_manager import VaultManager


@pytest.mark.asyncio
async def test_read_note_basic(test_vault_manager: VaultManager) -> None:
    """Test basic note reading."""
    result = await execute_read_note(test_vault_manager, "project_alpha.md", "concise")
    assert result.primary_note.path == "project_alpha.md"
    assert result.primary_note.word_count > 0
    assert result.token_estimate > 0


@pytest.mark.asyncio
async def test_read_note_detailed_format(test_vault_manager: VaultManager) -> None:
    """Test detailed format includes metadata."""
    result = await execute_read_note(test_vault_manager, "project_alpha.md", "detailed")
    assert result.primary_note.metadata is not None
    assert "tags" in result.primary_note.metadata


@pytest.mark.asyncio
async def test_read_note_not_found(test_vault_manager: VaultManager) -> None:
    """Test reading non-existent note raises error."""
    with pytest.raises(FileNotFoundError):
        await execute_read_note(test_vault_manager, "nonexistent.md", "concise")


@pytest.mark.asyncio
async def test_read_multiple_notes(test_vault_manager: VaultManager) -> None:
    """Test reading multiple notes."""
    result = await execute_read_multiple(
        test_vault_manager, ["project_alpha.md", "meeting_notes.md"], "concise"
    )
    assert result.primary_note.path == "project_alpha.md"
    assert result.related_notes is not None
    assert len(result.related_notes) == 1


@pytest.mark.asyncio
async def test_gather_related_notes(test_vault_manager: VaultManager) -> None:
    """Test gathering related notes."""
    result = await execute_gather_related(test_vault_manager, "project_alpha.md", 2, "concise")
    assert result.primary_note.path == "project_alpha.md"
    assert isinstance(result.related_notes, (list, type(None)))


@pytest.mark.asyncio
async def test_note_with_backlinks_no_backlinks(test_vault_manager: VaultManager) -> None:
    """Test note with no backlinks."""
    result = await execute_note_with_backlinks(test_vault_manager, "project_alpha.md", "concise")
    assert result.primary_note.path == "project_alpha.md"
    assert result.backlinks is None or len(result.backlinks) == 0


@pytest.mark.asyncio
async def test_daily_note_not_found(test_vault_manager: VaultManager) -> None:
    """Test daily note missing raises error with helpful message."""
    with pytest.raises(FileNotFoundError, match="Tried:"):
        await execute_daily_note(test_vault_manager, "2099-12-31", "concise")


@pytest.mark.asyncio
async def test_concise_vs_detailed_metadata(test_vault_manager: VaultManager) -> None:
    """Test concise omits metadata, detailed includes it."""
    concise = await execute_read_note(test_vault_manager, "project_alpha.md", "concise")
    detailed = await execute_read_note(test_vault_manager, "project_alpha.md", "detailed")
    assert concise.primary_note.metadata is None
    assert detailed.primary_note.metadata is not None
