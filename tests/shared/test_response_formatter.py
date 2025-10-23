"""Tests for response formatting utilities."""

import pytest

from src.shared.response_formatter import (
    ResponseFormat,
    estimate_tokens,
    format_note_response,
    format_query_results,
    truncate_with_guidance,
)


@pytest.mark.unit
def test_response_format_enum() -> None:
    """Test ResponseFormat enum values."""
    assert ResponseFormat.MINIMAL.value == "minimal"
    assert ResponseFormat.CONCISE.value == "concise"
    assert ResponseFormat.DETAILED.value == "detailed"


@pytest.mark.unit
def test_format_note_response_minimal() -> None:
    """Test minimal format produces ~50 tokens."""
    note_data = {
        "title": "Test Note",
        "content": "This is a long content that should be truncated in minimal format " * 10,
        "frontmatter": {"status": "active", "priority": 8},
        "tags": ["project", "test"],
        "path": "test.md",
    }

    result = format_note_response(note_data, ResponseFormat.MINIMAL)

    assert result["title"] == "Test Note"
    assert result["tags"] == ["project", "test"]
    assert result["path"] == "test.md"
    assert "summary" in result
    assert len(result["summary"]) <= 53  # 50 chars + "..."
    assert "frontmatter" not in result  # Frontmatter excluded in minimal
    assert "content" not in result  # Full content excluded


@pytest.mark.unit
def test_format_note_response_concise() -> None:
    """Test concise format produces ~150 tokens."""
    content = " ".join([f"word{i}" for i in range(150)])  # 150 words
    note_data = {
        "title": "Test Note",
        "content": content,
        "frontmatter": {"status": "active"},
        "tags": ["test"],
        "path": "test.md",
    }

    result = format_note_response(note_data, ResponseFormat.CONCISE)

    assert result["title"] == "Test Note"
    assert result["tags"] == ["test"]
    assert result["frontmatter"] == {"status": "active"}
    assert "content_preview" in result
    assert "..." in result["content_preview"]  # Truncated
    assert "content" not in result  # Full content excluded
    assert result["word_count"] == 150


@pytest.mark.unit
def test_format_note_response_detailed() -> None:
    """Test detailed format returns full content."""
    content = "Full content " * 200  # Long content
    note_data = {
        "title": "Test Note",
        "content": content,
        "frontmatter": {"status": "active", "priority": 8},
        "tags": ["test"],
        "path": "test.md",
    }

    result = format_note_response(note_data, ResponseFormat.DETAILED)

    assert result["title"] == "Test Note"
    assert result["tags"] == ["test"]
    assert result["frontmatter"] == {"status": "active", "priority": 8}
    assert result["content"] == content  # Full content included
    assert "word_count" in result
    assert "char_count" in result


@pytest.mark.unit
def test_format_query_results_minimal() -> None:
    """Test query results formatting with minimal format."""
    results = [
        {
            "title": f"Note {i}",
            "content": "Content " * 100,
            "frontmatter": {},
            "tags": [],
            "path": f"note{i}.md",
        }
        for i in range(5)
    ]

    output = format_query_results(results, ResponseFormat.MINIMAL, max_results=10)

    assert len(output["results"]) == 5
    assert output["total_found"] == 5
    assert output["returned"] == 5
    assert output["truncated"] is False
    assert "token_estimate" in output
    # Minimal: ~20 tokens per result
    assert output["token_estimate"] == 100  # 5 * 20


@pytest.mark.unit
def test_format_query_results_truncated() -> None:
    """Test query results truncation."""
    results = [{"title": f"Note {i}", "content": "", "frontmatter": {}, "tags": [], "path": f"note{i}.md"} for i in range(25)]

    output = format_query_results(results, ResponseFormat.CONCISE, max_results=10)

    assert len(output["results"]) == 10
    assert output["total_found"] == 25
    assert output["returned"] == 10
    assert output["truncated"] is True


@pytest.mark.unit
def test_truncate_with_guidance_no_overflow() -> None:
    """Test truncation when results fit within limit."""
    results = [1, 2, 3, 4, 5]

    truncated, guidance = truncate_with_guidance(results, limit=10)

    assert len(truncated) == 5
    assert guidance == ""  # No guidance when not truncated


@pytest.mark.unit
def test_truncate_with_guidance_with_overflow() -> None:
    """Test truncation with overflow provides helpful guidance."""
    results = list(range(100))

    truncated, guidance = truncate_with_guidance(results, limit=20)

    assert len(truncated) == 20
    assert "Showing 20 of 100 results" in guidance
    assert "80 more available" in guidance
    assert "property_filters" in guidance  # Suggests refinement options
    assert "tag_filters" in guidance


@pytest.mark.unit
def test_estimate_tokens() -> None:
    """Test token estimation."""
    text = "This is a test sentence with ten words in it"
    tokens = estimate_tokens(text)

    # 10 words * 1.3 = 13 tokens (approximate)
    assert tokens >= 10
    assert tokens <= 15


@pytest.mark.unit
def test_format_note_response_edge_cases() -> None:
    """Test edge cases: empty content, missing fields."""
    # Empty content
    note_data = {
        "title": "Empty",
        "content": "",
        "frontmatter": {},
        "tags": [],
        "path": "empty.md",
    }

    result = format_note_response(note_data, ResponseFormat.MINIMAL)
    assert result["summary"] == ""

    # Missing title
    note_data_no_title = {
        "content": "Content",
        "frontmatter": {},
        "tags": [],
        "path": "test.md",
    }

    result = format_note_response(note_data_no_title, ResponseFormat.CONCISE)
    assert result["title"] == "Untitled"
