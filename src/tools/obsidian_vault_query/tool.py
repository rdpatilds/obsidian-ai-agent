"""Tool registration for Obsidian Vault Query."""

import json
from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext

from src.agent.schemas import AgentDependencies
from src.shared.logging import get_logger
from src.tools.obsidian_vault_query.schemas import QueryMode, QueryRequest
from src.tools.obsidian_vault_query.service import query_vault_service


if TYPE_CHECKING:
    from pydantic_ai import Agent

logger = get_logger(__name__)


def register_obsidian_vault_query_tool(
    agent: "Agent[AgentDependencies, str]",
) -> None:
    """Register the obsidian_vault_query tool with the agent.

    Args:
        agent: Pydantic AI agent instance to register tool with.
    """

    @agent.tool
    async def obsidian_vault_query(
        ctx: RunContext["AgentDependencies"],
        query: str,
        mode: str = "fulltext",
        property_filters: str | None = None,
        tag_filters: str | None = None,
        case_sensitive: bool = False,
        max_results: int = 20,
        response_format: str = "concise",
    ) -> str:
        """Search and query the Obsidian vault across multiple dimensions.

        Use this when you need to:
        - Find notes containing specific text (full-text search)
        - Filter notes by metadata properties (status=active, priority>5)
        - Find notes with specific tags (#project, #review)
        - Discover notes matching certain criteria

        Do NOT use this for:
        - Reading a single known note (use obsidian_note_manage instead)
        - Analyzing relationships between notes (use obsidian_graph_analyze instead)
        - Modifying notes (use obsidian_note_manage or obsidian_vault_organize)

        Tool Orchestration Patterns (Use This FIRST):

        Pattern 1: Discovery → Read
            # User: "Read the project-alpha note"
            Step 1: obsidian_vault_query(query="project-alpha", mode="fulltext")
                    → Returns path: "projects/project-alpha.md"
            Step 2: obsidian_note_manage(path="projects/project-alpha.md", operation="read")
            Total: 2 calls ✅

        Pattern 2: Discovery → Batch Action
            # User: "Archive all completed projects"
            Step 1: obsidian_vault_query(mode="properties", property_filters='{"status": "completed"}')
                    → Returns: ["projects/old-1.md", "projects/old-2.md"]
            Step 2: obsidian_vault_organize(notes=[paths], operation="archive")
            Total: 2 calls ✅

        Pattern 3: Discovery → Graph Analysis
            # User: "Analyze connections around the AI safety note"
            Step 1: obsidian_vault_query(query="AI safety", mode="fulltext")
                    → Returns path: "research/ai-safety.md"
            Step 2: obsidian_graph_analyze(center_note="research/ai-safety.md", depth=2)
            Total: 2 calls ✅

        Key Principle: SEARCH FIRST, ACT SECOND
        - Use this tool to discover paths
        - Don't skip discovery step when path is unknown
        - One search is better than multiple failed attempts

        Args:
            query: Search query or filter criteria.
                For fulltext: text to search for
                For tags: can be empty (uses tag_filters)
                For properties: can be empty (uses property_filters)

            mode: Query type - "fulltext", "properties", "tags", or "dataview"
                - "fulltext": Search content for text matches (default)
                - "properties": Filter by frontmatter metadata
                - "tags": Filter by tags (frontmatter or inline)
                - "dataview": Execute DQL queries (basic support)

            property_filters: For properties mode, JSON dict of filters.
                Example: '{"status": "active", "priority": {"$gt": 5}}'
                Operators: $gt, $gte, $lt, $lte, $eq, $ne

            tag_filters: For tags mode, JSON list of tags.
                Example: '["project", "review"]'
                Matches notes with ANY of the listed tags (OR logic)

            case_sensitive: For fulltext mode, case-sensitive search.

            max_results: Maximum results to return (1-100), default 20.

            response_format: Output verbosity.
                - "minimal": Just paths and titles (~20 tokens per result)
                - "concise": Paths, titles, excerpts (~60 tokens per result)
                - "detailed": Full metadata and content (~300+ tokens per result)

        Returns:
            Formatted string with search results and metadata.

        Performance Notes:
            - Minimal format: ~20 tokens/result (use for browsing)
            - Concise format: ~60 tokens/result (default, good balance)
            - Detailed format: ~300+ tokens/result (use sparingly)
            - Full-text search of 1000 notes: ~500ms
            - Property filtering: ~200ms (faster than full-text)

        Examples:
            # Find notes mentioning "machine learning"
            obsidian_vault_query(
                query="machine learning",
                mode="fulltext",
                max_results=10,
                response_format="concise"
            )

            # Find active high-priority tasks
            obsidian_vault_query(
                query="",
                mode="properties",
                property_filters='{"status": "active", "priority": {"$gte": 8}}',
                response_format="minimal"
            )

            # Find all project notes
            obsidian_vault_query(
                query="",
                mode="tags",
                tag_filters='["project"]',
                response_format="concise"
            )

            # Find notes with either "review" or "todo" tags
            obsidian_vault_query(
                query="",
                mode="tags",
                tag_filters='["review", "todo"]',
                response_format="minimal"
            )

            # Case-sensitive search
            obsidian_vault_query(
                query="API",
                mode="fulltext",
                case_sensitive=True
            )
        """
        # Validate mode
        try:
            query_mode = QueryMode(mode)
        except ValueError:
            return f"Invalid mode: {mode}. Must be one of: fulltext, properties, tags, dataview"

        # Parse JSON parameters
        property_filters_dict: dict[str, Any] | None = None
        if property_filters:
            try:
                property_filters_dict = json.loads(property_filters)
            except json.JSONDecodeError as e:
                return f"Invalid JSON in property_filters: {e}"

        tag_filters_list: list[str] | None = None
        if tag_filters:
            try:
                tag_filters_list = json.loads(tag_filters)
                if not isinstance(tag_filters_list, list):
                    return "tag_filters must be a JSON array of tag strings"
            except json.JSONDecodeError as e:
                return f"Invalid JSON in tag_filters: {e}"

        # Create request
        try:
            request = QueryRequest(
                query=query,
                mode=query_mode,
                property_filters=property_filters_dict,
                tag_filters=tag_filters_list,
                case_sensitive=case_sensitive,
                max_results=max_results,
                response_format=response_format,  # type: ignore[arg-type]
            )
        except Exception as e:
            logger.exception("invalid_query_request", error=str(e))
            return f"Invalid request: {e}"

        # Execute query
        try:
            result = await query_vault_service(
                request=request,
                vault_path=ctx.deps.vault_path,
            )

            # Format response
            if not result.results:
                response = f"No results found for query: {query}\n"
                if result.guidance_message:
                    response += f"\n{result.guidance_message}"
                return response

            response_parts = [
                f"Found {result.total_found} notes (showing {len(result.results)})",
                f"Mode: {result.mode.value}",
            ]

            if result.truncated and result.guidance_message:
                response_parts.append(f"\n{result.guidance_message}")

            response_parts.append("\nResults:")

            for idx, note_result in enumerate(result.results, 1):
                response_parts.append(f"\n{idx}. {note_result.title} ({note_result.path})")

                if note_result.match_count:
                    response_parts.append(f"   Matches: {note_result.match_count}")

                if note_result.excerpt:
                    response_parts.append(f"   {note_result.excerpt}")

                # Include metadata for detailed format
                if response_format == "detailed" and note_result.metadata:
                    metadata_preview = str(note_result.metadata)[:200]
                    response_parts.append(f"   Metadata: {metadata_preview}...")

            # Token estimate
            token_estimate = len(result.results) * {
                "minimal": 20,
                "concise": 60,
                "detailed": 300,
            }.get(response_format, 60)

            response_parts.append(f"\n(~{token_estimate} tokens)")

            return "\n".join(response_parts)

        except Exception as e:
            logger.exception("vault_query_failed", query=query, mode=mode)
            return f"Query failed: {e}"

    logger.info("tool_registered", tool="obsidian_vault_query")
