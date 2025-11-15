"""Brave Web Search Tool - search the web for current information and research."""

from typing import Literal

from pydantic_ai import RunContext

from app.core.agents import AgentDeps, vault_agent
from app.core.logging import get_logger
from app.features.brave_web_search_tool import brave_web_search_tool_service as service
from app.features.brave_web_search_tool.brave_web_search_tool_models import (
    BraveWebSearchToolResult,
)

logger = get_logger(__name__)


@vault_agent.tool
async def brave_web_search_tool(
    ctx: RunContext[AgentDeps],
    query: str,
    count: int = 10,
    safesearch: Literal["off", "moderate", "strict"] = "moderate",
) -> BraveWebSearchToolResult:
    """Search the web using Brave Search API for current information and research.

    Use this when you need to:
    - Find current events or recent information not available in the vault
    - Fact-check claims against authoritative web sources
    - Research topics requiring up-to-date information (news, technology, science)
    - Gather external references and sources for note creation
    - Look up definitions, explanations, or documentation from the web

    Do NOT use this for:
    - Searching vault notes or content (use obsidian_query_vault_tool instead)
    - Reading existing notes in the vault (use obsidian_get_context_tool instead)
    - Finding local files or folders (use obsidian_query_vault_tool with list_structure)
    - Information that should already be in the vault (search vault first)

    Args:
        query: Natural language search query (max 400 chars, auto-truncated if longer).
            Be specific and use relevant keywords for best results.
            Examples:
            - "latest Python 3.12 features and improvements"
            - "climate change research findings 2025"
            - "FastAPI async database best practices"
            - "Obsidian plugin development tutorial"
        count: Number of results to return (1-20, default 10).
            - Use 3-5 for quick lookups and fact-checking
            - Use 10 (default) for balanced research
            - Use 15-20 for comprehensive topic exploration
            Results are automatically clamped to valid range.
        safesearch: Filter explicit content from results.
            - "moderate" (default): Filter explicit adult content, good for general use
            - "strict": Strictest filtering, use for sensitive topics or educational contexts
            - "off": No filtering, use only when researching topics that may require it

    Returns:
        BraveWebSearchToolResult containing:
        - results: List of SearchResult objects with title, url, snippet, page_age
        - query: The search query used (may be truncated from input)
        - total_found: Total estimated matches (may exceed returned count)

    Performance Notes:
        - API call latency: 200-500ms typical for US queries
        - Token cost: ~100-200 tokens per result (title + snippet + url)
        - Total response tokens: ~1,000-2,000 for count=10
        - Rate limits: Free tier allows 1 request/second, 2,000 requests/month
        - Cost: Free tier 2K searches/month, see https://brave.com/search/api/ for pricing
        - The API automatically returns the most relevant results first

    Examples:
        # Quick fact check on recent technology
        brave_web_search_tool(
            query="Python 3.12 release date and new features",
            count=5,
            safesearch="moderate"
        )

        # Comprehensive research on a topic
        brave_web_search_tool(
            query="machine learning best practices for production systems",
            count=15,
            safesearch="moderate"
        )

        # Current news and events
        brave_web_search_tool(
            query="latest developments in AI safety research 2025",
            count=10,
            safesearch="moderate"
        )

        # Technical documentation lookup
        brave_web_search_tool(
            query="FastAPI background tasks documentation",
            count=3,
            safesearch="off"
        )
    """
    settings = ctx.deps.settings

    logger.info(
        "agent.tool.execution_started",
        tool="brave_web_search_tool",
        query=query,
        count=count,
        safesearch=safesearch,
    )

    try:
        result = await service.execute_web_search(
            settings=settings,
            query=query,
            count=count,
            safesearch=safesearch,
        )

        logger.info(
            "agent.tool.execution_completed",
            tool="brave_web_search_tool",
            result_count=len(result.results),
            total_found=result.total_found,
        )

        return result

    except Exception as e:
        logger.error(
            "agent.tool.execution_failed",
            tool="brave_web_search_tool",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
