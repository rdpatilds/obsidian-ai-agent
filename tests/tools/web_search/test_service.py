"""Tests for web search service layer."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.tools.web_search.schemas import WebSearchRequest
from src.tools.web_search.service import search_web


# Sample DuckDuckGo HTML response for testing
SAMPLE_DUCKDUCKGO_HTML = """
<html>
<div class="result">
    <a class="result__a" href="https://example1.com">Example Result 1</a>
    <a class="result__snippet">This is the first test snippet with some content</a>
</div>
<div class="result">
    <a class="result__a" href="https://example2.com">Example Result 2</a>
    <a class="result__snippet">This is the second test snippet with more information</a>
</div>
<div class="result">
    <a class="result__a" href="https://example3.com">Example Result 3</a>
    <a class="result__snippet">This is the third test snippet about testing</a>
</div>
</html>
"""


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_web_success_concise() -> None:
    """Test successful web search with concise format."""
    request = WebSearchRequest(
        query="python async",
        max_results=2,
        response_format="concise",
    )

    # Mock httpx response
    mock_response = AsyncMock()
    mock_response.text = SAMPLE_DUCKDUCKGO_HTML
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search_web(request)

        assert "Found 2 results" in result
        assert "Example Result 1" in result
        assert "Example Result 2" in result
        assert "https://example1.com" in result
        assert "https://example2.com" in result
        assert "first test snippet" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_web_success_minimal() -> None:
    """Test successful web search with minimal format."""
    request = WebSearchRequest(
        query="test query",
        max_results=3,
        response_format="minimal",
    )

    mock_response = AsyncMock()
    mock_response.text = SAMPLE_DUCKDUCKGO_HTML
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search_web(request)

        assert "Found 3 results" in result
        assert "Example Result 1" in result
        assert "https://example1.com" in result
        # Minimal format should NOT include snippets
        assert "snippet" not in result.lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_web_success_detailed() -> None:
    """Test successful web search with detailed format."""
    request = WebSearchRequest(
        query="test query",
        max_results=2,
        response_format="detailed",
    )

    mock_response = AsyncMock()
    mock_response.text = SAMPLE_DUCKDUCKGO_HTML
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search_web(request)

        assert "Found 2 results" in result
        assert "Example Result 1" in result
        assert "first test snippet with some content" in result
        # Detailed format should include full snippets (not truncated)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_web_no_results() -> None:
    """Test web search when no results found."""
    request = WebSearchRequest(query="test", max_results=5)

    # Empty HTML with no results
    mock_response = AsyncMock()
    mock_response.text = "<html><body>No results</body></html>"
    mock_response.raise_for_status = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search_web(request)

        assert "No results found" in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_web_http_error() -> None:
    """Test web search when HTTP request fails."""
    request = WebSearchRequest(query="test", max_results=5)

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.HTTPError("Network error")
        )

        with pytest.raises(httpx.HTTPError):
            await search_web(request)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_web_max_results_limit() -> None:
    """Test that max_results limits the number of returned results."""
    request = WebSearchRequest(
        query="test",
        max_results=1,  # Limit to 1 result
        response_format="minimal",
    )

    mock_response = AsyncMock()
    mock_response.text = SAMPLE_DUCKDUCKGO_HTML  # Has 3 results
    mock_response.raise_for_status = AsyncMock()

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search_web(request)

        assert "Found 1 results" in result
        assert "Example Result 1" in result
        # Should NOT include results 2 and 3
        assert "Example Result 2" not in result
        assert "Example Result 3" not in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_web_html_entity_decoding() -> None:
    """Test that HTML entities are properly decoded."""
    html_with_entities = """
    <html>
    <div class="result">
        <a class="result__a" href="https://example.com">Test &amp; Example</a>
        <a class="result__snippet">Snippet with &quot;quotes&quot; and &lt;tags&gt;</a>
    </div>
    </html>
    """

    request = WebSearchRequest(query="test", max_results=1, response_format="concise")

    mock_response = AsyncMock()
    mock_response.text = html_with_entities
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        result = await search_web(request)

        # Check that entities are decoded
        assert "Test & Example" in result
        assert '"quotes"' in result
        assert "<tags>" in result
