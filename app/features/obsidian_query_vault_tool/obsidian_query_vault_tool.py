"""Obsidian Query Vault Tool - search and discovery operations."""

from typing import Literal

from pydantic_ai import RunContext

from app.core.agents import AgentDeps, vault_agent
from app.core.logging import get_logger
from app.features.obsidian_query_vault_tool import (
    obsidian_query_vault_tool_service as service,
)
from app.features.obsidian_query_vault_tool.obsidian_query_vault_tool_models import (
    ObsidianQueryVaultToolResult,
    SearchFilters,
)

logger = get_logger(__name__)


@vault_agent.tool
async def obsidian_query_vault_tool(
    ctx: RunContext[AgentDeps],
    query_type: Literal[
        "semantic_search",
        "list_structure",
        "find_related",
        "search_by_metadata",
        "recent_changes",
    ],
    query: str | None = None,
    path: str = "",
    reference_note: str | None = None,
    filters: SearchFilters | None = None,
    limit: int = 10,
    response_format: Literal["detailed", "concise"] = "concise",
) -> ObsidianQueryVaultToolResult:
    """Search and discover notes in the Obsidian vault using natural language queries.

    Use this when you need to:
    - Find notes by content or keywords (semantic search)
    - Explore vault structure and list files
    - Discover notes related to a specific note
    - Filter notes by tags, dates, or metadata
    - Find recently modified notes

    Do NOT use this for:
    - Reading full note content (use obsidian_get_context_tool instead - NOT YET IMPLEMENTED)
    - Modifying notes (use obsidian_vault_manager_tool instead - NOT YET IMPLEMENTED)
    - Just checking if a note exists (use response_format="concise" and limit=1)

    Args:
        query_type: Type of query operation to perform.
            - "semantic_search": Find notes by content relevance (requires query parameter)
                Use when: User asks "find notes about X" or "search for Y"
            - "list_structure": Browse folders and files (optional path parameter)
                Use when: User wants to see vault structure or files in a folder
            - "find_related": Discover connected notes (requires reference_note parameter)
                Use when: User asks "what's related to X" or "similar notes"
            - "search_by_metadata": Filter by tags/dates (requires filters parameter)
                Use when: User specifies tags or time ranges
            - "recent_changes": Get recently modified files
                Use when: User asks "what changed recently" or "recent notes"
        query: Search query string (required for semantic_search).
            Natural language or keywords to search for.
            Examples: "Python programming", "machine learning", "project ideas"
        path: Folder path for list_structure queries (e.g., "Projects/2025").
            Empty string means vault root. Searches recursively.
        reference_note: Note path to find related notes for (e.g., "Architecture.md").
            Required for find_related query_type.
            Must be relative path within vault.
        filters: Metadata filters for search_by_metadata.
            Example: SearchFilters(tags=["urgent"], date_range={"days": 7})
            All filters are optional (any match).
        limit: Maximum number of results to return (1-100).
            Default 10. Use smaller values for quick checks, larger for comprehensive searches.
            Results sorted by relevance for semantic_search.
        response_format: Control output verbosity to manage token usage.
            - "concise": Path, title, relevance only (~50 tokens per result)
              Use for: Large result sets, quick searches, checking existence (DEFAULT)
            - "detailed": Adds excerpt, tags, dates (~200 tokens per result)
              Use for: Detailed analysis, when you need full metadata

    Returns:
        ObsidianQueryVaultToolResult with matching notes and metadata.
        - results: List of NoteInfo objects
        - total_found: Total matches (may exceed limit)
        - truncated: True if more results exist than returned
        - suggestion: Guidance for refining search if truncated

    Performance Notes:
        - Concise format: ~50 tokens per result (recommended for most queries)
        - Detailed format: ~200 tokens per result (use sparingly)
        - Typical execution: <100ms for small vaults (<100 notes)
        - Typical execution: 100-500ms for large vaults (>1000 notes)
        - Results limited to prevent token overflow
        - Always prefer concise over detailed unless user specifically needs metadata

    Examples:
        # Find notes about Python (concise for efficiency)
        obsidian_query_vault_tool(
            query_type="semantic_search",
            query="Python programming",
            limit=5,
            response_format="concise"
        )

        # List all files in Projects folder
        obsidian_query_vault_tool(
            query_type="list_structure",
            path="Projects",
            response_format="detailed"
        )

        # Find notes related to Architecture Decision Record
        obsidian_query_vault_tool(
            query_type="find_related",
            reference_note="Architecture/ADR-001.md",
            limit=10,
            response_format="concise"
        )

        # Find notes tagged 'urgent' from last week
        obsidian_query_vault_tool(
            query_type="search_by_metadata",
            filters=SearchFilters(tags=["urgent"], date_range={"days": 7}),
            response_format="detailed"
        )

        # See recent changes
        obsidian_query_vault_tool(
            query_type="recent_changes",
            limit=20,
            response_format="concise"
        )
    """
    vault_manager = ctx.deps.vault_manager

    logger.info(
        "agent.tool.execution_started",
        tool="obsidian_query_vault_tool",
        query_type=query_type,
        limit=limit,
        response_format=response_format,
    )

    try:
        # Route to appropriate service function based on query_type
        if query_type == "semantic_search":
            if not query:
                raise ValueError("query parameter required for semantic_search")
            result = await service.execute_semantic_search(
                vault_manager, query, limit, response_format
            )
        elif query_type == "list_structure":
            result = await service.execute_list_structure(
                vault_manager, path, limit, response_format
            )
        elif query_type == "find_related":
            if not reference_note:
                raise ValueError("reference_note parameter required for find_related")
            result = await service.execute_find_related(
                vault_manager, reference_note, limit, response_format
            )
        elif query_type == "search_by_metadata":
            if not filters:
                raise ValueError("filters parameter required for search_by_metadata")
            result = await service.execute_search_by_metadata(
                vault_manager, filters, limit, response_format
            )
        elif query_type == "recent_changes":
            result = await service.execute_recent_changes(vault_manager, limit, response_format)
        else:
            raise ValueError(f"Unknown query_type: {query_type}")

        logger.info(
            "agent.tool.execution_completed",
            tool="obsidian_query_vault_tool",
            query_type=query_type,
            result_count=len(result.results),
            truncated=result.truncated,
        )

        return result

    except Exception as e:
        logger.error(
            "agent.tool.execution_failed",
            tool="obsidian_query_vault_tool",
            query_type=query_type,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
