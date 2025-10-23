"""Schemas for Obsidian Note Manager tool.

This module consolidates what would otherwise be 4 separate tools
(read_note, write_note, patch_note, update_metadata) into a single
workflow-oriented tool with operation modes.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.shared.response_formatter import ResponseFormat


class NoteOperation(str, Enum):
    """Note operation types for consolidated note management."""

    READ = "read"
    """Read note content with configurable response format."""

    UPDATE = "update"
    """Replace entire note content, optionally updating metadata."""

    PATCH = "patch"
    """Find and replace text within note (supports replace_all for multiple matches)."""

    APPEND = "append"
    """Append content to end of note, preserving existing content."""

    DELETE = "delete"
    """Delete note (requires confirmation path for safety)."""


class ManageNoteRequest(BaseModel):
    """Request for managing a note with various operations."""

    path: str = Field(description="Relative path from vault root (e.g., 'projects/alpha.md')")

    operation: NoteOperation = Field(description="Operation to perform on the note")

    content: str | None = Field(
        default=None,
        description="Content for UPDATE/APPEND operations. UPDATE: optional (preserves existing if omitted). APPEND: required. For PATCH, use find_replace instead.",
    )

    metadata_updates: dict[str, Any] | None = Field(
        default=None,
        description="Frontmatter metadata to merge (for UPDATE/APPEND operations)",
    )

    find_replace: tuple[str, str] | None = Field(
        default=None,
        description="Tuple of (find_text, replace_text) for PATCH operation",
    )

    replace_all: bool = Field(
        default=False,
        description="For PATCH: replace all occurrences (safety check for multiple matches)",
    )

    confirm_path: str | None = Field(
        default=None,
        description="Required for DELETE: must match path to confirm deletion",
    )

    response_format: ResponseFormat = Field(
        default=ResponseFormat.CONCISE,
        description="Response verbosity: minimal (~50 tokens), concise (~150 tokens), detailed (~1500+ tokens)",
    )


class ManageNoteResponse(BaseModel):
    """Response from note management operation."""

    success: bool = Field(description="Whether operation succeeded")

    path: str = Field(description="Note path that was operated on")

    operation: NoteOperation = Field(description="Operation that was performed")

    data: dict[str, Any] = Field(
        description="Operation result data (format varies by response_format)"
    )

    message: str = Field(description="Human-readable status message")

    token_estimate: int = Field(
        default=0,
        description="Estimated tokens in response (for optimization tracking)",
    )
