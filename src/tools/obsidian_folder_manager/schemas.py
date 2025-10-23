"""Schemas for Obsidian Folder Manager tool.

This module provides schemas for folder management operations including:
- Creating folders (with optional parent creation)
- Renaming folders (with wikilink updates)
- Moving folders (with wikilink updates)
- Deleting folders (with confirmation and wikilink checking)
- Listing folder contents (with stats and pagination)
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from src.shared.response_formatter import ResponseFormat


class FolderOperation(str, Enum):
    """Folder operation types for folder management."""

    CREATE = "create"
    """Create a new folder with optional parent directory creation."""

    RENAME = "rename"
    """Rename a folder and update all wikilinks that reference files within it."""

    MOVE = "move"
    """Move a folder to a new location and update all wikilinks."""

    DELETE = "delete"
    """Delete a folder (requires confirmation for safety)."""

    LIST = "list"
    """List folder contents with optional statistics and pagination."""


class ManageFolderRequest(BaseModel):
    """Request for managing a folder with various operations."""

    path: str = Field(
        description="Relative path from vault root (e.g., 'projects/2025', 'archive')"
    )

    operation: FolderOperation = Field(
        description="Operation to perform on the folder"
    )

    # CREATE parameters
    create_parents: bool = Field(
        default=True,
        description="For CREATE: create parent directories if they don't exist",
    )

    # RENAME parameters
    new_name: str | None = Field(
        default=None,
        description="For RENAME: new name for the folder (single component, not full path)",
    )

    # MOVE parameters
    destination: str | None = Field(
        default=None,
        description="For MOVE: destination path relative to vault root",
    )

    # DELETE parameters
    force: bool = Field(
        default=False,
        description="For DELETE: delete non-empty folders (use with caution)",
    )

    confirm_path: str | None = Field(
        default=None,
        description="For DELETE: must match path to confirm deletion (safety check)",
    )

    check_wikilinks: bool = Field(
        default=True,
        description="For DELETE: check for incoming wikilinks and warn about broken links",
    )

    # RENAME/MOVE parameters
    update_wikilinks: bool = Field(
        default=True,
        description="For RENAME/MOVE: update wikilinks in vault that reference folder contents",
    )

    # LIST parameters
    recursive: bool = Field(
        default=False,
        description="For LIST: recursively list subfolders (depth limited to 5)",
    )

    include_stats: bool = Field(
        default=True,
        description="For LIST: include statistics (note count, size, modified date)",
    )

    max_results: int = Field(
        default=50,
        ge=1,
        le=200,
        description="For LIST: maximum number of results to return (pagination)",
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="For LIST: number of results to skip (pagination)",
    )

    # Common parameters
    dry_run: bool = Field(
        default=False,
        description="Simulate operation without making changes (for testing)",
    )

    response_format: ResponseFormat = Field(
        default=ResponseFormat.CONCISE,
        description="Response verbosity: minimal (~50 tokens), concise (~150 tokens), detailed (~300 tokens)",
    )

    @model_validator(mode="after")
    def validate_operation_params(self) -> "ManageFolderRequest":
        """Validate that required parameters are provided for each operation.

        Returns:
            Validated request model.

        Raises:
            ValueError: If required parameters are missing for the operation.
        """
        if self.operation == FolderOperation.RENAME and not self.new_name:
            msg = "RENAME operation requires new_name parameter"
            raise ValueError(msg)

        if self.operation == FolderOperation.MOVE and not self.destination:
            msg = "MOVE operation requires destination parameter"
            raise ValueError(msg)

        if self.operation == FolderOperation.DELETE:
            if not self.confirm_path:
                msg = "DELETE operation requires confirm_path parameter for safety"
                raise ValueError(msg)
            if self.confirm_path != self.path:
                msg = f"confirm_path '{self.confirm_path}' must match path '{self.path}' to confirm deletion"
                raise ValueError(msg)

        return self


class FolderInfo(BaseModel):
    """Information about a folder (used in LIST operation results)."""

    path: str = Field(description="Relative path from vault root")
    name: str = Field(description="Folder name (last component)")
    note_count: int | None = Field(
        default=None,
        description="Number of notes (.md files) in folder (if include_stats=True)",
    )
    total_size_bytes: int | None = Field(
        default=None,
        description="Total size of all files in folder in bytes (if include_stats=True)",
    )
    modified_timestamp: float | None = Field(
        default=None,
        description="Last modified timestamp (if include_stats=True)",
    )
    depth: int = Field(
        default=0,
        description="Depth from listing root (0 = immediate child)",
    )


class FolderOperationResult(BaseModel):
    """Response from folder management operation."""

    success: bool = Field(description="Whether operation succeeded")

    path: str = Field(description="Folder path that was operated on")

    operation: FolderOperation = Field(description="Operation that was performed")

    message: str = Field(description="Human-readable status message")

    new_path: str | None = Field(
        default=None,
        description="New path after RENAME/MOVE operations",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific metadata (links_updated, affected_notes, folders, pagination, etc.)",
    )

    token_estimate: int = Field(
        default=50,
        description="Estimated tokens in response (for optimization tracking)",
    )
