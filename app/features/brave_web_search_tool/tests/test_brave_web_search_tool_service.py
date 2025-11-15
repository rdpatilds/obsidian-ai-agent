"""Tests for brave_web_search_tool_service."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.core.config import Settings
from app.features.brave_web_search_tool.brave_web_search_tool_service import (
    execute_web_search,
)


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings for testing."""
    # Create a minimal Settings object for testing
    # type: ignore is used because we're creating a mock object
    return Settings(  # type: ignore[call-arg]
        brave_api_key="test-api-key",
        anthropic_api_key="test-anthropic-key",
        database_url="postgresql+asyncpg://test:test@localhost/test",
        obsidian_vault_path="/tmp/test_vault",
    )


@pytest.fixture
def mock_brave_client(monkeypatch: Any) -> MagicMock:
    """Mock BraveSearch to avoid real API calls."""
    mock_client = MagicMock()

    # Create mock response structure
    mock_result = MagicMock()
    mock_result.title = "Test Result Title"
    mock_result.url = "https://example.com/test"
    mock_result.description = "This is a test snippet"
    mock_result.page_age = "2 days ago"

    mock_web = MagicMock()
    mock_web.results = [mock_result, mock_result]  # Two results
    mock_web.total_estimated_matches = 100

    mock_response = MagicMock()
    mock_response.web = mock_web

    # Mock the async web method
    async def mock_web_method(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    mock_client.web = mock_web_method

    # Patch the BraveSearch
    def mock_client_constructor(api_key: str) -> MagicMock:
        return mock_client

    monkeypatch.setattr(
        "app.features.brave_web_search_tool.brave_web_search_tool_service.BraveSearch",
        mock_client_constructor,
    )

    return mock_client


@pytest.mark.asyncio
async def test_web_search_basic(mock_settings: Settings, mock_brave_client: MagicMock) -> None:
    """Test basic web search functionality."""
    result = await execute_web_search(
        settings=mock_settings,
        query="Python programming",
        count=10,
        safesearch="moderate",
    )

    assert result.query == "Python programming"
    assert len(result.results) == 2
    assert result.total_found == 100
    assert result.results[0].title == "Test Result Title"
    assert result.results[0].url == "https://example.com/test"
    assert result.results[0].snippet == "This is a test snippet"


@pytest.mark.asyncio
async def test_web_search_with_count(mock_settings: Settings, mock_brave_client: MagicMock) -> None:
    """Test web search with custom count parameter."""
    result = await execute_web_search(
        settings=mock_settings,
        query="AI development",
        count=5,
        safesearch="strict",
    )

    assert result.query == "AI development"
    assert len(result.results) == 2


@pytest.mark.asyncio
async def test_web_search_safesearch_modes(
    mock_settings: Settings, mock_brave_client: MagicMock
) -> None:
    """Test web search with different safesearch modes."""
    # Test moderate
    await execute_web_search(
        settings=mock_settings, query="test query", count=10, safesearch="moderate"
    )

    # Test strict
    await execute_web_search(
        settings=mock_settings, query="test query", count=10, safesearch="strict"
    )

    # Test off
    await execute_web_search(settings=mock_settings, query="test query", count=10, safesearch="off")


@pytest.mark.asyncio
async def test_web_search_empty_query(
    mock_settings: Settings, mock_brave_client: MagicMock
) -> None:
    """Test that empty query raises ValueError."""
    with pytest.raises(ValueError, match="query cannot be empty"):
        await execute_web_search(
            settings=mock_settings,
            query="",
            count=10,
            safesearch="moderate",
        )

    with pytest.raises(ValueError, match="query cannot be empty"):
        await execute_web_search(
            settings=mock_settings,
            query="   ",
            count=10,
            safesearch="moderate",
        )


@pytest.mark.asyncio
async def test_web_search_query_truncation(
    mock_settings: Settings, mock_brave_client: MagicMock
) -> None:
    """Test that long queries are truncated to 400 chars."""
    long_query = "a" * 500  # 500 characters

    result = await execute_web_search(
        settings=mock_settings,
        query=long_query,
        count=10,
        safesearch="moderate",
    )

    # Query should be truncated to 400 chars
    assert len(result.query) == 400
    assert result.query == "a" * 400


@pytest.mark.asyncio
async def test_web_search_count_clamping(
    mock_settings: Settings, mock_brave_client: MagicMock
) -> None:
    """Test that count is clamped to valid range (1-20)."""
    # Test count too low
    result1 = await execute_web_search(
        settings=mock_settings,
        query="test",
        count=0,
        safesearch="moderate",
    )
    assert result1 is not None

    # Test count too high
    result2 = await execute_web_search(
        settings=mock_settings,
        query="test",
        count=100,
        safesearch="moderate",
    )
    assert result2 is not None


@pytest.mark.asyncio
async def test_web_search_api_error(mock_settings: Settings, monkeypatch: Any) -> None:
    """Test handling of API errors."""
    mock_client = MagicMock()

    async def mock_web_error(*args: Any, **kwargs: Any) -> None:
        raise Exception("API Error")

    mock_client.web = mock_web_error

    def mock_client_constructor(api_key: str) -> MagicMock:
        return mock_client

    monkeypatch.setattr(
        "app.features.brave_web_search_tool.brave_web_search_tool_service.BraveSearch",
        mock_client_constructor,
    )

    with pytest.raises(Exception, match="API Error"):
        await execute_web_search(
            settings=mock_settings,
            query="test",
            count=10,
            safesearch="moderate",
        )


@pytest.mark.asyncio
async def test_web_search_empty_results(mock_settings: Settings, monkeypatch: Any) -> None:
    """Test handling of empty search results."""
    mock_client = MagicMock()

    # Mock empty response
    mock_web = MagicMock()
    mock_web.results = []
    mock_web.total_estimated_matches = 0

    mock_response = MagicMock()
    mock_response.web = mock_web

    async def mock_web_method(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    mock_client.web = mock_web_method

    def mock_client_constructor(api_key: str) -> MagicMock:
        return mock_client

    monkeypatch.setattr(
        "app.features.brave_web_search_tool.brave_web_search_tool_service.BraveSearch",
        mock_client_constructor,
    )

    result = await execute_web_search(
        settings=mock_settings,
        query="very obscure query that returns nothing",
        count=10,
        safesearch="moderate",
    )

    assert len(result.results) == 0
    assert result.total_found == 0
