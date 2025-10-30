"""Tool registration for web search.

This module registers the web search tool with the agent,
providing web search capabilities using DuckDuckGo.
"""

from typing import TYPE_CHECKING

from pydantic_ai import RunContext

from src.agent.schemas import AgentDependencies
from src.shared.logging import get_logger
from src.tools.web_search.schemas import WebSearchRequest
from src.tools.web_search.service import search_web


if TYPE_CHECKING:
    from pydantic_ai import Agent

logger = get_logger(__name__)


def register_web_search_tool(
    agent: "Agent[AgentDependencies, str]",
) -> None:
    """Register the web_search tool with the agent.

    Args:
        agent: Pydantic AI agent instance to register tool with.
    """

    @agent.tool
    async def web_search(
        ctx: RunContext["AgentDependencies"],  # noqa: ARG001
        query: str,
        max_results: int = 5,
        response_format: str = "concise",
    ) -> str:
        """Search the web for information using DuckDuckGo.

        Use this when you need to:
        - Find current information not in your knowledge base
        - Look up recent news, events, or developments
        - Research factual information from the internet
        - Get multiple perspectives on a topic
        - Find external resources or documentation

        Do NOT use this for:
        - Searching the Obsidian vault (use obsidian_vault_query instead)
        - Reading specific notes (use obsidian_note_manage instead)
        - Analyzing note relationships (use obsidian_graph_analyze instead)
        - Information you already know with high confidence

        Args:
            query: Search query string. Be specific for better results.
                Examples: "Python async best practices 2025", "climate change latest research"
            max_results: Number of results to return (1-10).
                - Small (1-3): Quick fact checking, single answer needed
                - Medium (4-6): Balanced search, multiple perspectives (DEFAULT)
                - Large (7-10): Comprehensive research, gathering many sources
            response_format: Control output verbosity and token usage.
                - "minimal": Title + URL only (~30 tokens per result, ~150 total for 5 results)
                    Use when: Just need links to share or quickly scan options
                - "concise": Title + URL + 50-word snippet (~100 tokens per result, ~500 total)
                    Use when: Need brief context to evaluate relevance (DEFAULT)
                - "detailed": Title + URL + full snippet (~200 tokens per result, ~1000+ total)
                    Use when: Need comprehensive information to answer complex questions

        Returns:
            Formatted search results as a string.
            Format varies by response_format:
            - minimal: Numbered list with title and URL
            - concise: Numbered list with title, URL, and brief snippet
            - detailed: Numbered list with title, URL, and full snippet

        Performance Notes:
            - Minimal format: ~30 tokens/result (~150 for 5 results)
            - Concise format: ~100 tokens/result (~500 for 5 results, recommended)
            - Detailed format: ~200 tokens/result (~1000+ for 5 results)
            - Typical execution time: 1-3 seconds for network request
            - Max results: 10 (returns fewer if not enough results found)
            - No API key required (uses DuckDuckGo HTML)

        Examples:
            # Quick fact check with minimal output
            web_search(
                query="Python 3.12 release date",
                max_results=3,
                response_format="minimal"
            )

            # Research topic with balanced detail (default)
            web_search(
                query="machine learning explainability techniques",
                max_results=5,
                response_format="concise"
            )

            # Comprehensive research with full context
            web_search(
                query="best practices for API design REST vs GraphQL",
                max_results=7,
                response_format="detailed"
            )

            # Quick news check
            web_search(
                query="latest developments in quantum computing 2025",
                max_results=5
            )
        """
        logger.info(
            "tool_execution_started",
            tool="web_search",
            query=query,
            max_results=max_results,
            response_format=response_format,
        )

        try:
            request = WebSearchRequest(
                query=query,
                max_results=max_results,
                response_format=response_format,
            )

            result = await search_web(request)

            logger.info(
                "tool_execution_completed",
                tool="web_search",
                query=query,
            )

            return result

        except Exception as e:
            logger.exception(
                "tool_execution_failed",
                tool="web_search",
                query=query,
                error=str(e),
            )
            return f"Web search failed: {e!s}"

    logger.info("web_search_tool_registered")
