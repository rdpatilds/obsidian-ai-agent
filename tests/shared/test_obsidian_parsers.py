"""Tests for Obsidian-specific parsing utilities."""

import pytest

from src.shared.obsidian_parsers import (
    WikiLink,
    extract_frontmatter_safely,
    extract_inline_tags,
    extract_wikilinks,
    get_all_tags,
    parse_frontmatter_tags,
)


@pytest.mark.unit
def test_extract_wikilinks_simple() -> None:
    """Test extracting simple wikilinks."""
    content = "This links to [[Project Alpha]] and [[Overview]]."

    links = extract_wikilinks(content)

    assert len(links) == 2
    assert links[0].target == "Project Alpha"
    assert links[0].display_text is None
    assert links[0].is_embed is False
    assert links[1].target == "Overview"


@pytest.mark.unit
def test_extract_wikilinks_with_display_text() -> None:
    """Test extracting wikilinks with custom display text."""
    content = "See [[Project Alpha|the project]] for details."

    links = extract_wikilinks(content)

    assert len(links) == 1
    assert links[0].target == "Project Alpha"
    assert links[0].display_text == "the project"
    assert links[0].is_embed is False


@pytest.mark.unit
def test_extract_wikilinks_with_headings() -> None:
    """Test extracting wikilinks with heading anchors."""
    content = "Jump to [[Project#Overview]] or [[Tasks#Completed|done tasks]]."

    links = extract_wikilinks(content)

    assert len(links) == 2
    assert links[0].target == "Project"
    assert links[0].heading == "Overview"
    assert links[0].display_text is None
    assert links[1].target == "Tasks"
    assert links[1].heading == "Completed"
    assert links[1].display_text == "done tasks"


@pytest.mark.unit
def test_extract_wikilinks_embeds() -> None:
    """Test extracting embedded notes."""
    content = "![[Image]] and ![[Diagram|with caption]]"

    links = extract_wikilinks(content)

    assert len(links) == 2
    assert links[0].target == "Image"
    assert links[0].is_embed is True
    assert links[1].target == "Diagram"
    assert links[1].display_text == "with caption"
    assert links[1].is_embed is True


@pytest.mark.unit
def test_extract_wikilinks_line_numbers() -> None:
    """Test that line numbers are captured correctly."""
    content = "Line 0 [[Link1]]\nLine 1 [[Link2]]\nLine 2 [[Link3]]"

    links = extract_wikilinks(content)

    assert len(links) == 3
    assert links[0].line_number == 0
    assert links[1].line_number == 1
    assert links[2].line_number == 2


@pytest.mark.unit
def test_extract_inline_tags_simple() -> None:
    """Test extracting simple inline tags."""
    content = "This is #project and #review content."

    tags = extract_inline_tags(content)

    assert len(tags) == 2
    assert "project" in tags
    assert "review" in tags


@pytest.mark.unit
def test_extract_inline_tags_nested() -> None:
    """Test extracting nested tags."""
    content = "Tags: #project/alpha #team/engineering"

    tags = extract_inline_tags(content)

    assert len(tags) == 2
    assert "project/alpha" in tags
    assert "team/engineering" in tags


@pytest.mark.unit
def test_extract_inline_tags_with_underscores_hyphens() -> None:
    """Test tags with underscores and hyphens."""
    content = "Using #tag_name and #tag-name formats."

    tags = extract_inline_tags(content)

    assert len(tags) == 2
    assert "tag_name" in tags
    assert "tag-name" in tags


@pytest.mark.unit
def test_extract_inline_tags_ignores_code() -> None:
    """Test that tags in code blocks are ignored."""
    content = """
    Some text #real-tag

    ```python
    # This is a comment #not-a-tag
    print("#also-not-a-tag")
    ```

    More text with `inline #code-tag`.
    """

    tags = extract_inline_tags(content)

    assert len(tags) == 1
    assert "real-tag" in tags
    assert "not-a-tag" not in tags
    assert "also-not-a-tag" not in tags
    assert "code-tag" not in tags


@pytest.mark.unit
def test_extract_inline_tags_deduplication() -> None:
    """Test that duplicate tags are removed."""
    content = "#project appears #project multiple #project times #review"

    tags = extract_inline_tags(content)

    # Should have unique tags only
    assert len(tags) == 2
    assert "project" in tags
    assert "review" in tags


@pytest.mark.unit
def test_extract_frontmatter_safely_valid() -> None:
    """Test extracting valid YAML frontmatter."""
    content = """---
title: My Note
tags: [project, review]
status: active
priority: 8
---
Note content here."""

    frontmatter, body = extract_frontmatter_safely(content)

    assert frontmatter["title"] == "My Note"
    assert frontmatter["tags"] == ["project", "review"]
    assert frontmatter["status"] == "active"
    assert frontmatter["priority"] == 8
    assert "Note content here" in body
    assert "---" not in body  # Frontmatter separator removed


@pytest.mark.unit
def test_extract_frontmatter_safely_invalid() -> None:
    """Test fallback on invalid frontmatter."""
    content = """---
invalid: yaml: structure:
this: will: fail
---
Content"""

    frontmatter, body = extract_frontmatter_safely(content)

    # Should return empty dict and full content on parse error
    assert frontmatter == {}
    assert "---" in body
    assert "Content" in body


@pytest.mark.unit
def test_extract_frontmatter_safely_no_frontmatter() -> None:
    """Test content without frontmatter."""
    content = "Just regular markdown content without frontmatter."

    frontmatter, body = extract_frontmatter_safely(content)

    assert frontmatter == {}
    assert body == content


@pytest.mark.unit
def test_parse_frontmatter_tags_array() -> None:
    """Test parsing tags from frontmatter array."""
    frontmatter_dict = {"tags": ["project", "review", "2025"]}

    tags = parse_frontmatter_tags(frontmatter_dict)

    assert len(tags) == 3
    assert "project" in tags
    assert "review" in tags
    assert "2025" in tags


@pytest.mark.unit
def test_parse_frontmatter_tags_string() -> None:
    """Test parsing tags from comma-separated string."""
    frontmatter_dict = {"tags": "project, review, 2025"}

    tags = parse_frontmatter_tags(frontmatter_dict)

    assert len(tags) == 3
    assert "project" in tags
    assert "review" in tags
    assert "2025" in tags


@pytest.mark.unit
def test_parse_frontmatter_tags_single() -> None:
    """Test parsing single tag field."""
    frontmatter_dict = {"tag": "important"}

    tags = parse_frontmatter_tags(frontmatter_dict)

    assert len(tags) == 1
    assert "important" in tags


@pytest.mark.unit
def test_get_all_tags_combined() -> None:
    """Test combining frontmatter and inline tags."""
    content = "This is #inline-tag content with #another-tag."
    frontmatter_dict = {"tags": ["frontmatter-tag", "shared-tag"]}

    all_tags = get_all_tags(content, frontmatter_dict)

    # Should have all unique tags from both sources
    assert "frontmatter-tag" in all_tags
    assert "shared-tag" in all_tags
    assert "inline-tag" in all_tags
    assert "another-tag" in all_tags


@pytest.mark.unit
def test_get_all_tags_deduplication() -> None:
    """Test that duplicate tags across sources are deduplicated."""
    content = "Content with #duplicate and #unique-inline."
    frontmatter_dict = {"tags": ["duplicate", "unique-frontmatter"]}

    all_tags = get_all_tags(content, frontmatter_dict)

    # "duplicate" should appear only once
    assert all_tags.count("duplicate") == 1
    assert "unique-inline" in all_tags
    assert "unique-frontmatter" in all_tags
