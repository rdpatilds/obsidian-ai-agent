"""Tool registration for Obsidian Vault Organizer.

Registers the batch vault organization tool with the agent.
"""

from typing import TYPE_CHECKING

from pydantic_ai import RunContext

from src.agent.schemas import AgentDependencies
from src.shared.config import get_settings
from src.shared.logging import get_logger
from src.tools.obsidian_vault_organizer.schemas import OrganizeOperation, OrganizeRequest
from src.tools.obsidian_vault_organizer.service import organize_vault_service


if TYPE_CHECKING:
    from pydantic_ai import Agent

logger = get_logger(__name__)

# Constants
MAX_NOTES_PER_BATCH = 20


def register_obsidian_vault_organizer_tool(agent: "Agent[AgentDependencies, str]") -> None:
    """Register Obsidian Vault Organizer tool with agent.

    Args:
        agent: Pydantic AI agent instance.
    """

    @agent.tool
    async def obsidian_vault_organize(  # noqa: PLR0913, PLR0911, PLR0912
        ctx: RunContext[AgentDependencies],  # noqa: ARG001
        notes: str,
        operation: str,
        destination: str | None = None,
        tags_to_add: str | None = None,
        tags_to_remove: str | None = None,
        require_confirmation: bool = True,
        dry_run: bool = False,
    ) -> str:
        """Batch organize notes in the Obsidian vault (move, tag, archive, delete).

        Consolidates what would otherwise require 3+ tool calls for batch operations.
        Supports atomic transactions with automatic rollback on failure for MOVE/ARCHIVE.

        Use this when you need to:
        - Move multiple notes to a new location at once
        - Add or remove tags from multiple notes
        - Archive old notes with timestamp organization
        - Delete notes (with safety confirmation)
        - Preview changes before applying them (dry-run)

        Do NOT use this for:
        - Reading or writing note content (use obsidian_note_manage instead)
        - Finding notes to organize (use obsidian_vault_query first, then organize)
        - Single note operations (use obsidian_note_manage for individual notes)

        Efficient Batch Workflow Pattern:

        ✅ RECOMMENDED (2-step pattern):
            # User: "Move all drafts to archive"
            Step 1: obsidian_vault_query(query="", mode="tags", tag_filters='["draft"]')
                    → Returns: ["inbox/draft-1.md", "inbox/draft-2.md", "inbox/draft-3.md"]
            Step 2: obsidian_vault_organize(
                        notes="inbox/draft-1.md, inbox/draft-2.md, inbox/draft-3.md",
                        operation="archive"
                    )
            Total: 2 calls ✅

        ❌ AVOID (Multiple searches, redundant operations):
            Step 1: obsidian_vault_query(query="drafts")  # Search attempt 1
            Step 2: obsidian_vault_query(query="draft")   # Search attempt 2
            Step 3: obsidian_note_manage(...)             # Individual operation
            Step 4: obsidian_note_manage(...)             # Individual operation
            Step 5: obsidian_note_manage(...)             # Individual operation
            Total: 5+ calls ❌ (150% overhead)

        Key Principle: DISCOVER ONCE, ACT ON ALL
        - Use obsidian_vault_query ONCE to get all matching note paths
        - Use obsidian_vault_organize ONCE to act on all paths together
        - Don't organize notes one-by-one unless truly necessary

        Dry-Run First for Safety:
            # Preview before executing (recommended for destructive operations)
            Step 1: obsidian_vault_organize(notes=[paths], operation="delete", dry_run=True)
                    → Shows what would be deleted
            Step 2: User confirms → Run without dry_run
            Use for: DELETE, MOVE, ARCHIVE operations

        Args:
            notes: Comma-separated list of note paths (e.g. "note1.md, note2.md").
                Maximum 20 notes per batch for safety.
            operation: Operation type - "move", "tag", "archive", or "delete".
            destination: Destination folder path (required for MOVE, optional for ARCHIVE).
                - MOVE: Required. Specify destination folder (e.g. "projects/2025")
                - ARCHIVE: Optional. If not provided, auto-generates "archive/{YYYY-MM-DD}/" (recommended).
                  If provided, archives to custom destination (e.g. "archive/old-projects")
                - TAG/DELETE: Not used, can be omitted
            tags_to_add: Comma-separated tags to add for TAG operation (e.g. "review, important").
                Tags are stored in frontmatter. The "#" prefix is optional.
            tags_to_remove: Comma-separated tags to remove for TAG operation.
            require_confirmation: For DELETE operation only. Controls deletion safety.
                - True (DEFAULT): DELETE will fail with safety message (safe default)
                - False: DELETE will permanently delete notes (use with caution)
                RECOMMENDED: Always use dry_run=True first to preview, then set to False.
                Has no effect on MOVE, TAG, or ARCHIVE operations.
            dry_run: If true, preview what would happen without making changes.
                Useful for verifying batch operations before execution.
                RECOMMENDED for DELETE: Use dry_run first, then execute with require_confirmation=False.

        Returns:
            Summary of batch operation with success/failure counts and details for each note.

        Performance Notes:
            - MOVE/ARCHIVE: Atomic operations with automatic rollback on any failure
            - TAG: Non-atomic, processes all notes even if some fail
            - DELETE: Non-reversible, defaults to require_confirmation=true for safety
            - Dry-run mode: ~0ms execution, just validation and preview
            - Actual operations: ~10-50ms per note depending on operation
            - Recommended DELETE workflow: dry_run=True → review → require_confirmation=False

        Safety Features:
            - Path security validation (blocks .obsidian, .git, etc.)
            - Atomic batch for MOVE/ARCHIVE (all-or-nothing with rollback)
            - DELETE requires explicit require_confirmation=False (safe by default)
            - Maximum 20 notes per batch to prevent accidents
            - Dry-run mode for safe preview before executing

        Examples:
            # Move project notes to archive
            obsidian_vault_organize(
                notes="project-alpha.md, project-beta.md",
                operation="move",
                destination="archive/projects"
            )

            # Add tags to multiple notes
            obsidian_vault_organize(
                notes="meeting-jan-15.md, meeting-jan-16.md",
                operation="tag",
                tags_to_add="reviewed, q1-2025"
            )

            # Archive old drafts (auto-generates timestamp path - RECOMMENDED)
            obsidian_vault_organize(
                notes="draft1.md, draft2.md, draft3.md",
                operation="archive"
                # Auto-generates: archive/2025-10-18/ (no destination needed!)
            )

            # Archive to custom destination (optional)
            obsidian_vault_organize(
                notes="old-project-1.md, old-project-2.md",
                operation="archive",
                destination="archive/2024-projects"  # Custom destination
            )

            # Preview move operation before executing
            obsidian_vault_organize(
                notes="note1.md, note2.md",
                operation="move",
                destination="projects",
                dry_run=True  # Just show what would happen
            )

            # Delete notes (RECOMMENDED: 2-step workflow with dry-run first)
            # Step 1: Preview what will be deleted
            obsidian_vault_organize(
                notes="temp-1.md, temp-2.md, temp-3.md",
                operation="delete",
                dry_run=True  # Preview only, no actual deletion
            )
            # Step 2: Actually delete after confirming preview
            obsidian_vault_organize(
                notes="temp-1.md, temp-2.md, temp-3.md",
                operation="delete",
                require_confirmation=False  # Explicit opt-in to deletion
            )

            # Remove tags from batch of notes
            obsidian_vault_organize(
                notes="old-note-1.md, old-note-2.md",
                operation="tag",
                tags_to_remove="urgent, todo"
            )

        Workflow Pattern:
            1. Use obsidian_vault_query to find notes: "Find all notes tagged #old-draft"
            2. Review results to confirm which notes to organize
            3. Use dry_run=True to preview: obsidian_vault_organize(..., dry_run=True)
            4. Execute actual operation: obsidian_vault_organize(..., dry_run=False)
        """
        settings = get_settings()
        vault_path = settings.obsidian_vault_path

        if not vault_path:
            return "Error: OBSIDIAN_VAULT_PATH not configured"

        # Parse notes list
        notes_list = [n.strip() for n in notes.split(",") if n.strip()]

        if not notes_list:
            return "Error: No notes provided"

        if len(notes_list) > MAX_NOTES_PER_BATCH:
            return f"Error: Maximum {MAX_NOTES_PER_BATCH} notes per batch operation"

        # Parse operation
        try:
            op = OrganizeOperation(operation.lower())
        except ValueError:
            return f"Error: Invalid operation '{operation}'. Must be: move, tag, archive, delete"

        # Parse tags
        tags_add_list = None
        if tags_to_add:
            tags_add_list = [t.strip() for t in tags_to_add.split(",") if t.strip()]

        tags_remove_list = None
        if tags_to_remove:
            tags_remove_list = [t.strip() for t in tags_to_remove.split(",") if t.strip()]

        # Create request
        try:
            request = OrganizeRequest(
                notes=notes_list,
                operation=op,
                destination=destination,
                tags_to_add=tags_add_list,
                tags_to_remove=tags_remove_list,
                require_confirmation=require_confirmation,
                dry_run=dry_run,
            )
        except ValueError as e:
            return f"Error: Invalid request - {e!s}"

        # Execute operation
        try:
            response = await organize_vault_service(request, vault_path)

            # Format response
            lines = []
            if response.dry_run:
                lines.append("[DRY RUN - No changes made]")

            lines.append(
                f"\nBatch {operation.upper()} operation: "
                f"{response.total_succeeded} succeeded, {response.total_failed} failed"
            )

            if response.rolled_back:
                lines.append("\n⚠️  Operation failed and was ROLLED BACK - no changes made")

            # Show results for each note
            lines.append("\nResults:")
            for result in response.results:
                status = "✓" if result.success else "✗"
                msg = result.message
                if result.new_path:
                    msg = f"{msg} → {result.new_path}"
                lines.append(f"  {status} {result.path}: {msg}")

            # Add guidance if there were failures
            if response.total_failed > 0 and not response.rolled_back:
                if op == OrganizeOperation.DELETE:
                    lines.append(
                        "\nNote: DELETE operations require setting require_confirmation=False parameter"
                    )
                    lines.append(
                        "RECOMMENDED: Use dry_run=True first to preview, then re-run with require_confirmation=False"
                    )
                elif op in (OrganizeOperation.MOVE, OrganizeOperation.ARCHIVE):
                    lines.append(
                        "\nNote: MOVE/ARCHIVE operations are atomic - "
                        "partial failures trigger automatic rollback"
                    )

            return "\n".join(lines)

        except Exception as e:
            logger.exception("obsidian_vault_organize_failed", operation=operation, error=str(e))
            return f"Error organizing vault: {e!s}"

    logger.info("tool_registered", tool="obsidian_vault_organize")
