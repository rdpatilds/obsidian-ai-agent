"""Schemas for Obsidian Vault Organizer tool.

Defines request/response models for batch vault organization operations.
"""

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class OrganizeOperation(str, Enum):
    """Supported batch organization operations."""

    MOVE = "move"
    TAG = "tag"
    ARCHIVE = "archive"
    DELETE = "delete"


class OrganizeRequest(BaseModel):
    """Request for batch vault organization operation."""

    notes: list[str] = Field(..., min_length=1, max_length=20)
    """List of note paths to organize (max 20 for safety)."""

    operation: OrganizeOperation
    """Operation to perform: move, tag, archive, or delete."""

    destination: str | None = None
    """Destination folder for MOVE (required) or ARCHIVE (optional, auto-generates timestamp if not provided)."""

    tags_to_add: list[str] | None = None
    """Tags to add for TAG operation."""

    tags_to_remove: list[str] | None = None
    """Tags to remove for TAG operation."""

    require_confirmation: bool = True
    """Require explicit confirmation for DELETE operation."""

    dry_run: bool = False
    """Preview changes without executing (returns what would happen)."""

    @model_validator(mode="after")
    def validate_operation_requirements(self) -> "OrganizeRequest":
        """Validate operation-specific requirements."""
        # MOVE requires destination (ARCHIVE auto-generates if not provided)
        if self.operation == OrganizeOperation.MOVE:
            if not self.destination:
                raise ValueError("move operation requires destination")

        # TAG requires at least one tag list
        if self.operation == OrganizeOperation.TAG:
            if not self.tags_to_add and not self.tags_to_remove:
                raise ValueError("TAG operation requires tags_to_add or tags_to_remove")

        return self


class NoteOperationResult(BaseModel):
    """Result of a single note operation."""

    path: str
    """Path of the note that was operated on."""

    success: bool
    """Whether the operation succeeded."""

    message: str
    """Success or error message."""

    new_path: str | None = None
    """New path after MOVE/ARCHIVE operation."""


class OrganizeResponse(BaseModel):
    """Response from batch vault organization operation."""

    operation: OrganizeOperation
    """Operation that was performed."""

    results: list[NoteOperationResult]
    """Results for each note."""

    total_requested: int
    """Total number of notes requested."""

    total_succeeded: int
    """Total number of notes that succeeded."""

    total_failed: int
    """Total number of notes that failed."""

    rolled_back: bool
    """Whether operation was rolled back due to failure."""

    dry_run: bool
    """Whether this was a dry-run preview."""

    message: str
    """Overall operation message."""
