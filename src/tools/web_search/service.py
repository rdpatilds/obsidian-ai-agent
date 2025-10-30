"""Web search service implementation.

This module implements web search using DuckDuckGo HTML interface.
No API key required - uses simple HTML parsing.
"""

import re
from urllib.parse import quote_plus

import httpx

from src.shared.logging import get_logger
from src.tools.web_search.schemas import (
    WebSearchRequest,
    WebSearchResult,
)


logger = get_logger(__name__)


async def search_web(request: WebSearchRequest) -> str:
    """Search the web using DuckDuckGo and return formatted results.

    Args:
        request: Web search request with query and options.

    Returns:
        Formatted search results as a string.

    Raises:
        httpx.HTTPError: If the HTTP request fails.
        ValueError: If response parsing fails.
    """
    logger.info(
        "web_search_started",
        query=request.query,
        max_results=request.max_results,
        response_format=request.response_format,
    )

    try:
        # Perform search
        encoded_query = quote_plus(request.query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            html = response.text

        # Parse results using simple regex
        results = _parse_duckduckgo_html(html, request.max_results)

        logger.info(
            "web_search_completed",
            query=request.query,
            total_found=len(results),
            duration_ms=0,  # Could add timing if needed
        )

        # Format response
        return _format_results(results, request.response_format)

    except httpx.HTTPError as e:
        logger.exception(
            "web_search_http_error",
            query=request.query,
            error=str(e),
        )
        raise
    except Exception as e:
        logger.exception(
            "web_search_failed",
            query=request.query,
            error=str(e),
        )
        raise


def _parse_duckduckgo_html(html: str, max_results: int) -> list[WebSearchResult]:
    """Parse DuckDuckGo HTML to extract search results.

    Args:
        html: HTML content from DuckDuckGo.
        max_results: Maximum number of results to extract.

    Returns:
        List of search results.
    """
    results: list[WebSearchResult] = []

    # Find all result blocks (simplified parsing)
    # DuckDuckGo HTML structure: results are in <div class="result">
    result_pattern = re.compile(
        r'<div class="result[^"]*">.*?'
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        re.DOTALL | re.IGNORECASE,
    )

    matches = result_pattern.findall(html)

    for url, title, snippet in matches[:max_results]:
        # Clean HTML tags from title and snippet
        clean_title = re.sub(r"<[^>]+>", "", title).strip()
        clean_snippet = re.sub(r"<[^>]+>", "", snippet).strip()

        # Decode HTML entities
        clean_title = _decode_html_entities(clean_title)
        clean_snippet = _decode_html_entities(clean_snippet)

        if clean_title and url:
            results.append(
                WebSearchResult(
                    title=clean_title,
                    url=url,
                    snippet=clean_snippet or "No description available",
                )
            )

        if len(results) >= max_results:
            break

    return results


def _decode_html_entities(text: str) -> str:
    """Decode common HTML entities.

    Args:
        text: Text with HTML entities.

    Returns:
        Decoded text.
    """
    # Decode common HTML entities
    replacements = {
        "&amp;": "&",
        "&lt;": "<",
        "&gt;": ">",
        "&quot;": '"',
        "&#39;": "'",
        "&nbsp;": " ",
    }

    for entity, char in replacements.items():
        text = text.replace(entity, char)

    return text


def _format_results(results: list[WebSearchResult], format_type: str) -> str:
    """Format search results based on response format.

    Args:
        results: List of search results.
        format_type: Format type - "minimal", "concise", or "detailed".

    Returns:
        Formatted results string.
    """
    if not results:
        return "No results found."

    formatted_parts: list[str] = [f"Found {len(results)} results:\n"]

    for i, result in enumerate(results, 1):
        if format_type == "minimal":
            # Title + URL only (~30 tokens per result)
            formatted_parts.append(f"{i}. {result.title}")
            formatted_parts.append(f"   {result.url}\n")

        elif format_type == "concise":
            # Title + URL + snippet (truncated to 50 words)
            snippet = _truncate_words(result.snippet, 50)
            formatted_parts.append(f"{i}. {result.title}")
            formatted_parts.append(f"   {result.url}")
            formatted_parts.append(f"   {snippet}\n")

        else:  # detailed
            # Title + URL + full snippet
            formatted_parts.append(f"{i}. {result.title}")
            formatted_parts.append(f"   {result.url}")
            formatted_parts.append(f"   {result.snippet}\n")

    return "\n".join(formatted_parts)


def _truncate_words(text: str, max_words: int) -> str:
    """Truncate text to maximum number of words.

    Args:
        text: Text to truncate.
        max_words: Maximum number of words.

    Returns:
        Truncated text with ellipsis if truncated.
    """
    words = text.split()
    if len(words) <= max_words:
        return text

    return " ".join(words[:max_words]) + "..."
