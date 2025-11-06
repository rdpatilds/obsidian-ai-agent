"""Integration tests for obsidian_get_context_tool."""

import pytest

from app.features.obsidian_get_context_tool.obsidian_get_context_tool_service import (
    execute_gather_related,
    execute_read_multiple,
    execute_read_note,
)
from app.shared.vault.vault_manager import VaultManager


@pytest.mark.asyncio
async def test_read_note_integration(test_vault_manager: VaultManager) -> None:
    """Test reading note works end-to-end."""
    result = await execute_read_note(test_vault_manager, "project_alpha.md", "detailed")
    assert result.primary_note.path == "project_alpha.md"
    assert result.primary_note.title == "Project Alpha"
    assert result.primary_note.content is not None
    assert result.primary_note.word_count > 0
    assert result.token_estimate > 0


@pytest.mark.asyncio
async def test_read_multiple_integration(test_vault_manager: VaultManager) -> None:
    """Test reading multiple notes works end-to-end."""
    result = await execute_read_multiple(
        test_vault_manager, ["project_alpha.md", "meeting_notes.md", "daily_journal.md"], "detailed"
    )
    assert result.primary_note.path == "project_alpha.md"
    assert result.related_notes is not None
    assert len(result.related_notes) == 2
    assert result.token_estimate > 0


@pytest.mark.asyncio
async def test_gather_related_integration(test_vault_manager: VaultManager) -> None:
    """Test gathering related notes works end-to-end."""
    result = await execute_gather_related(test_vault_manager, "project_alpha.md", 2, "detailed")
    assert result.primary_note.path == "project_alpha.md"
    # Related notes may be empty or present depending on similarity
    assert isinstance(result.related_notes, (list, type(None)))
    assert result.token_estimate > 0
