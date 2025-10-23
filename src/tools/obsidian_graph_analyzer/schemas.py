"""Schemas for Obsidian Graph Analyzer tool."""

from pydantic import BaseModel, Field

from src.shared.response_formatter import ResponseFormat


class GraphNode(BaseModel):
    """Represents a node in the knowledge graph."""

    path: str = Field(description="Note path")
    title: str = Field(description="Note title")
    tags: list[str] = Field(default_factory=list, description="Note tags")
    outbound_links: list[str] = Field(
        default_factory=list,
        description="Paths of notes this note links to",
    )
    inbound_links: list[str] = Field(
        default_factory=list,
        description="Paths of notes that link to this note",
    )
    content_preview: str | None = Field(
        default=None,
        description="Content preview based on response_format",
    )
    depth: int = Field(default=0, description="Depth from center node")


class GraphAnalysisRequest(BaseModel):
    """Request for analyzing knowledge graph."""

    center_note: str = Field(description="Path to center note for graph analysis")

    depth: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Traversal depth (1-3, deeper graphs grow exponentially)",
    )

    include_content_preview: bool = Field(
        default=True,
        description="Include content preview for each node",
    )

    filter_tags: list[str] | None = Field(
        default=None,
        description="Only traverse notes with these tags",
    )

    response_format: ResponseFormat = Field(
        default=ResponseFormat.CONCISE,
        description="Response verbosity level",
    )


class GraphAnalysisResponse(BaseModel):
    """Response from graph analysis."""

    center_note: str = Field(description="Center note path")
    nodes: list[GraphNode] = Field(description="Graph nodes found")
    total_nodes: int = Field(description="Total nodes in graph")
    depth_reached: int = Field(description="Maximum depth reached")
    truncated: bool = Field(
        default=False,
        description="Whether results were truncated (hit node limit)",
    )
