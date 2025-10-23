"""Tests for Obsidian Note Manager service layer."""

import pytest

from src.shared.response_formatter import ResponseFormat
from src.tools.obsidian_note_manager.schemas import (
    ManageNoteRequest,
    NoteOperation,
)
from src.tools.obsidian_note_manager.service import manage_note_service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_note_minimal(temp_vault: str) -> None:
    """Test reading note with minimal format."""
    # Create test note
    test_path = f"{temp_vault}/test.md"
    content = "---\ntags: [test]\n---\nTest content"
    with open(test_path, "w") as f:
        f.write(content)

    request = ManageNoteRequest(
        path="test.md",
        operation=NoteOperation.READ,
        response_format=ResponseFormat.MINIMAL,
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is True
    assert result.operation == NoteOperation.READ
    assert "title" in result.data
    assert "summary" in result.data
    assert result.token_estimate <= 100  # Minimal should be ~50 tokens


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_note_not_found(temp_vault: str) -> None:
    """Test reading non-existent note."""
    request = ManageNoteRequest(
        path="nonexistent.md",
        operation=NoteOperation.READ,
    )

    with pytest.raises(FileNotFoundError):
        await manage_note_service(request, temp_vault, max_file_size_mb=10)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_note_creates_new(temp_vault: str) -> None:
    """Test updating creates new note if doesn't exist."""
    request = ManageNoteRequest(
        path="new.md",
        operation=NoteOperation.UPDATE,
        content="New content",
        metadata_updates={"status": "active"},
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is True
    assert result.operation == NoteOperation.UPDATE

    # Verify file exists
    test_path = f"{temp_vault}/new.md"
    with open(test_path) as f:
        content = f.read()
    assert "New content" in content
    assert "status: active" in content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_note_merges_metadata(temp_vault: str) -> None:
    """Test updating merges with existing frontmatter."""
    test_path = f"{temp_vault}/existing.md"
    content = "---\ntags: [old]\npriority: 5\n---\nOld content"
    with open(test_path, "w") as f:
        f.write(content)

    request = ManageNoteRequest(
        path="existing.md",
        operation=NoteOperation.UPDATE,
        content="New content",
        metadata_updates={"status": "active", "priority": 10},
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is True

    # Verify metadata merged
    with open(test_path) as f:
        new_content = f.read()
    assert "status: active" in new_content
    assert "priority: 10" in new_content
    assert "tags:" in new_content  # Old tag preserved


@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_note_metadata_only(temp_vault: str) -> None:
    """Test UPDATE operation updating only metadata (preserving content)."""
    # Create initial note
    test_path = f"{temp_vault}/metadata-only.md"
    with open(test_path, "w") as f:
        f.write("---\ntags: [draft]\nstatus: pending\n---\n# Original Content\n\nThis should not change.")

    # Update only metadata (no content parameter)
    request = ManageNoteRequest(
        path="metadata-only.md",
        operation=NoteOperation.UPDATE,
        metadata_updates={"status": "completed", "priority": 5},
        response_format=ResponseFormat.CONCISE,
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success
    assert result.operation == NoteOperation.UPDATE

    # Verify metadata was updated but content preserved
    with open(test_path) as f:
        updated_content = f.read()

    assert "status: completed" in updated_content
    assert "priority: 5" in updated_content
    assert "# Original Content\n\nThis should not change." in updated_content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_patch_note_single_match(temp_vault: str) -> None:
    """Test patching with single match."""
    test_path = f"{temp_vault}/patch.md"
    content = "Content with TODO item"
    with open(test_path, "w") as f:
        f.write(content)

    request = ManageNoteRequest(
        path="patch.md",
        operation=NoteOperation.PATCH,
        find_replace=("TODO", "DONE"),
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is True
    assert result.data.get("match_count") == 1

    with open(test_path) as f:
        new_content = f.read()
    assert "DONE" in new_content
    assert "TODO" not in new_content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_patch_note_multiple_matches_without_replace_all(temp_vault: str) -> None:
    """Test patching with multiple matches fails without replace_all."""
    test_path = f"{temp_vault}/patch.md"
    content = "TODO item 1\nTODO item 2"
    with open(test_path, "w") as f:
        f.write(content)

    request = ManageNoteRequest(
        path="patch.md",
        operation=NoteOperation.PATCH,
        find_replace=("TODO", "DONE"),
        replace_all=False,
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is False
    assert result.data.get("match_count") == 2
    assert "replace_all=true" in result.message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_patch_note_multiple_matches_with_replace_all(temp_vault: str) -> None:
    """Test patching with multiple matches succeeds with replace_all."""
    test_path = f"{temp_vault}/patch.md"
    content = "TODO item 1\nTODO item 2\nTODO item 3"
    with open(test_path, "w") as f:
        f.write(content)

    request = ManageNoteRequest(
        path="patch.md",
        operation=NoteOperation.PATCH,
        find_replace=("TODO", "DONE"),
        replace_all=True,
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is True
    assert result.data.get("match_count") == 3

    with open(test_path) as f:
        new_content = f.read()
    assert new_content.count("DONE") == 3
    assert "TODO" not in new_content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_append_note_to_existing(temp_vault: str) -> None:
    """Test appending to existing note."""
    test_path = f"{temp_vault}/append.md"
    content = "Existing content"
    with open(test_path, "w") as f:
        f.write(content)

    request = ManageNoteRequest(
        path="append.md",
        operation=NoteOperation.APPEND,
        content="Appended content",
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is True

    with open(test_path) as f:
        new_content = f.read()
    assert "Existing content" in new_content
    assert "Appended content" in new_content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_append_note_creates_new(temp_vault: str) -> None:
    """Test appending creates new note if doesn't exist."""
    request = ManageNoteRequest(
        path="new-append.md",
        operation=NoteOperation.APPEND,
        content="First content",
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is True

    test_path = f"{temp_vault}/new-append.md"
    with open(test_path) as f:
        content = f.read()
    assert "First content" in content


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_note_with_confirmation(temp_vault: str) -> None:
    """Test deleting note with correct confirmation."""
    test_path = f"{temp_vault}/delete.md"
    with open(test_path, "w") as f:
        f.write("Content to delete")

    request = ManageNoteRequest(
        path="delete.md",
        operation=NoteOperation.DELETE,
        confirm_path="delete.md",
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is True
    import os
    assert not os.path.exists(test_path)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_note_without_confirmation(temp_vault: str) -> None:
    """Test deleting note without confirmation fails."""
    test_path = f"{temp_vault}/delete.md"
    with open(test_path, "w") as f:
        f.write("Content")

    request = ManageNoteRequest(
        path="delete.md",
        operation=NoteOperation.DELETE,
        confirm_path="wrong-path.md",  # Wrong confirmation
    )

    result = await manage_note_service(request, temp_vault, max_file_size_mb=10)

    assert result.success is False
    assert "confirmation" in result.message.lower()
    import os
    assert os.path.exists(test_path)  # File still exists
