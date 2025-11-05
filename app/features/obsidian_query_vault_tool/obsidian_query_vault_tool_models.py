"""Pydantic models for Obsidian Query Vault Tool."""

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Metadata search filters."""

    tags: list[str] | None = Field(default=None, description="Filter by tags (any match)")
    date_range: dict[str, int] | None = Field(
        default=None, description="Date range filter (e.g., {'days': 7})"
    )
    folder: str | None = Field(default=None, description="Filter by folder path")


class NoteInfo(BaseModel):
    """Note information returned by queries."""

    # Always included (concise mode)
    path: str = Field(..., description="Relative path to note (e.g., 'Projects/ML.md')")
    title: str = Field(..., description="Note title extracted from content or filename")
    relevance: float = Field(..., description="Relevance score (0.0-1.0) for semantic searches")

    # Detailed mode only
    excerpt: str | None = Field(default=None, description="First 200 chars or matching context")
    tags: list[str] | None = Field(default=None, description="Tags from frontmatter")
    created: str | None = Field(default=None, description="Creation date (ISO 8601)")
    modified: str | None = Field(default=None, description="Last modified date (ISO 8601)")


class ObsidianQueryVaultToolResult(BaseModel):
    """Result returned by obsidian_query_vault_tool."""

    results: list[NoteInfo] = Field(..., description="List of matching notes")
    total_found: int = Field(..., description="Total number of matches")
    truncated: bool = Field(..., description="True if results were limited (more exist)")
    suggestion: str | None = Field(
        default=None,
        description="Suggestion for refining query if truncated or no results",
    )
