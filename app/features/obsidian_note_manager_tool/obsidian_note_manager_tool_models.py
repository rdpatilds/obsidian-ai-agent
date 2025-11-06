"""Pydantic models for Obsidian Note Manager Tool."""

from pydantic import BaseModel, Field


class ObsidianNoteManagerToolResult(BaseModel):
    """Result returned by obsidian_note_manager_tool."""

    success: bool = Field(..., description="Whether operation completed successfully")
    operation: str = Field(..., description="Operation type that was executed")
    affected_count: int = Field(..., description="Number of items affected by operation")
    affected_paths: list[str] = Field(..., description="List of paths that were modified")
    message: str = Field(..., description="Human-readable summary of operation result")
    warnings: list[str] | None = Field(
        default=None, description="Non-fatal issues encountered during operation"
    )

    # For bulk operations
    partial_success: bool | None = Field(
        default=None,
        description="True if some items succeeded and some failed (bulk operations only)",
    )
    failures: list[dict[str, str]] | None = Field(
        default=None,
        description="List of failed items with reasons (bulk operations only). Format: [{'path': '...', 'reason': '...'}]",
    )
