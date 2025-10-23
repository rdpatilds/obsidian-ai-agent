"""Obsidian-specific parsing utilities for wikilinks, tags, and frontmatter.

This module provides robust parsers for Obsidian's markdown extensions including
wikilinks ([[note]]), embeds (![[note]]), and inline tags (#tag).
"""

import re
from dataclasses import dataclass
from typing import Any

import frontmatter  # type: ignore[import-untyped]

from src.shared.logging import get_logger


logger = get_logger(__name__)

# Regex patterns for Obsidian syntax
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
"""Matches [[target]] and [[target|display text]]."""

EMBED_PATTERN = re.compile(r"!\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")
"""Matches ![[embedded file]] and ![[embedded file|display text]]."""

INLINE_TAG_PATTERN = re.compile(r"(?:^|\s)#([a-zA-Z0-9_/-]+)")
"""Matches #tag, #nested/tag, #tag-name (not inside words)."""

HEADING_WIKILINK_PATTERN = re.compile(r"\[\[([^\]|#]+)#([^\]|]+)(?:\|([^\]]+))?\]\]")
"""Matches [[note#heading]] and [[note#heading|display]]."""


@dataclass
class WikiLink:
    """Represents a wikilink found in note content."""

    target: str
    """Target note name (without .md extension)."""

    display_text: str | None
    """Display text if using [[target|display]] syntax."""

    is_embed: bool
    """True if this is an embed (![[...]]) rather than a link."""

    heading: str | None = None
    """Heading anchor if using [[note#heading]] syntax."""

    line_number: int = 0
    """Line number where link was found (0-indexed)."""


def extract_wikilinks(content: str) -> list[WikiLink]:
    """Extract all wikilinks from note content.

    Handles multiple formats:
    - [[note name]]
    - [[note name|display text]]
    - [[note name#heading]]
    - [[note name#heading|display]]
    - ![[embedded note]]

    Args:
        content: Markdown content to parse.

    Returns:
        List of WikiLink objects found in content.

    Examples:
        >>> content = "See [[Project Alpha]] and [[Overview|summary]]"
        >>> links = extract_wikilinks(content)
        >>> len(links)
        2
        >>> links[0].target
        'Project Alpha'
        >>> links[1].display_text
        'summary'
    """
    links: list[WikiLink] = []
    lines = content.split("\n")

    for line_idx, line in enumerate(lines):
        # First, find embeds (they include !)
        for match in EMBED_PATTERN.finditer(line):
            target = match.group(1).strip()
            display = match.group(2).strip() if match.group(2) else None

            links.append(
                WikiLink(
                    target=target,
                    display_text=display,
                    is_embed=True,
                    line_number=line_idx,
                )
            )

        # Then find regular wikilinks with headings
        for match in HEADING_WIKILINK_PATTERN.finditer(line):
            target = match.group(1).strip()
            heading = match.group(2).strip()
            display = match.group(3).strip() if match.group(3) else None

            links.append(
                WikiLink(
                    target=target,
                    display_text=display,
                    is_embed=False,
                    heading=heading,
                    line_number=line_idx,
                )
            )

        # Finally, find regular wikilinks (without headings, not embeds)
        # Filter out embeds and heading links already captured
        for match in WIKILINK_PATTERN.finditer(line):
            # Skip if this is part of an embed or heading link
            if line[max(0, match.start() - 1) : match.start()] == "!":
                continue
            if "#" in match.group(0):
                continue

            target = match.group(1).strip()
            display = match.group(2).strip() if match.group(2) else None

            links.append(
                WikiLink(
                    target=target,
                    display_text=display,
                    is_embed=False,
                    line_number=line_idx,
                )
            )

    logger.debug(
        "wikilinks_extracted",
        total_links=len(links),
        embeds=sum(1 for link in links if link.is_embed),
        regular_links=sum(1 for link in links if not link.is_embed),
    )

    return links


def extract_inline_tags(content: str) -> list[str]:
    """Extract inline tags from note content.

    Handles:
    - #simple-tag
    - #nested/tag/structure
    - #tag_with_underscores

    Ignores tags inside code blocks and inline code.

    Args:
        content: Markdown content to parse.

    Returns:
        List of unique tag names (without # prefix).

    Examples:
        >>> content = "This is #project-alpha and #review"
        >>> extract_inline_tags(content)
        ['project-alpha', 'review']
    """
    # Remove code blocks first (``` ... ```)
    code_block_pattern = re.compile(r"```.*?```", re.DOTALL)
    content_no_code_blocks = code_block_pattern.sub("", content)

    # Remove inline code (` ... `)
    inline_code_pattern = re.compile(r"`[^`]+`")
    content_no_code = inline_code_pattern.sub("", content_no_code_blocks)

    # Extract tags
    tags = []
    for match in INLINE_TAG_PATTERN.finditer(content_no_code):
        tag = match.group(1)
        tags.append(tag)

    # Return unique tags, preserving order
    unique_tags = list(dict.fromkeys(tags))

    logger.debug(
        "inline_tags_extracted",
        total_tags=len(unique_tags),
        tags=unique_tags,
    )

    return unique_tags


def extract_frontmatter_safely(content: str) -> tuple[dict[str, Any], str]:
    """Extract YAML frontmatter from note content with fallback.

    Uses python-frontmatter library with error handling.
    If frontmatter is invalid, returns empty dict and full content.

    Args:
        content: Full markdown content including optional frontmatter.

    Returns:
        Tuple of (frontmatter_dict, content_without_frontmatter).

    Examples:
        >>> content = '''---
        ... title: My Note
        ... tags: [project, review]
        ... ---
        ... Note content here'''
        >>> fm, body = extract_frontmatter_safely(content)
        >>> fm['title']
        'My Note'
        >>> 'Note content here' in body
        True
    """
    try:
        post = frontmatter.loads(content)
        metadata = dict(post.metadata) if post.metadata else {}
        body = post.content

        logger.debug(
            "frontmatter_extracted",
            has_frontmatter=bool(metadata),
            field_count=len(metadata),
        )
    except Exception as e:
        logger.warning(
            "frontmatter_parse_failed",
            error=str(e),
            content_preview=content[:100],
        )
        # Return empty metadata and full content
        metadata = {}
        body = content

    return metadata, body


def parse_frontmatter_tags(frontmatter_dict: dict[str, Any]) -> list[str]:
    """Extract tags from frontmatter, handling multiple formats.

    Frontmatter tags can be:
    - tags: [tag1, tag2]
    - tags: tag1, tag2
    - tag: single-tag

    Args:
        frontmatter_dict: Parsed frontmatter dictionary.

    Returns:
        List of tag strings.
    """
    tags: list[str] = []

    # Check "tags" field (array or comma-separated string)
    if "tags" in frontmatter_dict:
        tags_value = frontmatter_dict["tags"]

        if isinstance(tags_value, list):
            tags.extend(str(tag).strip() for tag in tags_value)
        elif isinstance(tags_value, str):
            # Split by comma or space
            tag_parts = re.split(r"[,\s]+", tags_value)
            tags.extend(tag.strip() for tag in tag_parts if tag.strip())

    # Check "tag" field (single tag)
    if "tag" in frontmatter_dict:
        tag_value = frontmatter_dict["tag"]
        if isinstance(tag_value, str):
            tags.append(tag_value.strip())

    # Remove duplicates while preserving order
    return list(dict.fromkeys(tags))


def get_all_tags(content: str, frontmatter_dict: dict[str, Any]) -> list[str]:
    """Get all tags from both frontmatter and inline content.

    Args:
        content: Note content (body, without frontmatter).
        frontmatter_dict: Parsed frontmatter dictionary.

    Returns:
        Combined list of unique tags from both sources.
    """
    frontmatter_tags = parse_frontmatter_tags(frontmatter_dict)
    inline_tags = extract_inline_tags(content)

    # Combine and deduplicate
    all_tags = frontmatter_tags + inline_tags
    unique_tags = list(dict.fromkeys(all_tags))

    logger.debug(
        "all_tags_extracted",
        frontmatter_tags=len(frontmatter_tags),
        inline_tags=len(inline_tags),
        total_unique=len(unique_tags),
    )

    return unique_tags
