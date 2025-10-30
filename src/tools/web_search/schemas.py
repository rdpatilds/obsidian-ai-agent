"""Schemas for web search tool.

This module defines Pydantic models for web search requests and responses.
"""

from pydantic import BaseModel, Field, field_validator


class WebSearchRequest(BaseModel):
    """Request model for web search.

    Args:
        query: Search query string.
        max_results: Number of results to return (1-10).
        response_format: Output format - "minimal", "concise", or "detailed".
    """

    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of results to return",
    )
    response_format: str = Field(
        default="concise",
        description="Response format: minimal, concise, or detailed",
    )

    @field_validator("response_format")
    @classmethod
    def validate_response_format(cls, v: str) -> str:
        """Validate response format is one of the allowed values.

        Args:
            v: Response format value.

        Returns:
            Validated response format.

        Raises:
            ValueError: If response format is not allowed.
        """
        allowed = {"minimal", "concise", "detailed"}
        if v not in allowed:
            msg = f"response_format must be one of {allowed}, got {v}"
            raise ValueError(msg)
        return v


class WebSearchResult(BaseModel):
    """Individual search result.

    Args:
        title: Result title.
        url: Result URL.
        snippet: Result description/snippet.
    """

    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Result snippet/description")


class WebSearchResponse(BaseModel):
    """Response model for web search.

    Args:
        results: List of search results.
        total_found: Total number of results found.
    """

    results: list[WebSearchResult] = Field(
        default_factory=list,
        description="List of search results",
    )
    total_found: int = Field(
        default=0,
        ge=0,
        description="Total results found",
    )
