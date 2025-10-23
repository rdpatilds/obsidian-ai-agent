"""Tests for Obsidian Note Manager schemas."""

import pytest

from src.shared.response_formatter import ResponseFormat
from src.tools.obsidian_note_manager.schemas import (
    ManageNoteRequest,
    ManageNoteResponse,
    NoteOperation,
)


@pytest.mark.unit
def test_note_operation_enum() -> None:
    """Test NoteOperation enum values."""
    assert NoteOperation.READ.value == "read"
    assert NoteOperation.UPDATE.value == "update"
    assert NoteOperation.PATCH.value == "patch"
    assert NoteOperation.APPEND.value == "append"
    assert NoteOperation.DELETE.value == "delete"


@pytest.mark.unit
def test_manage_note_request_read() -> None:
    """Test creating a read request."""
    request = ManageNoteRequest(
        path="test.md",
        operation=NoteOperation.READ,
        response_format=ResponseFormat.MINIMAL,
    )

    assert request.path == "test.md"
    assert request.operation == NoteOperation.READ
    assert request.content is None
    assert request.response_format == ResponseFormat.MINIMAL


@pytest.mark.unit
def test_manage_note_request_update() -> None:
    """Test creating an update request with metadata."""
    request = ManageNoteRequest(
        path="test.md",
        operation=NoteOperation.UPDATE,
        content="New content",
        metadata_updates={"status": "active", "priority": 8},
    )

    assert request.path == "test.md"
    assert request.operation == NoteOperation.UPDATE
    assert request.content == "New content"
    assert request.metadata_updates == {"status": "active", "priority": 8}


@pytest.mark.unit
def test_manage_note_request_patch() -> None:
    """Test creating a patch request."""
    request = ManageNoteRequest(
        path="test.md",
        operation=NoteOperation.PATCH,
        find_replace=("old", "new"),
        replace_all=True,
    )

    assert request.path == "test.md"
    assert request.operation == NoteOperation.PATCH
    assert request.find_replace == ("old", "new")
    assert request.replace_all is True


@pytest.mark.unit
def test_manage_note_request_delete() -> None:
    """Test creating a delete request with confirmation."""
    request = ManageNoteRequest(
        path="test.md",
        operation=NoteOperation.DELETE,
        confirm_path="test.md",
    )

    assert request.path == "test.md"
    assert request.operation == NoteOperation.DELETE
    assert request.confirm_path == "test.md"


@pytest.mark.unit
def test_manage_note_response() -> None:
    """Test creating a response."""
    response = ManageNoteResponse(
        success=True,
        path="test.md",
        operation=NoteOperation.READ,
        data={"title": "Test", "content": "Content"},
        message="Success",
        token_estimate=150,
    )

    assert response.success is True
    assert response.path == "test.md"
    assert response.operation == NoteOperation.READ
    assert response.data == {"title": "Test", "content": "Content"}
    assert response.message == "Success"
    assert response.token_estimate == 150
