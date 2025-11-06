"""Obsidian Note Manager Tool - note and folder modification operations."""

from typing import Literal

from pydantic_ai import RunContext

from app.core.agents import AgentDeps, vault_agent
from app.core.logging import get_logger
from app.features.obsidian_note_manager_tool import (
    obsidian_note_manager_tool_service as service,
)
from app.features.obsidian_note_manager_tool.obsidian_note_manager_tool_models import (
    ObsidianNoteManagerToolResult,
)

logger = get_logger(__name__)


@vault_agent.tool
async def obsidian_note_manager_tool(
    ctx: RunContext[AgentDeps],
    operation: Literal[
        "create_note",
        "update_note",
        "append_note",
        "delete_note",
        "move_note",
        "create_folder",
        "delete_folder",
        "move_folder",
        "bulk_tag",
        "bulk_move",
        "bulk_update_metadata",
    ],
    target: str | None = None,
    content: str | None = None,
    destination: str | None = None,
    metadata: dict[str, str | list[str] | int | float | bool] | None = None,
    targets: list[str] | None = None,
    destination_folder: str | None = None,
    create_folders: bool = True,
    confirm_destructive: bool = False,
    exist_ok: bool = False,
    recursive: bool = False,
) -> ObsidianNoteManagerToolResult:
    """Manage notes and folders in the Obsidian vault - all modification operations.

    Use this when you need to:
    - Create new notes with optional frontmatter metadata
    - Modify existing note content (update entire content or append to end)
    - Delete notes or folders (requires confirm_destructive=True)
    - Move or reorganize notes and folders within the vault
    - Perform bulk operations on multiple notes (tagging, moving, metadata updates)
    - Create or manage folder structures for organization

    Do NOT use this for:
    - Searching for notes or exploring vault content (use obsidian_query_vault_tool instead)
    - Reading note content without modification (use obsidian_query_vault_tool instead)
    - Checking if notes exist (use obsidian_query_vault_tool with response_format="concise")

    Args:
        operation: Type of modification operation to perform.
            - "create_note": Create new note (requires target, content; optional metadata, create_folders)
                Use when: User asks to "create", "write", or "make a new note"
            - "update_note": Replace entire note content (requires target, content; optional metadata)
                Use when: User asks to "update", "replace", or "rewrite" a note
            - "append_note": Add content to end of existing note (requires target, content)
                Use when: User asks to "add to", "append", or "continue" a note
            - "delete_note": Remove note from vault (requires target, confirm_destructive=True)
                Use when: User explicitly confirms deletion
            - "move_note": Relocate note to new path (requires target, destination; optional create_folders)
                Use when: User asks to "move", "relocate", or "rename" a note
            - "create_folder": Create folder structure (requires target; optional exist_ok)
                Use when: User asks to "create folder" or "make directory"
            - "delete_folder": Remove folder (requires target, confirm_destructive=True; optional recursive)
                Use when: User explicitly confirms folder deletion
            - "move_folder": Relocate folder (requires target, destination)
                Use when: User asks to "move" or "rename" a folder
            - "bulk_tag": Add tags to multiple notes (requires targets, metadata with "tags" key)
                Use when: User wants to "tag multiple notes" or "add tags to several files"
            - "bulk_move": Move multiple notes to folder (requires targets, destination_folder; optional create_folders)
                Use when: User asks to "move several notes" or "organize notes into folder"
            - "bulk_update_metadata": Update frontmatter for multiple notes (requires targets, metadata)
                Use when: User wants to "update metadata" or "set properties" for multiple notes
        target: Path to target note or folder (relative to vault root).
            Examples: "Daily/2025-01-15.md", "Projects/New Project.md", "Archive/2024"
            Required for: create_note, update_note, append_note, delete_note, move_note,
                         create_folder, delete_folder, move_folder
        content: Content to write or append to note.
            For create_note/update_note: Full note content (markdown).
            For append_note: Content to add to end of note.
            Required for: create_note, update_note, append_note
        destination: Destination path for move operations.
            Used for: move_note (new note path), move_folder (new folder path)
        metadata: Frontmatter metadata dictionary for notes.
            Example: {"tags": ["project", "active"], "status": "planning", "priority": 1}
            Supported types: str, list[str], int, float, bool
            Used for: create_note, update_note, bulk_tag, bulk_update_metadata
        targets: List of note paths for bulk operations.
            Example: ["note1.md", "Projects/note2.md", "Archive/old.md"]
            Required for: bulk_tag, bulk_move, bulk_update_metadata
        destination_folder: Folder path for bulk_move operation.
            Example: "Archive/2024" - all notes will be moved here
            Required for: bulk_move
        create_folders: Auto-create parent folders if they don't exist.
            Default True. Set False to fail if parent doesn't exist.
            Used for: create_note, move_note, bulk_move
        confirm_destructive: Safety flag required for deletion operations.
            Must be True to proceed with delete_note or delete_folder.
            Prevents accidental data loss.
            Required for: delete_note, delete_folder (must be True)
        exist_ok: Don't error if folder already exists during create_folder.
            Default False. Set True to skip existing folders.
            Used for: create_folder
        recursive: Delete non-empty folders during delete_folder.
            Default False (only delete empty folders).
            Set True to delete folder with all contents.
            Used for: delete_folder

    Returns:
        ObsidianNoteManagerToolResult with operation details:
        - success: bool - Whether operation completed successfully
        - operation: str - Operation type that was executed
        - affected_count: int - Number of items modified (1 for single ops, N for bulk)
        - affected_paths: list[str] - Paths that were created/modified/deleted
        - message: str - Human-readable summary
        - warnings: list[str] | None - Non-fatal issues encountered
        - partial_success: bool | None - True if some bulk items succeeded and some failed
        - failures: list[dict] | None - Failed items with reasons for bulk operations

    Performance Notes:
        - Single operations: <50ms typical execution
        - Bulk operations: ~20-50ms per item
        - Token usage: ~100 tokens for result (minimal overhead)
        - Bulk partial success: Returns details on what succeeded vs failed
        - Safety confirmations add no performance overhead

    Examples:
        # Create note with frontmatter
        obsidian_note_manager_tool(
            operation="create_note",
            target="Projects/New Project.md",
            content="# New Project\n\nProject details...",
            metadata={"tags": ["project", "active"], "status": "planning"}
        )

        # Append to daily note
        obsidian_note_manager_tool(
            operation="append_note",
            target="Daily/2025-01-15.md",
            content="\n## Meeting Notes\n- Discussed architecture"
        )

        # Update entire note content
        obsidian_note_manager_tool(
            operation="update_note",
            target="Draft.md",
            content="# Revised Draft\n\nCompletely new content...",
            metadata={"tags": ["draft", "updated"]}
        )

        # Move note to archive
        obsidian_note_manager_tool(
            operation="move_note",
            target="Old Project.md",
            destination="Archive/2024/Old Project.md",
            create_folders=True
        )

        # Delete note (requires confirmation)
        obsidian_note_manager_tool(
            operation="delete_note",
            target="Draft.md",
            confirm_destructive=True
        )

        # Create nested folder structure
        obsidian_note_manager_tool(
            operation="create_folder",
            target="Projects/2025/Q1",
            exist_ok=True
        )

        # Bulk tag multiple notes
        obsidian_note_manager_tool(
            operation="bulk_tag",
            targets=["note1.md", "note2.md", "note3.md"],
            metadata={"tags": ["reviewed", "processed"]}
        )

        # Bulk move notes to archive
        obsidian_note_manager_tool(
            operation="bulk_move",
            targets=["note1.md", "Projects/note2.md"],
            destination_folder="Archive/Old Projects",
            create_folders=True
        )

        # Bulk update metadata
        obsidian_note_manager_tool(
            operation="bulk_update_metadata",
            targets=["Project1.md", "Project2.md"],
            metadata={"status": "completed", "archived": True}
        )

        # Delete folder recursively (requires confirmation)
        obsidian_note_manager_tool(
            operation="delete_folder",
            target="Archive/2023",
            confirm_destructive=True,
            recursive=True
        )

        # Move folder
        obsidian_note_manager_tool(
            operation="move_folder",
            target="Projects/Old",
            destination="Archive/Projects/Old"
        )
    """
    vault_manager = ctx.deps.vault_manager

    logger.info(
        "agent.tool.execution_started",
        tool="obsidian_note_manager_tool",
        operation=operation,
    )

    try:
        # Route to appropriate service function based on operation
        if operation == "create_note":
            if not target or not content:
                raise ValueError("create_note requires target and content parameters")
            result = await service.execute_create_note(
                vault_manager, target, content, metadata, create_folders
            )

        elif operation == "update_note":
            if not target or not content:
                raise ValueError("update_note requires target and content parameters")
            result = await service.execute_update_note(vault_manager, target, content, metadata)

        elif operation == "append_note":
            if not target or not content:
                raise ValueError("append_note requires target and content parameters")
            result = await service.execute_append_note(vault_manager, target, content)

        elif operation == "delete_note":
            if not target:
                raise ValueError("delete_note requires target parameter")
            result = await service.execute_delete_note(vault_manager, target, confirm_destructive)

        elif operation == "move_note":
            if not target or not destination:
                raise ValueError("move_note requires target and destination parameters")
            result = await service.execute_move_note(
                vault_manager, target, destination, create_folders
            )

        elif operation == "create_folder":
            if not target:
                raise ValueError("create_folder requires target parameter")
            result = await service.execute_create_folder(vault_manager, target, exist_ok)

        elif operation == "delete_folder":
            if not target:
                raise ValueError("delete_folder requires target parameter")
            result = await service.execute_delete_folder(
                vault_manager, target, confirm_destructive, recursive
            )

        elif operation == "move_folder":
            if not target or not destination:
                raise ValueError("move_folder requires target and destination parameters")
            result = await service.execute_move_folder(vault_manager, target, destination)

        elif operation == "bulk_tag":
            if not targets or not metadata:
                raise ValueError("bulk_tag requires targets and metadata parameters")
            result = await service.execute_bulk_tag(vault_manager, targets, metadata)

        elif operation == "bulk_move":
            if not targets or not destination_folder:
                raise ValueError("bulk_move requires targets and destination_folder parameters")
            result = await service.execute_bulk_move(
                vault_manager, targets, destination_folder, create_folders
            )

        elif operation == "bulk_update_metadata":
            if not targets or not metadata:
                raise ValueError("bulk_update_metadata requires targets and metadata parameters")
            result = await service.execute_bulk_update_metadata(vault_manager, targets, metadata)

        else:
            raise ValueError(f"Unknown operation: {operation}")

        logger.info(
            "agent.tool.execution_completed",
            tool="obsidian_note_manager_tool",
            operation=operation,
            success=result.success,
            affected_count=result.affected_count,
        )

        return result

    except Exception as e:
        logger.error(
            "agent.tool.execution_failed",
            tool="obsidian_note_manager_tool",
            operation=operation,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
