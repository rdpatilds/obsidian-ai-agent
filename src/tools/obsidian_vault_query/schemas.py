"""Schemas for Obsidian Vault Query tool."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from src.shared.response_formatter import ResponseFormat


class QueryMode(str, Enum):
    """Query mode types for vault search."""

    FULLTEXT = "fulltext"
    """Search note content for text matches."""

    PROPERTIES = "properties"
    """Filter notes by frontmatter properties."""

    TAGS = "tags"
    """Filter notes by tags (frontmatter and inline)."""

    DATAVIEW = "dataview"
    """Execute Dataview Query Language (DQL) queries."""


class QueryRequest(BaseModel):
    """Request for querying the vault."""

    query: str = Field(description="Search query or DQL statement")

    mode: QueryMode = Field(
        default=QueryMode.FULLTEXT,
        description="Query type: fulltext, properties, tags, or dataview",
    )

    property_filters: dict[str, Any] | None = Field(
        default=None,
        description='For properties mode: {"status": "active", "priority": {"$gt": 5}}',
    )

    tag_filters: list[str] | None = Field(
        default=None,
        description='For tags mode: ["project", "review"]',
    )

    case_sensitive: bool = Field(
        default=False,
        description="Case-sensitive search for fulltext mode",
    )

    max_results: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return",
    )

    offset: int = Field(
        default=0,
        ge=0,
        description="Result offset for pagination",
    )

    sort_by: str = Field(
        default="relevance",
        description="Sort order: relevance, modified, created",
    )

    response_format: ResponseFormat = Field(
        default=ResponseFormat.CONCISE,
        description="Response verbosity level",
    )


class QueryResult(BaseModel):
    """Individual query result."""

    path: str = Field(description="Note path")
    title: str = Field(description="Note title")
    excerpt: str | None = Field(default=None, description="Content excerpt around match")
    match_count: int | None = Field(default=None, description="Number of matches in note")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Note metadata based on response_format",
    )


class QueryResponse(BaseModel):
    """Response from vault query."""

    results: list[QueryResult] = Field(description="Query results")
    total_found: int = Field(description="Total number of matching notes")
    truncated: bool = Field(description="Whether results were truncated")
    query: str = Field(description="Original query")
    mode: QueryMode = Field(description="Query mode used")
    guidance_message: str | None = Field(
        default=None,
        description="Helpful message if results truncated or empty",
    )
