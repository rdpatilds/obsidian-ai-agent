"""Pydantic models for Obsidian Get Context Tool."""

from pydantic import BaseModel, Field


class NoteContent(BaseModel):
    """Complete note representation for context results."""

    path: str = Field(..., description="Relative path from vault root")
    title: str = Field(..., description="Note title from frontmatter or filename")
    content: str = Field(..., description="Full markdown content without frontmatter")
    metadata: dict[str, str | list[str] | int | float | bool] | None = Field(
        default=None, description="Frontmatter metadata (detailed mode only)"
    )
    word_count: int = Field(..., description="Number of words in content")


class BacklinkInfo(BaseModel):
    """Information about a note linking to the target."""

    note_path: str = Field(..., description="Path to note containing the link")
    note_title: str = Field(..., description="Title of linking note")
    context: str = Field(..., description="Surrounding text where link appears (~100 chars)")


class ObsidianGetContextToolResult(BaseModel):
    """Result from obsidian_get_context_tool."""

    primary_note: NoteContent = Field(..., description="Main requested note")
    related_notes: list[NoteContent] | None = Field(
        default=None, description="Related notes (gather_related, note_with_backlinks)"
    )
    backlinks: list[BacklinkInfo] | None = Field(
        default=None, description="Notes linking to primary (note_with_backlinks only)"
    )
    token_estimate: int = Field(..., description="Approximate tokens in response content")
