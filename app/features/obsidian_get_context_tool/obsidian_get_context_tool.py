"""Obsidian Get Context Tool - read full note content with context."""

from typing import Literal

from pydantic_ai import RunContext

from app.core.agents import AgentDeps, vault_agent
from app.core.logging import get_logger
from app.features.obsidian_get_context_tool import (
    obsidian_get_context_tool_service as service,
)
from app.features.obsidian_get_context_tool.obsidian_get_context_tool_models import (
    ObsidianGetContextToolResult,
)

logger = get_logger(__name__)


@vault_agent.tool
async def obsidian_get_context_tool(
    ctx: RunContext[AgentDeps],
    context_type: Literal[
        "read_note", "read_multiple", "gather_related", "daily_note", "note_with_backlinks"
    ],
    target: str | None = None,
    targets: list[str] | None = None,
    date: str | None = None,
    max_related: int = 3,
    response_format: Literal["detailed", "concise"] = "detailed",
) -> ObsidianGetContextToolResult:
    """Retrieve full note content with optional context for synthesis and analysis.

    Use this when you need to:
    - Read complete note content (not just summaries) for detailed analysis
    - Gather multiple related notes together for comparison or synthesis
    - Discover and read all notes that link to a specific note (backlinks)
    - Access daily notes for journaling workflows
    - Understand relationships and connections between notes
    - Get full context including metadata, frontmatter, and surrounding notes

    Do NOT use this for:
    - Finding or searching notes (use obsidian_query_vault_tool first to discover)
    - Checking if a note exists (use obsidian_query_vault_tool with concise format)
    - Modifying or creating notes (use obsidian_vault_manager_tool instead)
    - Quick summaries (use obsidian_query_vault_tool which returns excerpts)

    Args:
        context_type: Type of reading operation to perform.
            - "read_note": Read a single note with full content
                Use when: User wants to read/view/see complete note content
                Required params: target
                Token cost: ~1500+ tokens per note
            - "read_multiple": Read multiple notes in batch
                Use when: User wants to read several specific notes together
                Required params: targets (list of paths)
                Token cost: ~1500+ tokens per note (can be expensive)
            - "gather_related": Read note plus automatically discovered related notes
                Use when: User wants context around a note, understand connections
                Required params: target, optional max_related
                Token cost: ~1500+ tokens per note * (1 + max_related)
            - "daily_note": Get daily note for today or specific date
                Use when: User asks for daily note, journal entry, today's note
                Optional params: date (ISO format "YYYY-MM-DD" or "today")
                Token cost: ~1500+ tokens
            - "note_with_backlinks": Read note with all notes that link to it
                Use when: User wants to see what references a note
                Required params: target
                Token cost: ~1500+ tokens per note (primary + all linking notes)
        target: Relative path to single note (e.g., "Projects/ML.md").
            Required for: read_note, gather_related, note_with_backlinks
            Must be valid path within vault, including .md extension.
            WHY: Specifies which note to read and build context around.
        targets: List of note paths to read together (e.g., ["Ideas.md", "Projects/ML.md"]).
            Required for: read_multiple
            First note becomes primary_note, rest become related_notes.
            WHY: Allows batch reading of specific notes for comparison.
        date: Date for daily note (ISO format "YYYY-MM-DD" or "today").
            Optional for: daily_note (defaults to today if not provided)
            WHY: Specifies which daily note to retrieve.
            Examples: "2025-01-15", "today"
        max_related: Maximum number of related notes to include (1-10).
            Used by: gather_related
            Default: 3 (balance between context and token cost)
            WHY: Controls token usage - more related = more tokens (~1500 each)
        response_format: Control output detail level to manage token usage.
            - "detailed": Include full metadata, frontmatter, tags, dates (DEFAULT)
              Use for: Complete analysis, when you need all available information
              Token cost: Full metadata included (~50-200 extra tokens per note)
            - "concise": Just path, title, content, word count (no metadata)
              Use for: Quick reading when metadata not needed
              Token cost: Minimal overhead

    Returns:
        ObsidianGetContextToolResult with full content and optional context.
        - primary_note: NoteContent with path, title, content, metadata, word_count
        - related_notes: List[NoteContent] for gather_related, read_multiple, note_with_backlinks
        - backlinks: List[BacklinkInfo] with linking notes and context (note_with_backlinks only)
        - token_estimate: Approximate tokens in response (~4 chars per token)

    Performance Notes:
        - Token-heavy operation: ~1500+ tokens per full note (vs ~50-200 for query tool)
        - Always use obsidian_query_vault_tool FIRST to find notes, THEN this tool to read
        - Workflow: discover (query_tool concise ~50 tokens) → read (context_tool ~1500+ tokens)
        - Daily note searches 4 common paths: Daily/, daily/, root, Journal/
        - Backlink discovery scans entire vault (O(n)) - acceptable for <1000 notes
        - Typical execution: read_note <200ms, gather_related/backlinks <1s
        - Default "detailed" format includes all metadata (opposite of query_tool)
        - Use concise format to save ~50-200 tokens per note if metadata not needed

    Examples:
        # Read complete note after finding it with query_tool
        obsidian_get_context_tool(
            context_type="read_note",
            target="Projects/ML-Research.md",
            response_format="detailed"
        )

        # Read multiple notes together for comparison
        obsidian_get_context_tool(
            context_type="read_multiple",
            targets=["Ideas/Feature-A.md", "Ideas/Feature-B.md", "Projects/Roadmap.md"],
            response_format="detailed"
        )

        # Get note with related context for synthesis
        obsidian_get_context_tool(
            context_type="gather_related",
            target="Architecture/System-Design.md",
            max_related=5,
            response_format="detailed"
        )

        # Get today's daily note
        obsidian_get_context_tool(
            context_type="daily_note",
            date="today",
            response_format="detailed"
        )

        # Get specific date's daily note
        obsidian_get_context_tool(
            context_type="daily_note",
            date="2025-01-15",
            response_format="detailed"
        )

        # See what notes link to this one
        obsidian_get_context_tool(
            context_type="note_with_backlinks",
            target="Concepts/Knowledge-Graph.md",
            response_format="detailed"
        )
    """
    vault_manager = ctx.deps.vault_manager

    logger.info(
        "agent.tool.execution_started",
        tool="obsidian_get_context_tool",
        context_type=context_type,
        target=target,
        response_format=response_format,
    )

    try:
        # Route to appropriate service function based on context_type
        if context_type == "read_note":
            if not target:
                raise ValueError("target parameter required for read_note")
            result = await service.execute_read_note(vault_manager, target, response_format)
        elif context_type == "read_multiple":
            if not targets:
                raise ValueError("targets parameter required for read_multiple")
            result = await service.execute_read_multiple(vault_manager, targets, response_format)
        elif context_type == "gather_related":
            if not target:
                raise ValueError("target parameter required for gather_related")
            result = await service.execute_gather_related(
                vault_manager, target, max_related, response_format
            )
        elif context_type == "daily_note":
            result = await service.execute_daily_note(vault_manager, date, response_format)
        elif context_type == "note_with_backlinks":
            if not target:
                raise ValueError("target parameter required for note_with_backlinks")
            result = await service.execute_note_with_backlinks(
                vault_manager, target, response_format
            )
        else:
            raise ValueError(f"Unknown context_type: {context_type}")

        logger.info(
            "agent.tool.execution_completed",
            tool="obsidian_get_context_tool",
            context_type=context_type,
            token_estimate=result.token_estimate,
            has_related=result.related_notes is not None,
            has_backlinks=result.backlinks is not None,
        )

        return result

    except Exception as e:
        logger.error(
            "agent.tool.execution_failed",
            tool="obsidian_get_context_tool",
            context_type=context_type,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
