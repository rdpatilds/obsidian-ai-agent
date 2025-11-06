"""Tests for Obsidian Note Manager Tool service layer."""

import pytest

from app.features.obsidian_note_manager_tool import (
    obsidian_note_manager_tool_service as service,
)
from app.shared.vault.vault_manager import VaultManager


@pytest.mark.asyncio
async def test_execute_create_note_success(vault_manager: VaultManager) -> None:
    """Test successful note creation."""
    result = await service.execute_create_note(
        vault_manager,
        "test.md",
        "# Test Note\n\nContent here.",
        {"tags": ["test"]},
        True,
    )

    assert result.success is True
    assert result.operation == "create_note"
    assert result.affected_count == 1
    assert "test.md" in result.affected_paths

    # Verify file exists
    note = vault_manager.read_note("test.md")
    assert note.content == "# Test Note\n\nContent here."
    assert "test" in note.frontmatter.tags if note.frontmatter else False


@pytest.mark.asyncio
async def test_execute_create_note_already_exists(vault_manager: VaultManager) -> None:
    """Test creating note that already exists."""
    # Create first note
    vault_manager.write_note("exists.md", "content", None, overwrite=False)

    # Try to create again
    result = await service.execute_create_note(
        vault_manager, "exists.md", "new content", None, False
    )

    assert result.success is False
    assert result.affected_count == 0
    assert "already exists" in result.message.lower() or "failed" in result.message.lower()


@pytest.mark.asyncio
async def test_execute_update_note_success(vault_manager: VaultManager, sample_note: str) -> None:
    """Test successful note update."""
    result = await service.execute_update_note(
        vault_manager, sample_note, "# Updated Content", {"tags": ["updated"]}
    )

    assert result.success is True
    assert result.operation == "update_note"
    assert result.affected_count == 1
    assert sample_note in result.affected_paths

    # Verify content updated
    note = vault_manager.read_note(sample_note)
    assert note.content == "# Updated Content"


@pytest.mark.asyncio
async def test_execute_update_note_not_found(vault_manager: VaultManager) -> None:
    """Test updating non-existent note."""
    result = await service.execute_update_note(
        vault_manager, "nonexistent.md", "content", None
    )

    assert result.success is False
    assert result.affected_count == 0
    assert "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_execute_append_note_success(vault_manager: VaultManager, sample_note: str) -> None:
    """Test successful content append."""
    result = await service.execute_append_note(
        vault_manager, sample_note, "\n\n## Appended Section"
    )

    assert result.success is True
    assert result.operation == "append_note"
    assert result.affected_count == 1

    # Verify content appended
    note = vault_manager.read_note(sample_note)
    assert "## Appended Section" in note.content


@pytest.mark.asyncio
async def test_execute_append_note_not_found(vault_manager: VaultManager) -> None:
    """Test appending to non-existent note."""
    result = await service.execute_append_note(vault_manager, "missing.md", "content")

    assert result.success is False
    assert "not found" in result.message.lower()


@pytest.mark.asyncio
async def test_execute_delete_note_without_confirmation(vault_manager: VaultManager) -> None:
    """Test delete note fails without confirmation."""
    vault_manager.write_note("delete_me.md", "content", None, overwrite=True)

    result = await service.execute_delete_note(vault_manager, "delete_me.md", False)

    assert result.success is False
    assert result.affected_count == 0
    assert "confirm_destructive" in result.message


@pytest.mark.asyncio
async def test_execute_delete_note_with_confirmation(vault_manager: VaultManager) -> None:
    """Test successful note deletion with confirmation."""
    vault_manager.write_note("delete_me.md", "content", None, overwrite=True)

    result = await service.execute_delete_note(vault_manager, "delete_me.md", True)

    assert result.success is True
    assert result.operation == "delete_note"
    assert result.affected_count == 1

    # Verify note deleted
    with pytest.raises(FileNotFoundError):
        vault_manager.read_note("delete_me.md")


@pytest.mark.asyncio
async def test_execute_move_note_success(vault_manager: VaultManager, sample_note: str) -> None:
    """Test successful note move."""
    result = await service.execute_move_note(
        vault_manager, sample_note, "moved/relocated.md", True
    )

    assert result.success is True
    assert result.operation == "move_note"
    assert result.affected_count == 1
    assert "moved/relocated.md" in result.affected_paths

    # Verify note moved
    note = vault_manager.read_note("moved/relocated.md")
    assert "Sample Note" in note.content


@pytest.mark.asyncio
async def test_execute_create_folder_success(vault_manager: VaultManager) -> None:
    """Test successful folder creation."""
    result = await service.execute_create_folder(vault_manager, "new_folder", False)

    assert result.success is True
    assert result.operation == "create_folder"
    assert result.affected_count == 1

    # Verify folder exists
    folder_path = vault_manager.vault_root / "new_folder"
    assert folder_path.exists()
    assert folder_path.is_dir()


@pytest.mark.asyncio
async def test_execute_delete_folder_success(vault_manager: VaultManager) -> None:
    """Test successful folder deletion."""
    vault_manager.create_folder("delete_folder", exist_ok=True)

    result = await service.execute_delete_folder(vault_manager, "delete_folder", True, False)

    assert result.success is True
    assert result.operation == "delete_folder"
    assert result.affected_count == 1


@pytest.mark.asyncio
async def test_execute_move_folder_success(vault_manager: VaultManager) -> None:
    """Test successful folder move."""
    vault_manager.create_folder("old_folder", exist_ok=True)

    result = await service.execute_move_folder(vault_manager, "old_folder", "new_location")

    assert result.success is True
    assert result.operation == "move_folder"
    assert "new_location" in result.affected_paths


@pytest.mark.asyncio
async def test_execute_bulk_tag_success(vault_manager: VaultManager) -> None:
    """Test successful bulk tagging."""
    # Create multiple notes
    vault_manager.write_note("note1.md", "content1", {"tags": ["existing"]}, overwrite=True)
    vault_manager.write_note("note2.md", "content2", None, overwrite=True)

    result = await service.execute_bulk_tag(
        vault_manager, ["note1.md", "note2.md"], {"tags": ["bulk_added"]}
    )

    assert result.success is True
    assert result.operation == "bulk_tag"
    assert result.affected_count == 2

    # Verify tags added
    note1 = vault_manager.read_note("note1.md")
    assert "bulk_added" in (note1.frontmatter.tags if note1.frontmatter else [])


@pytest.mark.asyncio
async def test_execute_bulk_tag_partial_success(vault_manager: VaultManager) -> None:
    """Test bulk tagging with some failures."""
    vault_manager.write_note("exists.md", "content", None, overwrite=True)

    result = await service.execute_bulk_tag(
        vault_manager, ["exists.md", "missing.md"], {"tags": ["test"]}
    )

    # Should have partial success
    assert result.affected_count == 1
    assert result.partial_success is True
    assert result.failures is not None
    assert len(result.failures) == 1


@pytest.mark.asyncio
async def test_execute_bulk_move_success(vault_manager: VaultManager) -> None:
    """Test successful bulk move."""
    vault_manager.write_note("move1.md", "content1", None, overwrite=True)
    vault_manager.write_note("move2.md", "content2", None, overwrite=True)

    result = await service.execute_bulk_move(
        vault_manager, ["move1.md", "move2.md"], "archive", True
    )

    assert result.success is True
    assert result.operation == "bulk_move"
    assert result.affected_count == 2

    # Verify notes moved
    note1 = vault_manager.read_note("archive/move1.md")
    assert note1.content == "content1"


@pytest.mark.asyncio
async def test_execute_bulk_update_metadata_success(vault_manager: VaultManager) -> None:
    """Test successful bulk metadata update."""
    vault_manager.write_note("meta1.md", "content1", {"tags": ["old"]}, overwrite=True)
    vault_manager.write_note("meta2.md", "content2", None, overwrite=True)

    result = await service.execute_bulk_update_metadata(
        vault_manager,
        ["meta1.md", "meta2.md"],
        {"status": "archived", "priority": 1},
    )

    assert result.success is True
    assert result.operation == "bulk_update_metadata"
    assert result.affected_count == 2

    # Verify metadata updated
    note1 = vault_manager.read_note("meta1.md")
    if note1.frontmatter and note1.frontmatter.custom:
        assert note1.frontmatter.custom.get("status") == "archived"
        assert note1.frontmatter.custom.get("priority") == 1
