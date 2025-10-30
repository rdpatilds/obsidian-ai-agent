"""Tests for web search tool registration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tools.web_search.tool import register_web_search_tool


@pytest.mark.unit
def test_tool_registration() -> None:
    """Test that tool registration doesn't raise errors."""
    mock_agent = MagicMock()

    # Should not raise any exceptions
    register_web_search_tool(mock_agent)

    # Verify tool decorator was called
    assert mock_agent.tool.called


@pytest.mark.integration
@pytest.mark.asyncio
async def test_web_search_tool_execution() -> None:
    """Test web search tool execution end-to-end."""
    from unittest.mock import MagicMock

    # Create mock agent
    mock_agent = MagicMock()
    tool_func = None

    # Capture the tool function when it's registered
    def capture_tool(func):  # type: ignore[no-untyped-def]
        nonlocal tool_func
        tool_func = func
        return func

    mock_agent.tool = capture_tool

    # Register the tool
    register_web_search_tool(mock_agent)

    # Verify tool was registered
    assert tool_func is not None

    # Create mock context (web_search doesn't use deps)
    mock_ctx = MagicMock()

    # Mock the HTTP response
    mock_response = AsyncMock()
    mock_response.text = """
    <html>
    <div class="result">
        <a class="result__a" href="https://example.com">Test Result</a>
        <a class="result__snippet">Test snippet content</a>
    </div>
    </html>
    """
    mock_response.raise_for_status = lambda: None

    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=mock_response
        )

        # Execute the tool
        result = await tool_func(
            mock_ctx, query="test query", max_results=5, response_format="concise"
        )

        # Verify results
        assert isinstance(result, str)
        assert "Test Result" in result
        assert "https://example.com" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_web_search_tool_error_handling() -> None:
    """Test web search tool handles errors gracefully."""
    from unittest.mock import MagicMock

    import httpx

    # Create mock agent and capture tool
    mock_agent = MagicMock()
    tool_func = None

    def capture_tool(func):  # type: ignore[no-untyped-def]
        nonlocal tool_func
        tool_func = func
        return func

    mock_agent.tool = capture_tool

    # Register the tool
    register_web_search_tool(mock_agent)

    # Create mock context (web_search doesn't use deps)
    mock_ctx = MagicMock()

    # Mock HTTP error
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=httpx.HTTPError("Network error")
        )

        # Execute the tool - should return error message instead of raising
        result = await tool_func(mock_ctx, query="test", max_results=5)

        assert isinstance(result, str)
        assert "Web search failed" in result
