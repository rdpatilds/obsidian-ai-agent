"""Tool registration for Obsidian Note Manager.

This module registers the consolidated note management tool with the agent,
providing a unified interface for read, write, patch, append, and delete operations.
"""

import json
from typing import TYPE_CHECKING, Any

from pydantic_ai import RunContext

from src.agent.schemas import AgentDependencies
from src.shared.config import get_settings
from src.shared.logging import get_logger
from src.tools.obsidian_note_manager.schemas import (
    ManageNoteRequest,
    NoteOperation,
)
from src.tools.obsidian_note_manager.service import manage_note_service


if TYPE_CHECKING:
    from pydantic_ai import Agent

logger = get_logger(__name__)


def register_obsidian_note_manager_tool(
    agent: "Agent[AgentDependencies, str]",
) -> None:
    """Register the obsidian_note_manage tool with the agent.

    Args:
        agent: Pydantic AI agent instance to register tool with.
    """

    @agent.tool
    async def obsidian_note_manage(
        ctx: RunContext["AgentDependencies"],
        path: str,
        operation: str,
        content: str | None = None,
        metadata_updates: str | None = None,
        find_replace: str | None = None,
        replace_all: bool = False,
        confirm_path: str | None = None,
        response_format: str = "concise",
    ) -> str:
        """Manage notes with unified read, write, patch, append, and delete operations.

        This consolidated tool replaces what would otherwise require 4-5 separate tool calls.
        It provides token-efficient response formatting to minimize costs.

        Use this when you need to:
        - Read a SPECIFIC note you already know the path to
        - Create or update a note's content
        - Find and replace text within a note
        - Append content to an existing note
        - Delete a note (with confirmation)
        - Update note metadata (frontmatter)

        Do NOT use this for:
        - Finding notes (use obsidian_vault_query instead)
        - Reading MULTIPLE notes at once (use obsidian_vault_query with batch mode)
        - Analyzing note relationships (use obsidian_graph_analyze instead)
        - Just checking if a note exists (use operation="read" with response_format="minimal")

        Path Resolution Strategy (IMPORTANT):
        If you don't know the exact path to a note:
        1. ✅ FIRST: Use obsidian_vault_query to find the note's path
        2. ✅ THEN: Use this tool with the discovered path

        DO NOT:
        - ❌ Try guessing paths (e.g., "note.md" without folder)
        - ❌ Try reading with bare filename hoping it works
        - ❌ Make multiple read attempts with different paths

        Efficient Pattern:
            # User: "Read project-alpha and tell me the status"
            Step 1: obsidian_vault_query(query="project-alpha", mode="fulltext")
                    → Result: "projects/project-alpha.md"
            Step 2: obsidian_note_manage(path="projects/project-alpha.md", operation="read")
            Total: 2 calls ✅

        Inefficient Pattern (AVOID):
            # ❌ Don't do this:
            Step 1: obsidian_note_manage(path="project-alpha.md", operation="read")
                    → Error: Note not found
            Step 2: obsidian_vault_query(query="project-alpha")
                    → Result: "projects/project-alpha.md"
            Step 3: obsidian_note_manage(path="projects/project-alpha.md", operation="read")
            Total: 3 calls ❌ (50% overhead)

        Args:
            path: Relative path from vault root.
                Examples: "daily/2025-01-15.md", "projects/alpha.md", "inbox/ideas.md"
                DO NOT include vault path - just the relative path within the vault.

            operation: Operation to perform - "read", "update", "patch", "append", or "delete".
                - "read": View note content (use response_format to control detail)
                - "update": Replace entire note content (optionally update metadata)
                - "patch": Find and replace text within note
                - "append": Add content to end of note
                - "delete": Delete note (requires confirm_path)

            content: Content for "update" or "append" operations.
                For "patch", use find_replace instead.

            metadata_updates: JSON string of frontmatter fields to update.
                Example: '{"status": "completed", "priority": 8, "tags": ["project", "done"]}'
                Merges with existing frontmatter.

            find_replace: For "patch" operation: JSON array of [find_text, replace_text].
                Example: '["TODO", "DONE"]' or '["old text", "new text"]'

            replace_all: For "patch" operation: if true, replace all occurrences.
                If false and multiple matches found, operation will fail with error message.
                This is a safety check to prevent accidental mass replacements.

            confirm_path: Required for "delete" operation - must match path parameter.
                Safety mechanism to prevent accidental deletions.
                Example: if path="old-draft.md", set confirm_path="old-draft.md"

            response_format: Control output verbosity to save tokens.
                - "minimal": Title, tags, summary only (~50 tokens)
                    Use when: Just need to check metadata or verify existence
                - "concise": Key metadata + content preview (~150 tokens)
                    Use when: Need overview before deciding next action (DEFAULT)
                - "detailed": Full content with all frontmatter (~1500+ tokens)
                    Use when: Need complete content for summarization or analysis

        Returns:
            Formatted string with operation result. Content varies by response_format:
            - Minimal: Title, tags, modified date
            - Concise: Above + first 100 words of content
            - Detailed: Full content with complete frontmatter section

        Performance Notes:
            - Minimal format: ~50 tokens (recommended for metadata checks)
            - Concise format: ~150 tokens (default, good balance)
            - Detailed format: ~1500+ tokens (use only when truly needed)
            - Execution time: 10-50ms for typical notes
            - Max file size: Configured in vault settings (default 10MB)
            - Always prefer concise over detailed to conserve tokens

        Examples:
            # Read note with minimal details (just check if it exists)
            obsidian_note_manage(
                path="daily/2025-01-15.md",
                operation="read",
                response_format="minimal"
            )

            # Read full note for analysis
            obsidian_note_manage(
                path="projects/website-redesign.md",
                operation="read",
                response_format="detailed"
            )

            # Create or update a note with metadata
            obsidian_note_manage(
                path="meetings/2025-01-15-standup.md",
                operation="update",
                content="# Standup Meeting\\n\\n## Attendees\\n- Alice\\n- Bob",
                metadata_updates='{"tags": ["meeting", "standup"], "date": "2025-01-15"}'
            )

            # Find and replace text (single occurrence)
            obsidian_note_manage(
                path="project-plan.md",
                operation="patch",
                find_replace='["Phase 1", "Phase 2"]'
            )

            # Find and replace all occurrences
            obsidian_note_manage(
                path="meeting-notes.md",
                operation="patch",
                find_replace='["TODO", "DONE"]',
                replace_all=True
            )

            # Append to daily note
            obsidian_note_manage(
                path="daily/2025-01-15.md",
                operation="append",
                content="## Evening Update\\n\\nCompleted the quarterly review."
            )

            # Delete note (requires confirmation)
            obsidian_note_manage(
                path="old-draft.md",
                operation="delete",
                confirm_path="old-draft.md"
            )

            # Update just metadata without changing content
            obsidian_note_manage(
                path="project-alpha.md",
                operation="read",
                response_format="detailed"  # First read to get content
            )
            # Then update with same content but new metadata
            obsidian_note_manage(
                path="project-alpha.md",
                operation="update",
                content="<previous content>",
                metadata_updates='{"status": "completed", "completed_date": "2025-01-15"}'
            )
        """
        settings = get_settings()

        # Validate operation
        try:
            note_operation = NoteOperation(operation)
        except ValueError:
            return f"Invalid operation: {operation}. Must be one of: read, update, patch, append, delete"

        # Parse JSON parameters
        metadata_dict: dict[str, Any] | None = None
        if metadata_updates:
            try:
                metadata_dict = json.loads(metadata_updates)
            except json.JSONDecodeError as e:
                return f"Invalid JSON in metadata_updates: {e}"

        find_replace_tuple: tuple[str, str] | None = None
        if find_replace:
            try:
                find_replace_list = json.loads(find_replace)
                if not isinstance(find_replace_list, list) or len(find_replace_list) != 2:
                    return "find_replace must be a JSON array with exactly 2 elements: [find_text, replace_text]"
                find_replace_tuple = (find_replace_list[0], find_replace_list[1])
            except json.JSONDecodeError as e:
                return f"Invalid JSON in find_replace: {e}"

        # Create request
        try:
            request = ManageNoteRequest(
                path=path,
                operation=note_operation,
                content=content,
                metadata_updates=metadata_dict,
                find_replace=find_replace_tuple,
                replace_all=replace_all,
                confirm_path=confirm_path,
                response_format=response_format,  # type: ignore[arg-type]
            )
        except Exception as e:
            logger.error("invalid_note_request", error=str(e), path=path)
            return f"Invalid request: {e}"

        # Execute service
        try:
            result = await manage_note_service(
                request=request,
                vault_path=ctx.deps.vault_path,
                max_file_size_mb=settings.max_file_size_mb,
            )

            if not result.success:
                return f"Operation failed: {result.message}"

            # Format response
            response_parts = [
                f"✓ {result.message}",
                f"Operation: {result.operation.value}",
            ]

            # Add operation-specific details
            if result.operation == NoteOperation.READ:
                response_parts.append(f"\nNote: {result.data.get('title', 'Untitled')}")
                if tags := result.data.get("tags"):
                    response_parts.append(f"Tags: {', '.join(tags)}")

                if response_format == "minimal":
                    response_parts.append(f"Summary: {result.data.get('summary', '')}")
                elif response_format == "concise":
                    response_parts.append(f"\nPreview:\n{result.data.get('content_preview', '')}")
                    response_parts.append(f"\nWord count: {result.data.get('word_count', 0)}")
                else:  # detailed
                    response_parts.append(f"\nContent:\n{result.data.get('content', '')}")
                    if frontmatter := result.data.get("frontmatter"):
                        response_parts.append(f"\nFrontmatter: {json.dumps(frontmatter, indent=2)}")

            elif result.operation == NoteOperation.PATCH:
                match_count = result.data.get("match_count", 0)
                response_parts.append(f"Replaced {match_count} occurrence(s)")

            response_parts.append(f"\n(~{result.token_estimate} tokens)")

            return "\n".join(response_parts)

        except FileNotFoundError as e:
            logger.error("note_not_found", path=path, error=str(e))
            return f"Note not found: {path}"
        except ValueError as e:
            logger.error("note_operation_error", path=path, error=str(e))
            return f"Error: {e}"
        except Exception as e:
            logger.exception("note_operation_failed", path=path, operation=operation)
            return f"Operation failed: {e}"

    logger.info("tool_registered", tool="obsidian_note_manager")
