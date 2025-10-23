"""Service layer for Obsidian Graph Analyzer tool."""

import time
from collections import deque
from pathlib import Path

import aiofiles  # type: ignore[import-untyped]

from src.shared.logging import get_logger
from src.shared.obsidian_parsers import (
    extract_frontmatter_safely,
    extract_wikilinks,
    get_all_tags,
)
from src.shared.vault_security import is_path_allowed, validate_vault_path
from src.tools.obsidian_graph_analyzer.schemas import (
    GraphAnalysisRequest,
    GraphAnalysisResponse,
    GraphNode,
)


logger = get_logger(__name__)

MAX_NODES = 100  # Prevent graph explosion


async def analyze_graph_service(
    request: GraphAnalysisRequest,
    vault_path: str,
) -> GraphAnalysisResponse:
    """Analyze knowledge graph starting from center note.

    Uses breadth-first search (BFS) to traverse the graph to specified depth.

    Args:
        request: GraphAnalysisRequest with center note and traversal options.
        vault_path: Absolute path to Obsidian vault root.

    Returns:
        GraphAnalysisResponse with graph nodes and relationships.

    Raises:
        FileNotFoundError: If center note doesn't exist.
    """
    start_time = time.perf_counter()
    vault_root = Path(vault_path)

    # Validate center note
    center_path_str = validate_vault_path(vault_path, request.center_note)
    center_path = Path(center_path_str)

    if not center_path.exists():
        msg = f"Center note not found: {request.center_note}"
        raise FileNotFoundError(msg)

    logger.info(
        "graph_analysis_started",
        center_note=request.center_note,
        depth=request.depth,
        max_nodes=MAX_NODES,
    )

    # BFS traversal
    nodes_dict: dict[str, GraphNode] = {}
    visited: set[str] = set()
    queue: deque[tuple[str, int]] = deque([(request.center_note, 0)])

    while queue and len(nodes_dict) < MAX_NODES:
        current_path, current_depth = queue.popleft()

        if current_path in visited:
            continue

        if current_depth > request.depth:
            continue

        visited.add(current_path)

        # Read note
        try:
            full_path_str = validate_vault_path(vault_path, current_path)
            full_path = Path(full_path_str)

            if not full_path.exists():
                logger.warning("graph_note_not_found", path=current_path)
                continue

            async with aiofiles.open(full_path, encoding="utf-8") as f:
                content = await f.read()

            metadata, body = extract_frontmatter_safely(content)
            tags = get_all_tags(body, metadata)

            # Apply tag filter
            if request.filter_tags:
                if not any(tag in tags for tag in request.filter_tags):
                    continue

            # Extract wikilinks
            wikilinks = extract_wikilinks(content)
            outbound_targets = []

            for link in wikilinks:
                if link.is_embed:
                    continue

                # Resolve wikilink to path
                target_path = _resolve_wikilink(link.target, vault_root)
                if target_path:
                    outbound_targets.append(target_path)

                    # Add to queue for further exploration
                    if current_depth < request.depth:
                        queue.append((target_path, current_depth + 1))

            # Create node
            content_preview = None
            if request.include_content_preview:
                words = body.split()[:50]
                content_preview = " ".join(words)
                if len(body.split()) > 50:
                    content_preview += "..."

            node = GraphNode(
                path=current_path,
                title=full_path.stem,
                tags=tags,
                outbound_links=outbound_targets,
                inbound_links=[],  # Will be populated in second pass
                content_preview=content_preview,
                depth=current_depth,
            )

            nodes_dict[current_path] = node

        except Exception as e:
            logger.warning(
                "graph_node_read_failed",
                path=current_path,
                error=str(e),
            )
            continue

    # Second pass: build inbound links
    for node in nodes_dict.values():
        for outbound_path in node.outbound_links:
            if outbound_path in nodes_dict:
                nodes_dict[outbound_path].inbound_links.append(node.path)

    nodes_list = list(nodes_dict.values())
    max_depth = max((n.depth for n in nodes_list), default=0)
    truncated = len(nodes_list) >= MAX_NODES

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "graph_analysis_completed",
        center_note=request.center_note,
        total_nodes=len(nodes_list),
        depth_reached=max_depth,
        truncated=truncated,
        duration_ms=duration_ms,
    )

    return GraphAnalysisResponse(
        center_note=request.center_note,
        nodes=nodes_list,
        total_nodes=len(nodes_list),
        depth_reached=max_depth,
        truncated=truncated,
    )


def _resolve_wikilink(target: str, vault_root: Path) -> str | None:
    """Resolve wikilink target to note path.

    Args:
        target: Wikilink target (e.g., "Project Alpha" or "folder/note")
        vault_root: Vault root path.

    Returns:
        Relative note path if found, None otherwise.
    """
    # Try direct path with .md extension
    candidates = [
        f"{target}.md",
        f"{target}",
    ]

    # Also try searching by filename
    target_filename = target.split("/")[-1]  # Get last part if path
    if target_filename:
        candidates.append(f"{target_filename}.md")

    for candidate in candidates:
        candidate_path = vault_root / candidate

        if candidate_path.exists() and is_path_allowed(str(candidate_path)):
            try:
                relative_path = str(candidate_path.relative_to(vault_root))
                return relative_path
            except ValueError:
                continue

    # Search vault for matching filename
    target_stem = target_filename.replace(".md", "")
    for note_path in vault_root.rglob("*.md"):
        if note_path.stem == target_stem and is_path_allowed(str(note_path)):
            try:
                return str(note_path.relative_to(vault_root))
            except ValueError:
                continue

    return None
