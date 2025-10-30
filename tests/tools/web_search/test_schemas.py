"""Tests for web search schemas."""

import pytest
from pydantic import ValidationError

from src.tools.web_search.schemas import (
    WebSearchRequest,
    WebSearchResponse,
    WebSearchResult,
)


@pytest.mark.unit
def test_web_search_request_default_values() -> None:
    """Test WebSearchRequest with default values."""
    request = WebSearchRequest(query="test query")

    assert request.query == "test query"
    assert request.max_results == 5
    assert request.response_format == "concise"


@pytest.mark.unit
def test_web_search_request_custom_values() -> None:
    """Test WebSearchRequest with custom values."""
    request = WebSearchRequest(
        query="python async",
        max_results=3,
        response_format="minimal",
    )

    assert request.query == "python async"
    assert request.max_results == 3
    assert request.response_format == "minimal"


@pytest.mark.unit
def test_web_search_request_empty_query_fails() -> None:
    """Test that empty query raises validation error."""
    with pytest.raises(ValidationError):
        WebSearchRequest(query="")


@pytest.mark.unit
def test_web_search_request_max_results_validation() -> None:
    """Test max_results validation (must be 1-10)."""
    # Valid range
    request = WebSearchRequest(query="test", max_results=1)
    assert request.max_results == 1

    request = WebSearchRequest(query="test", max_results=10)
    assert request.max_results == 10

    # Invalid: too low
    with pytest.raises(ValidationError):
        WebSearchRequest(query="test", max_results=0)

    # Invalid: too high
    with pytest.raises(ValidationError):
        WebSearchRequest(query="test", max_results=11)


@pytest.mark.unit
def test_web_search_request_response_format_validation() -> None:
    """Test response_format validation."""
    # Valid formats
    for fmt in ["minimal", "concise", "detailed"]:
        request = WebSearchRequest(query="test", response_format=fmt)
        assert request.response_format == fmt

    # Invalid format
    with pytest.raises(ValidationError, match="response_format must be one of"):
        WebSearchRequest(query="test", response_format="invalid")


@pytest.mark.unit
def test_web_search_result_creation() -> None:
    """Test creating a WebSearchResult."""
    result = WebSearchResult(
        title="Test Title",
        url="https://example.com",
        snippet="This is a test snippet",
    )

    assert result.title == "Test Title"
    assert result.url == "https://example.com"
    assert result.snippet == "This is a test snippet"


@pytest.mark.unit
def test_web_search_response_default() -> None:
    """Test WebSearchResponse with default values."""
    response = WebSearchResponse()

    assert response.results == []
    assert response.total_found == 0


@pytest.mark.unit
def test_web_search_response_with_results() -> None:
    """Test WebSearchResponse with results."""
    results = [
        WebSearchResult(
            title="Result 1",
            url="https://example1.com",
            snippet="Snippet 1",
        ),
        WebSearchResult(
            title="Result 2",
            url="https://example2.com",
            snippet="Snippet 2",
        ),
    ]

    response = WebSearchResponse(results=results, total_found=2)

    assert len(response.results) == 2
    assert response.total_found == 2
    assert response.results[0].title == "Result 1"
    assert response.results[1].title == "Result 2"
