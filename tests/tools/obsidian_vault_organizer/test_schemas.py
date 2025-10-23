"""Unit tests for Obsidian Vault Organizer schemas."""

import pytest
from pydantic import ValidationError

from src.tools.obsidian_vault_organizer.schemas import (
    NoteOperationResult,
    OrganizeOperation,
    OrganizeRequest,
    OrganizeResponse,
)


@pytest.mark.unit
def test_organize_operation_enum() -> None:
    """Test OrganizeOperation enum values."""
    assert OrganizeOperation.MOVE == "move"
    assert OrganizeOperation.TAG == "tag"
    assert OrganizeOperation.ARCHIVE == "archive"
    assert OrganizeOperation.DELETE == "delete"


@pytest.mark.unit
def test_organize_request_move() -> None:
    """Test OrganizeRequest for MOVE operation."""
    request = OrganizeRequest(
        notes=["project-alpha.md"],
        operation=OrganizeOperation.MOVE,
        destination="archive/2025",
    )
    assert request.notes == ["project-alpha.md"]
    assert request.operation == OrganizeOperation.MOVE
    assert request.destination == "archive/2025"


@pytest.mark.unit
def test_organize_request_tag() -> None:
    """Test OrganizeRequest for TAG operation."""
    request = OrganizeRequest(
        notes=["note1.md", "note2.md"],
        operation=OrganizeOperation.TAG,
        tags_to_add=["review", "important"],
        tags_to_remove=["draft"],
    )
    assert request.operation == OrganizeOperation.TAG
    assert request.tags_to_add == ["review", "important"]
    assert request.tags_to_remove == ["draft"]


@pytest.mark.unit
def test_organize_request_move_requires_destination() -> None:
    """Test MOVE operation requires destination."""
    with pytest.raises(ValidationError, match="requires destination"):
        OrganizeRequest(
            notes=["note.md"],
            operation=OrganizeOperation.MOVE,
        )


@pytest.mark.unit
def test_organize_request_tag_requires_tags() -> None:
    """Test TAG operation requires tags_to_add or tags_to_remove."""
    with pytest.raises(ValidationError, match="requires tags_to_add or tags_to_remove"):
        OrganizeRequest(
            notes=["note.md"],
            operation=OrganizeOperation.TAG,
        )


@pytest.mark.unit
def test_organize_request_max_notes_limit() -> None:
    """Test notes list has max limit of 20."""
    with pytest.raises(ValidationError):
        OrganizeRequest(
            notes=[f"note{i}.md" for i in range(21)],  # 21 notes > max 20
            operation=OrganizeOperation.TAG,
            tags_to_add=["test"],
        )


@pytest.mark.unit
def test_organize_request_min_notes_required() -> None:
    """Test notes list requires at least 1 note."""
    with pytest.raises(ValidationError):
        OrganizeRequest(
            notes=[],
            operation=OrganizeOperation.TAG,
            tags_to_add=["test"],
        )


@pytest.mark.unit
def test_organize_request_dry_run() -> None:
    """Test dry_run flag."""
    request = OrganizeRequest(
        notes=["note.md"],
        operation=OrganizeOperation.DELETE,
        dry_run=True,
    )
    assert request.dry_run is True


@pytest.mark.unit
def test_note_operation_result() -> None:
    """Test NoteOperationResult model."""
    result = NoteOperationResult(
        path="project-alpha.md",
        success=True,
        message="Moved successfully",
        new_path="archive/2025/project-alpha.md",
    )
    assert result.path == "project-alpha.md"
    assert result.success is True
    assert result.new_path == "archive/2025/project-alpha.md"


@pytest.mark.unit
def test_organize_response() -> None:
    """Test OrganizeResponse model."""
    results = [
        NoteOperationResult(
            path="note1.md", success=True, message="Moved successfully"
        ),
        NoteOperationResult(
            path="note2.md", success=False, message="File not found"
        ),
    ]

    response = OrganizeResponse(
        operation=OrganizeOperation.MOVE,
        results=results,
        total_requested=2,
        total_succeeded=1,
        total_failed=1,
        rolled_back=False,
        dry_run=False,
        message="Batch operation completed with 1 success, 1 failure",
    )

    assert response.total_requested == 2
    assert response.total_succeeded == 1
    assert response.total_failed == 1
    assert len(response.results) == 2
