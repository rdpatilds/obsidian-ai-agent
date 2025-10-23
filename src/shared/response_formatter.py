"""Response formatting utilities for token-efficient agent tool outputs.

This module provides formatters that control output verbosity based on
the response_format parameter, following Anthropic's recommendation for
token efficiency (minimal ~50 tokens, concise ~150 tokens, detailed ~1500+ tokens).
"""

from enum import Enum
from typing import Any

from src.shared.logging import get_logger


logger = get_logger(__name__)


class ResponseFormat(str, Enum):
    """Response format levels for controlling output verbosity and token usage."""

    MINIMAL = "minimal"
    """Title, tags, summary only (~50 tokens). Use for metadata checks or existence verification."""

    CONCISE = "concise"
    """Title, tags, frontmatter, content preview (~150 tokens). Default balanced format."""

    DETAILED = "detailed"
    """Full content with all metadata (~1500+ tokens). Use only when complete content needed."""


def format_note_response(
    note_data: dict[str, Any], format_level: ResponseFormat
) -> dict[str, Any]:
    """Format note data based on response format level.

    This function controls token usage by returning different levels of detail:
    - MINIMAL: ~50 tokens (title, tags, summary)
    - CONCISE: ~150 tokens (+ frontmatter + 100-word preview)
    - DETAILED: ~1500+ tokens (full content)

    Args:
        note_data: Dictionary with keys: title, content, frontmatter, tags, path, etc.
        format_level: ResponseFormat enum controlling verbosity.

    Returns:
        Formatted dictionary with appropriate level of detail.

    Examples:
        >>> note_data = {
        ...     "title": "Project Alpha",
        ...     "content": "Long content...",
        ...     "frontmatter": {"status": "active", "priority": 8},
        ...     "tags": ["project", "2025"],
        ...     "path": "projects/alpha.md"
        ... }
        >>> format_note_response(note_data, ResponseFormat.MINIMAL)
        {
            "title": "Project Alpha",
            "tags": ["project", "2025"],
            "summary": "Long content...",  # First 50 chars
            "path": "projects/alpha.md"
        }
    """
    path = note_data.get("path", "")
    title = note_data.get("title", "Untitled")
    content = note_data.get("content", "")
    frontmatter = note_data.get("frontmatter", {})
    tags = note_data.get("tags", [])

    minimal_char_limit = 50

    if format_level == ResponseFormat.MINIMAL:
        # ~50 tokens: title, tags, first 50 chars
        summary = content[:minimal_char_limit].strip()
        if len(content) > minimal_char_limit:
            summary += "..."

        result = {
            "title": title,
            "tags": tags,
            "summary": summary,
            "path": path,
        }

        logger.debug(
            "note_formatted",
            format="minimal",
            token_estimate=50,
            path=path,
        )
        return result

    concise_word_limit = 100

    if format_level == ResponseFormat.CONCISE:
        # ~150 tokens: title, tags, frontmatter, 100-word preview
        words = content.split()
        preview_words = words[:concise_word_limit]
        preview = " ".join(preview_words)
        if len(words) > concise_word_limit:
            preview += "..."

        result = {
            "title": title,
            "tags": tags,
            "frontmatter": frontmatter,
            "content_preview": preview,
            "path": path,
            "word_count": len(words),
        }

        logger.debug(
            "note_formatted",
            format="concise",
            token_estimate=150,
            path=path,
        )
        return result

    # DETAILED
    # ~1500+ tokens: full content + all metadata
    result = {
        "title": title,
        "tags": tags,
        "frontmatter": frontmatter,
        "content": content,
        "path": path,
        "word_count": len(content.split()),
        "char_count": len(content),
    }

    # Rough token estimate (1 token ≈ 0.75 words)
    token_estimate = int(len(content.split()) * 1.3)

    logger.debug(
        "note_formatted",
        format="detailed",
        token_estimate=token_estimate,
        path=path,
    )
    return result


def format_query_results(
    results: list[dict[str, Any]],
    format_level: ResponseFormat,
    max_results: int = 20,
) -> dict[str, Any]:
    """Format query results with token-efficient output.

    Args:
        results: List of result dictionaries (path, title, content, metadata, etc.).
        format_level: ResponseFormat enum controlling verbosity per result.
        max_results: Maximum number of results to include.

    Returns:
        Dictionary with formatted results and metadata.
    """
    # Truncate to max_results
    truncated = len(results) > max_results
    limited_results = results[:max_results]

    # Format each result
    formatted_results = []
    for result in limited_results:
        formatted = format_note_response(result, format_level)
        formatted_results.append(formatted)

    # Calculate token estimate per format level
    tokens_per_result = {
        ResponseFormat.MINIMAL: 20,
        ResponseFormat.CONCISE: 60,
        ResponseFormat.DETAILED: 300,
    }
    total_tokens = len(formatted_results) * tokens_per_result.get(format_level, 60)

    output = {
        "results": formatted_results,
        "total_found": len(results),
        "returned": len(formatted_results),
        "truncated": truncated,
        "token_estimate": total_tokens,
    }

    logger.debug(
        "query_results_formatted",
        format=format_level.value,
        result_count=len(formatted_results),
        token_estimate=total_tokens,
        truncated=truncated,
    )

    return output


def truncate_with_guidance(
    results: list[Any], limit: int
) -> tuple[list[Any], str]:
    """Truncate results and provide guidance on refining the query.

    Args:
        results: List of results to truncate.
        limit: Maximum number of results to return.

    Returns:
        Tuple of (truncated_results, guidance_message).
    """
    truncated_results = results[:limit]

    if len(results) <= limit:
        return truncated_results, ""

    # Generate helpful guidance message
    overflow_count = len(results) - limit
    guidance = (
        f"Showing {limit} of {len(results)} results ({overflow_count} more available). "
        f"To refine: "
        f"(1) Add more specific search terms, "
        f"(2) Use property_filters to narrow by metadata, "
        f"(3) Use tag_filters to limit by tags, "
        f"or (4) Increase max_results parameter."
    )

    logger.info(
        "results_truncated",
        total_results=len(results),
        returned=limit,
        overflow=overflow_count,
    )

    return truncated_results, guidance


def estimate_tokens(text: str) -> int:
    """Estimate token count for text.

    Uses rough approximation: 1 token ≈ 0.75 words.
    For production, use tiktoken or actual tokenizer.

    Args:
        text: Text to estimate tokens for.

    Returns:
        Estimated token count.
    """
    word_count = len(text.split())
    return int(word_count * 1.3)  # ~1.3 tokens per word
