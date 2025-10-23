"""Unit tests for Obsidian Vault Organizer service."""

from pathlib import Path

import frontmatter
import pytest

from src.tools.obsidian_vault_organizer.schemas import OrganizeOperation, OrganizeRequest
from src.tools.obsidian_vault_organizer.service import organize_vault_service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_operation_success(temp_vault: Path) -> None:
    """Test successful MOVE operation."""
    # Create a note to move
    note_path = temp_vault / "note-to-move.md"
    note_path.write_text("# Note to Move\n\nContent here.")

    request = OrganizeRequest(
        notes=["note-to-move.md"],
        operation=OrganizeOperation.MOVE,
        destination="projects",
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_succeeded == 1
    assert response.total_failed == 0
    assert response.rolled_back is False
    assert len(response.results) == 1
    assert response.results[0].success is True
    assert "projects/note-to-move.md" in response.results[0].message

    # Verify file was moved
    assert not note_path.exists()
    assert (temp_vault / "projects" / "note-to-move.md").exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_operation_dry_run(temp_vault: Path) -> None:
    """Test MOVE operation in dry-run mode."""
    note_path = temp_vault / "test-note.md"
    note_path.write_text("# Test Note")

    request = OrganizeRequest(
        notes=["test-note.md"],
        operation=OrganizeOperation.MOVE,
        destination="archive",
        dry_run=True,
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.dry_run is True
    assert response.total_succeeded == 1
    assert "[DRY RUN]" in response.results[0].message

    # Verify file was NOT moved
    assert note_path.exists()
    assert not (temp_vault / "archive" / "test-note.md").exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tag_operation_add_tags(temp_vault: Path) -> None:
    """Test TAG operation adding tags."""
    note_path = temp_vault / "note-for-tagging.md"
    post = frontmatter.Post("# Note Content", tags=["existing"])
    note_path.write_text(frontmatter.dumps(post))

    request = OrganizeRequest(
        notes=["note-for-tagging.md"],
        operation=OrganizeOperation.TAG,
        tags_to_add=["important", "review"],
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_succeeded == 1
    assert response.results[0].success is True

    # Verify tags were added
    content = note_path.read_text()
    post = frontmatter.loads(content)
    assert "existing" in post["tags"]
    assert "important" in post["tags"]
    assert "review" in post["tags"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tag_operation_remove_tags(temp_vault: Path) -> None:
    """Test TAG operation removing tags."""
    note_path = temp_vault / "note-for-untagging.md"
    post = frontmatter.Post("# Note Content", tags=["draft", "review", "keep"])
    note_path.write_text(frontmatter.dumps(post))

    request = OrganizeRequest(
        notes=["note-for-untagging.md"],
        operation=OrganizeOperation.TAG,
        tags_to_remove=["draft", "review"],
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_succeeded == 1

    # Verify tags were removed
    content = note_path.read_text()
    post = frontmatter.loads(content)
    assert "draft" not in post["tags"]
    assert "review" not in post["tags"]
    assert "keep" in post["tags"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_archive_operation_auto_generated_path(temp_vault: Path) -> None:
    """Test ARCHIVE operation with auto-generated timestamp path (destination=None)."""
    from datetime import datetime

    note_path = temp_vault / "old-note.md"
    note_path.write_text("# Old Note\n\nArchive this.")

    request = OrganizeRequest(
        notes=["old-note.md"],
        operation=OrganizeOperation.ARCHIVE,
        # destination=None → auto-generates archive/{YYYY-MM-DD}/
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_succeeded == 1
    assert "archive" in response.results[0].message

    # Verify file was archived
    assert not note_path.exists()

    # Check file was archived to auto-generated timestamp directory
    expected_date = datetime.now().strftime("%Y-%m-%d")
    archive_dir = temp_vault / "archive" / expected_date
    archived_file = archive_dir / "old-note.md"

    assert archive_dir.exists()
    assert archived_file.exists()
    assert archived_file.read_text() == "# Old Note\n\nArchive this."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_archive_operation_custom_destination(temp_vault: Path) -> None:
    """Test ARCHIVE operation with custom destination path."""
    note_path = temp_vault / "project-note.md"
    note_path.write_text("# Project Note\n\nCustom archive.")

    request = OrganizeRequest(
        notes=["project-note.md"],
        operation=OrganizeOperation.ARCHIVE,
        destination="archive/2024-projects",  # Custom destination
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_succeeded == 1
    assert "archive" in response.results[0].message

    # Verify file was archived to custom destination
    assert not note_path.exists()
    custom_archive = temp_vault / "archive" / "2024-projects" / "project-note.md"
    assert custom_archive.exists()
    assert custom_archive.read_text() == "# Project Note\n\nCustom archive."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_archive_operation(temp_vault: Path) -> None:
    """Test ARCHIVE operation with timestamp (backward compatibility)."""
    note_path = temp_vault / "old-note-2.md"
    note_path.write_text("# Old Note\n\nArchive this.")

    request = OrganizeRequest(
        notes=["old-note-2.md"],
        operation=OrganizeOperation.ARCHIVE,
        destination="archive/backup",  # Custom path
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_succeeded == 1
    assert "archive" in response.results[0].message

    # Verify file was archived
    assert not note_path.exists()

    # Check file was archived to custom backup directory
    backup_dir = temp_vault / "archive" / "backup"
    archived_file = backup_dir / "old-note-2.md"
    assert backup_dir.exists()
    assert archived_file.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_operation_with_confirmation(temp_vault: Path) -> None:
    """Test DELETE operation requires confirmation."""
    note_path = temp_vault / "delete-me.md"
    note_path.write_text("# Delete Me")

    request = OrganizeRequest(
        notes=["delete-me.md"],
        operation=OrganizeOperation.DELETE,
        require_confirmation=True,
    )

    response = await organize_vault_service(request, str(temp_vault))

    # Should fail because confirmation is required
    assert response.total_succeeded == 0
    assert response.total_failed == 1
    assert "confirmation" in response.results[0].message.lower()

    # Verify file was NOT deleted
    assert note_path.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_operation_without_confirmation(temp_vault: Path) -> None:
    """Test DELETE operation without confirmation."""
    note_path = temp_vault / "delete-me-now.md"
    note_path.write_text("# Delete Me Now")

    request = OrganizeRequest(
        notes=["delete-me-now.md"],
        operation=OrganizeOperation.DELETE,
        require_confirmation=False,
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_succeeded == 1
    assert "deleted" in response.results[0].message.lower()

    # Verify file was deleted
    assert not note_path.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_operation_dry_run(temp_vault: Path) -> None:
    """Test DELETE operation in dry-run mode (preview only)."""
    note_path = temp_vault / "preview-delete.md"
    note_path.write_text("# Preview Delete")

    request = OrganizeRequest(
        notes=["preview-delete.md"],
        operation=OrganizeOperation.DELETE,
        dry_run=True,
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.dry_run is True
    assert response.total_succeeded == 1
    assert "[DRY RUN]" in response.results[0].message
    assert "delete" in response.results[0].message.lower()

    # Verify file was NOT deleted (dry-run only)
    assert note_path.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_batch_workflow(temp_vault: Path) -> None:
    """Test recommended DELETE workflow: dry-run first, then actual deletion."""
    # Create multiple notes
    for i in range(3):
        note_path = temp_vault / f"temp-note-{i}.md"
        note_path.write_text(f"# Temp Note {i}")

    notes = [f"temp-note-{i}.md" for i in range(3)]

    # Step 1: Preview with dry-run
    preview_request = OrganizeRequest(
        notes=notes,
        operation=OrganizeOperation.DELETE,
        dry_run=True,
    )

    preview_response = await organize_vault_service(preview_request, str(temp_vault))

    assert preview_response.dry_run is True
    assert preview_response.total_succeeded == 3
    assert all("[DRY RUN]" in r.message for r in preview_response.results)

    # Verify all files still exist after preview
    for i in range(3):
        assert (temp_vault / f"temp-note-{i}.md").exists()

    # Step 2: Actually delete after confirming preview
    delete_request = OrganizeRequest(
        notes=notes,
        operation=OrganizeOperation.DELETE,
        require_confirmation=False,
    )

    delete_response = await organize_vault_service(delete_request, str(temp_vault))

    assert delete_response.total_succeeded == 3
    assert all("deleted" in r.message.lower() for r in delete_response.results)

    # Verify all files were deleted
    for i in range(3):
        assert not (temp_vault / f"temp-note-{i}.md").exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_operation_multiple_notes(temp_vault: Path) -> None:
    """Test batch operation on multiple notes."""
    # Create multiple notes
    for i in range(3):
        note_path = temp_vault / f"batch-note-{i}.md"
        post = frontmatter.Post(f"# Batch Note {i}", tags=["batch"])
        note_path.write_text(frontmatter.dumps(post))

    request = OrganizeRequest(
        notes=[f"batch-note-{i}.md" for i in range(3)],
        operation=OrganizeOperation.TAG,
        tags_to_add=["processed"],
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_requested == 3
    assert response.total_succeeded == 3
    assert response.total_failed == 0

    # Verify all notes were tagged
    for i in range(3):
        content = (temp_vault / f"batch-note-{i}.md").read_text()
        post = frontmatter.loads(content)
        assert "processed" in post["tags"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_batch_operation_partial_failure(temp_vault: Path) -> None:
    """Test batch operation with some failures."""
    # Create only 2 of 3 notes
    for i in range(2):
        note_path = temp_vault / f"partial-note-{i}.md"
        note_path.write_text(f"# Note {i}")

    request = OrganizeRequest(
        notes=[f"partial-note-{i}.md" for i in range(3)],  # 3rd note doesn't exist
        operation=OrganizeOperation.TAG,
        tags_to_add=["test"],
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_requested == 3
    assert response.total_succeeded == 2
    assert response.total_failed == 1
    assert "not found" in response.results[2].message.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_move_rollback_on_failure(temp_vault: Path) -> None:
    """Test MOVE operation rolls back on failure."""
    # Create first note (will succeed)
    note1 = temp_vault / "move-note-1.md"
    note1.write_text("# Note 1")

    # Create destination with second note already existing (will fail)
    dest_dir = temp_vault / "destination"
    dest_dir.mkdir()
    (dest_dir / "move-note-2.md").write_text("# Existing")

    # Create second note
    note2 = temp_vault / "move-note-2.md"
    note2.write_text("# Note 2")

    request = OrganizeRequest(
        notes=["move-note-1.md", "move-note-2.md"],
        operation=OrganizeOperation.MOVE,
        destination="destination",
    )

    response = await organize_vault_service(request, str(temp_vault))

    # Should rollback because second move fails
    assert response.rolled_back is True
    assert response.total_succeeded == 0

    # Verify first note was rolled back to original location
    assert note1.exists()
    assert note2.exists()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_blocked_path_rejected(temp_vault: Path) -> None:
    """Test that blocked paths are rejected."""
    # Try to organize a file in .obsidian directory
    obsidian_dir = temp_vault / ".obsidian"
    obsidian_dir.mkdir()
    blocked_note = obsidian_dir / "config.md"
    blocked_note.write_text("# Config")

    request = OrganizeRequest(
        notes=[".obsidian/config.md"],
        operation=OrganizeOperation.TAG,
        tags_to_add=["test"],
    )

    response = await organize_vault_service(request, str(temp_vault))

    assert response.total_succeeded == 0
    assert response.total_failed == 1
    assert "not allowed" in response.results[0].message.lower()
