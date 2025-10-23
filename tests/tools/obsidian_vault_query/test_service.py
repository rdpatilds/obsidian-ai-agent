"""Tests for Obsidian Vault Query service layer."""

import pytest

from src.shared.response_formatter import ResponseFormat
from src.tools.obsidian_vault_query.schemas import QueryMode, QueryRequest
from src.tools.obsidian_vault_query.service import query_vault_service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fulltext_query_finds_matches(temp_vault: str) -> None:
    """Test full-text search finds matching notes."""
    # Create test notes
    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("This is about machine learning and AI")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("This is about data science")

    note3_path = f"{temp_vault}/note3.md"
    with open(note3_path, "w") as f:
        f.write("Machine learning is a subset of AI")

    request = QueryRequest(
        query="machine learning",
        mode=QueryMode.FULLTEXT,
        max_results=10,
    )

    result = await query_vault_service(request, temp_vault)

    assert result.total_found == 2
    assert len(result.results) == 2
    assert result.mode == QueryMode.FULLTEXT

    # Should be sorted by match count
    assert result.results[0].match_count is not None
    assert result.results[0].excerpt is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fulltext_query_case_sensitive(temp_vault: str) -> None:
    """Test case-sensitive full-text search."""
    note_path = f"{temp_vault}/note.md"
    with open(note_path, "w") as f:
        f.write("API is different from api")

    # Case-insensitive (default)
    request = QueryRequest(
        query="API",
        mode=QueryMode.FULLTEXT,
        case_sensitive=False,
    )
    result = await query_vault_service(request, temp_vault)
    assert result.results[0].match_count == 2  # Both "API" and "api"

    # Case-sensitive
    request_sensitive = QueryRequest(
        query="API",
        mode=QueryMode.FULLTEXT,
        case_sensitive=True,
    )
    result_sensitive = await query_vault_service(request_sensitive, temp_vault)
    assert result_sensitive.results[0].match_count == 1  # Only "API"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fulltext_query_no_matches(temp_vault: str) -> None:
    """Test full-text search with no matches."""
    note_path = f"{temp_vault}/note.md"
    with open(note_path, "w") as f:
        f.write("Some content")

    request = QueryRequest(
        query="nonexistent",
        mode=QueryMode.FULLTEXT,
    )

    result = await query_vault_service(request, temp_vault)

    assert result.total_found == 0
    assert len(result.results) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_properties_query_exact_match(temp_vault: str) -> None:
    """Test properties query with exact matching."""
    # Create notes with different properties
    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("---\nstatus: active\npriority: 8\n---\nContent")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("---\nstatus: inactive\npriority: 3\n---\nContent")

    note3_path = f"{temp_vault}/note3.md"
    with open(note3_path, "w") as f:
        f.write("---\nstatus: active\npriority: 5\n---\nContent")

    request = QueryRequest(
        query="",
        mode=QueryMode.PROPERTIES,
        property_filters={"status": "active"},
        max_results=10,
    )

    result = await query_vault_service(request, temp_vault)

    assert result.total_found == 2
    assert len(result.results) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_properties_query_with_operators(temp_vault: str) -> None:
    """Test properties query with comparison operators."""
    # Create notes with numeric properties
    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("---\npriority: 8\n---\nContent")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("---\npriority: 3\n---\nContent")

    note3_path = f"{temp_vault}/note3.md"
    with open(note3_path, "w") as f:
        f.write("---\npriority: 10\n---\nContent")

    request = QueryRequest(
        query="",
        mode=QueryMode.PROPERTIES,
        property_filters={"priority": {"$gte": 8}},
    )

    result = await query_vault_service(request, temp_vault)

    assert result.total_found == 2  # priority 8 and 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tags_query_frontmatter_tags(temp_vault: str) -> None:
    """Test tags query with frontmatter tags."""
    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("---\ntags: [project, review]\n---\nContent")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("---\ntags: [archive]\n---\nContent")

    note3_path = f"{temp_vault}/note3.md"
    with open(note3_path, "w") as f:
        f.write("---\ntags: [project]\n---\nContent")

    request = QueryRequest(
        query="",
        mode=QueryMode.TAGS,
        tag_filters=["project"],
    )

    result = await query_vault_service(request, temp_vault)

    assert result.total_found == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tags_query_inline_tags(temp_vault: str) -> None:
    """Test tags query with inline tags."""
    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("Content with #project tag")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("Content with #archive tag")

    request = QueryRequest(
        query="",
        mode=QueryMode.TAGS,
        tag_filters=["project"],
    )

    result = await query_vault_service(request, temp_vault)

    assert result.total_found == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tags_query_or_logic(temp_vault: str) -> None:
    """Test tags query with OR logic (any tag matches)."""
    note1_path = f"{temp_vault}/note1.md"
    with open(note1_path, "w") as f:
        f.write("---\ntags: [project]\n---\nContent")

    note2_path = f"{temp_vault}/note2.md"
    with open(note2_path, "w") as f:
        f.write("---\ntags: [review]\n---\nContent")

    note3_path = f"{temp_vault}/note3.md"
    with open(note3_path, "w") as f:
        f.write("---\ntags: [archive]\n---\nContent")

    request = QueryRequest(
        query="",
        mode=QueryMode.TAGS,
        tag_filters=["project", "review"],  # Match either
    )

    result = await query_vault_service(request, temp_vault)

    assert result.total_found == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pagination(temp_vault: str) -> None:
    """Test result pagination."""
    # Create multiple notes
    for i in range(25):
        note_path = f"{temp_vault}/note{i}.md"
        with open(note_path, "w") as f:
            f.write(f"Content with keyword number {i}")

    request = QueryRequest(
        query="keyword",
        mode=QueryMode.FULLTEXT,
        max_results=10,
        offset=0,
    )

    result = await query_vault_service(request, temp_vault)

    assert result.total_found == 25
    assert len(result.results) == 10
    assert result.truncated is True
    assert result.guidance_message is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_response_format_minimal(temp_vault: str) -> None:
    """Test minimal response format."""
    note_path = f"{temp_vault}/note.md"
    with open(note_path, "w") as f:
        f.write("---\ntags: [test]\n---\n" + "Content " * 100)

    request = QueryRequest(
        query="Content",
        mode=QueryMode.FULLTEXT,
        response_format=ResponseFormat.MINIMAL,
    )

    result = await query_vault_service(request, temp_vault)

    assert len(result.results) == 1
    # Minimal format should have compact metadata
    assert result.results[0].metadata is not None
