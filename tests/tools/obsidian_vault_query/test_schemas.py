"""Tests for Obsidian Vault Query schemas."""

import pytest

from src.shared.response_formatter import ResponseFormat
from src.tools.obsidian_vault_query.schemas import (
    QueryMode,
    QueryRequest,
    QueryResult,
)


@pytest.mark.unit
def test_query_mode_enum() -> None:
    """Test QueryMode enum values."""
    assert QueryMode.FULLTEXT.value == "fulltext"
    assert QueryMode.PROPERTIES.value == "properties"
    assert QueryMode.TAGS.value == "tags"
    assert QueryMode.DATAVIEW.value == "dataview"


@pytest.mark.unit
def test_query_request_fulltext() -> None:
    """Test creating a fulltext query request."""
    request = QueryRequest(
        query="machine learning",
        mode=QueryMode.FULLTEXT,
        case_sensitive=False,
        max_results=10,
    )

    assert request.query == "machine learning"
    assert request.mode == QueryMode.FULLTEXT
    assert request.case_sensitive is False
    assert request.max_results == 10


@pytest.mark.unit
def test_query_request_properties() -> None:
    """Test creating a properties query request."""
    request = QueryRequest(
        query="",
        mode=QueryMode.PROPERTIES,
        property_filters={"status": "active", "priority": {"$gt": 5}},
    )

    assert request.mode == QueryMode.PROPERTIES
    assert request.property_filters == {"status": "active", "priority": {"$gt": 5}}


@pytest.mark.unit
def test_query_request_tags() -> None:
    """Test creating a tags query request."""
    request = QueryRequest(
        query="",
        mode=QueryMode.TAGS,
        tag_filters=["project", "review"],
    )

    assert request.mode == QueryMode.TAGS
    assert request.tag_filters == ["project", "review"]


@pytest.mark.unit
def test_query_request_defaults() -> None:
    """Test query request defaults."""
    request = QueryRequest(query="test")

    assert request.mode == QueryMode.FULLTEXT
    assert request.case_sensitive is False
    assert request.max_results == 20
    assert request.offset == 0
    assert request.sort_by == "relevance"
    assert request.response_format == ResponseFormat.CONCISE


@pytest.mark.unit
def test_query_result() -> None:
    """Test QueryResult creation."""
    result = QueryResult(
        path="test.md",
        title="Test Note",
        excerpt="...excerpt...",
        match_count=5,
        metadata={"tags": ["test"]},
    )

    assert result.path == "test.md"
    assert result.title == "Test Note"
    assert result.excerpt == "...excerpt..."
    assert result.match_count == 5
    assert result.metadata == {"tags": ["test"]}
