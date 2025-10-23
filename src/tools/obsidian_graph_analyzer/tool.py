"""Tool registration for Obsidian Graph Analyzer."""

import json
from typing import TYPE_CHECKING

from pydantic_ai import RunContext

from src.agent.schemas import AgentDependencies
from src.shared.logging import get_logger
from src.tools.obsidian_graph_analyzer.schemas import GraphAnalysisRequest
from src.tools.obsidian_graph_analyzer.service import analyze_graph_service


if TYPE_CHECKING:
    from pydantic_ai import Agent

logger = get_logger(__name__)


def register_obsidian_graph_analyzer_tool(
    agent: "Agent[AgentDependencies, str]",
) -> None:
    """Register the obsidian_graph_analyze tool with the agent.

    Args:
        agent: Pydantic AI agent instance to register tool with.
    """

    @agent.tool
    async def obsidian_graph_analyze(
        ctx: RunContext["AgentDependencies"],
        center_note: str,
        depth: int = 1,
        include_content_preview: bool = True,
        filter_tags: str | None = None,
        response_format: str = "concise",
    ) -> str:
        """Analyze knowledge graph relationships and note connections.

        Use this when you need to:
        - Understand how notes are connected via wikilinks
        - Find all notes linked FROM a specific note (outbound links)
        - Find all notes that link TO a specific note (backlinks/inbound links)
        - Explore the neighborhood of related notes around a central concept
        - Map out the knowledge graph in a specific area

        Do NOT use this for:
        - Finding notes by content (use obsidian_vault_query instead)
        - Reading a single note (use obsidian_note_manage instead)
        - Searching by tags (use obsidian_vault_query mode="tags" instead)

        Args:
            center_note: Path to the note at the center of analysis.
                Example: "projects/alpha.md", "concepts/machine-learning.md"

            depth: How many hops to traverse from center (1-3).
                - depth=1: Only immediate neighbors (notes directly linked)
                - depth=2: Neighbors + their neighbors (2 hops away)
                - depth=3: Extended network (3 hops)
                WARNING: Depth 2+ can return MANY nodes exponentially.
                Start with depth=1, only increase if needed.

            include_content_preview: Include 50-word preview for each node.
                Set to False to reduce tokens if you only need link structure.

            filter_tags: JSON list of tags to filter traversal.
                Example: '["project", "active"]'
                Only traverses notes with at least one of these tags.

            response_format: Output verbosity (not heavily used for graph).
                - "minimal": Just node titles and links
                - "concise": Add tags and previews (default)
                - "detailed": Full metadata

        Returns:
            Formatted graph structure with nodes and relationships.

        Performance Notes:
            - Depth 1: ~5-20 nodes typically (~300 tokens)
            - Depth 2: ~20-50 nodes typically (~1000 tokens)
            - Depth 3: ~50-100 nodes (may hit limit) (~2000+ tokens)
            - Max nodes: 100 (prevents explosion)
            - Typical execution: 100-500ms depending on graph size

        Examples:
            # Find immediate neighbors of a note
            obsidian_graph_analyze(
                center_note="concepts/machine-learning.md",
                depth=1,
                response_format="concise"
            )

            # Explore extended network around a project
            obsidian_graph_analyze(
                center_note="projects/website-redesign.md",
                depth=2,
                include_content_preview=False  # Just structure, save tokens
            )

            # Analyze graph filtered by tags
            obsidian_graph_analyze(
                center_note="overview.md",
                depth=2,
                filter_tags='["project", "active"]'
            )

            # Find backlinks (notes linking TO this note)
            obsidian_graph_analyze(
                center_note="concepts/core-idea.md",
                depth=1
            )
            # Look at inbound_links in result for backlinks
        """
        # Parse filter_tags
        filter_tags_list: list[str] | None = None
        if filter_tags:
            try:
                filter_tags_list = json.loads(filter_tags)
                if not isinstance(filter_tags_list, list):
                    return "filter_tags must be a JSON array of tag strings"
            except json.JSONDecodeError as e:
                return f"Invalid JSON in filter_tags: {e}"

        # Create request
        try:
            request = GraphAnalysisRequest(
                center_note=center_note,
                depth=depth,
                include_content_preview=include_content_preview,
                filter_tags=filter_tags_list,
                response_format=response_format,  # type: ignore[arg-type]
            )
        except Exception as e:
            logger.exception("invalid_graph_request", error=str(e))
            return f"Invalid request: {e}"

        # Execute analysis
        try:
            result = await analyze_graph_service(
                request=request,
                vault_path=ctx.deps.vault_path,
            )

            # Format response
            response_parts = [
                f"Graph Analysis: {result.center_note}",
                f"Total nodes: {result.total_nodes}",
                f"Max depth reached: {result.depth_reached}",
            ]

            if result.truncated:
                response_parts.append(
                    "⚠️  Graph truncated at 100 nodes. Consider narrowing depth or using filter_tags."
                )

            # Group nodes by depth
            from src.tools.obsidian_graph_analyzer.schemas import GraphNode
            nodes_by_depth: dict[int, list[GraphNode]] = {}
            for node in result.nodes:
                if node.depth not in nodes_by_depth:
                    nodes_by_depth[node.depth] = []
                nodes_by_depth[node.depth].append(node)

            # Display nodes by depth level
            for current_depth in sorted(nodes_by_depth.keys()):
                nodes_at_depth = nodes_by_depth[current_depth]
                response_parts.append(f"\n--- Depth {current_depth} ({len(nodes_at_depth)} nodes) ---")

                for node in nodes_at_depth:
                    node_info = f"\n• {node.title} ({node.path})"

                    if node.tags:
                        node_info += f"\n  Tags: {', '.join(node.tags[:5])}"

                    if node.outbound_links:
                        node_info += f"\n  Links to: {len(node.outbound_links)} notes"

                    if node.inbound_links:
                        node_info += f"\n  Linked from: {len(node.inbound_links)} notes"

                    if include_content_preview and node.content_preview:
                        node_info += f"\n  Preview: {node.content_preview[:100]}"

                    response_parts.append(node_info)

            # Token estimate
            token_estimate = result.total_nodes * (
                100 if include_content_preview else 50
            )
            response_parts.append(f"\n(~{token_estimate} tokens)")

            return "\n".join(response_parts)

        except FileNotFoundError:
            return f"Center note not found: {center_note}"
        except Exception as e:
            logger.exception(
                "graph_analysis_failed",
                center_note=center_note,
                depth=depth,
            )
            return f"Graph analysis failed: {e}"

    logger.info("tool_registered", tool="obsidian_graph_analyze")
