"""Business logic for Brave Web Search Tool."""

from typing import Literal

from brave_search_client import BraveSearchClient  # type: ignore[import-untyped]

from app.core.config import Settings
from app.core.logging import get_logger
from app.features.brave_web_search_tool.brave_web_search_tool_models import (
    BraveWebSearchToolResult,
    SearchResult,
)

logger = get_logger(__name__)


async def execute_web_search(
    settings: Settings,
    query: str,
    count: int,
    safesearch: Literal["off", "moderate", "strict"],
) -> BraveWebSearchToolResult:
    """Execute web search using Brave Search API.

    Args:
        settings: Application settings with brave_api_key.
        query: Search query string.
        count: Number of results to return (1-20).
        safesearch: Safe search filter level.

    Returns:
        BraveWebSearchToolResult with search results.

    Raises:
        ValueError: If query is empty or invalid.
        Exception: If API request fails.
    """
    logger.info("brave.search_started", query=query, count=count, safesearch=safesearch)

    # Validate inputs
    if not query or len(query.strip()) == 0:
        logger.error("brave.search_failed", error="query cannot be empty")
        raise ValueError("query cannot be empty")

    # Truncate query if too long (Brave API max is 400 chars)
    if len(query) > 400:
        logger.warning("brave.query_truncated", original_length=len(query), truncated_to=400)
        query = query[:400]

    # Clamp count to valid range (1-20)
    count = max(1, min(20, count))

    try:
        # Initialize Brave Search client
        client = BraveSearchClient(api_key=settings.brave_api_key)

        # Execute search - the client supports both sync and async
        # For consistency with our async architecture, we'll use it synchronously
        # but in an async function context
        response = client.search(q=query, count=count, safesearch=safesearch)

        # Parse results
        results: list[SearchResult] = []
        if hasattr(response, "web") and hasattr(response.web, "results"):
            for item in response.web.results:
                results.append(
                    SearchResult(
                        title=item.title,
                        url=item.url,
                        snippet=getattr(item, "description", None),
                        page_age=getattr(item, "page_age", None),
                    )
                )

        total_found = len(results)
        if hasattr(response, "web") and hasattr(response.web, "total_estimated_matches"):
            total_found = response.web.total_estimated_matches

        logger.info(
            "brave.search_completed",
            result_count=len(results),
            total_found=total_found,
        )

        return BraveWebSearchToolResult(
            results=results,
            query=query,
            total_found=total_found,
        )

    except Exception as e:
        logger.error(
            "brave.search_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
