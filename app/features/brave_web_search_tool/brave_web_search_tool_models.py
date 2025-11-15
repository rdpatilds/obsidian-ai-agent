"""Pydantic models for Brave Web Search Tool."""

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Individual web search result."""

    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str | None = Field(default=None, description="Text excerpt from the page")
    page_age: str | None = Field(
        default=None, description="Age of the page (e.g., '2 days ago', '1 week ago')"
    )


class BraveWebSearchToolResult(BaseModel):
    """Result returned by brave_web_search_tool."""

    results: list[SearchResult] = Field(..., description="List of search results")
    query: str = Field(..., description="Original search query")
    total_found: int = Field(..., description="Total number of results found")
