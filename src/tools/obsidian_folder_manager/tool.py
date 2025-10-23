"""Tool registration for Obsidian Folder Manager.

This module registers the folder management tool with the agent,
providing operations for creating, renaming, moving, deleting, and listing folders.
"""

from typing import TYPE_CHECKING

from pydantic_ai import RunContext

from src.agent.schemas import AgentDependencies
from src.shared.config import get_settings
from src.shared.logging import get_logger
from src.tools.obsidian_folder_manager.schemas import (
    FolderOperation,
    ManageFolderRequest,
)
from src.tools.obsidian_folder_manager.service import manage_folder_service


if TYPE_CHECKING:
    from pydantic_ai import Agent

logger = get_logger(__name__)


def register_obsidian_folder_manager_tool(
    agent: "Agent[AgentDependencies, str]",
) -> None:
    """Register the obsidian_folder_manage tool with the agent.

    Args:
        agent: Pydantic AI agent instance to register tool with.
    """

    @agent.tool
    async def obsidian_folder_manage(
        ctx: RunContext["AgentDependencies"],
        path: str,
        operation: str,
        new_name: str | None = None,
        destination: str | None = None,
        create_parents: bool = True,
        force: bool = False,
        confirm_path: str | None = None,
        check_wikilinks: bool = True,
        update_wikilinks: bool = True,
        recursive: bool = False,
        include_stats: bool = True,
        max_results: int = 50,
        offset: int = 0,
        dry_run: bool = False,
        response_format: str = "concise",
    ) -> str:
        """Manage vault folder structure with create, rename, move, delete, and list operations.

        This consolidated tool enables folder organization and automatically updates
        wikilinks when folders are renamed or moved, preventing broken links.

        Use this when you need to:
        - Create new folder structures for projects or organization
        - Rename folders when project names change (auto-updates all wikilinks)
        - Move folders to reorganize vault structure (auto-updates wikilinks)
        - Delete old or empty folders during cleanup
        - List folder contents with statistics (note counts, sizes)
        - Organize vault structure without manually updating references

        Do NOT use this for:
        - Working with individual notes (use obsidian_note_manage instead)
        - Batch operations on multiple folders at once (use obsidian_vault_organizer instead)
        - Finding folders (use LIST operation or obsidian_vault_query instead)
        - Reading or modifying note content (use obsidian_note_manage instead)
        - Just checking if a folder exists (use LIST with minimal response_format)

        Args:
            path: Relative path from vault root to the folder.
                Examples: "projects/2025", "archive", "daily/2025/01"
                DO NOT include vault path - just the relative path within vault.

            operation: Folder operation - "create", "rename", "move", "delete", or "list".
                - "create": Create new folder (optionally create parent directories)
                - "rename": Rename folder in place (updates wikilinks automatically)
                - "move": Move folder to new location (updates wikilinks automatically)
                - "delete": Delete folder (requires confirmation for safety)
                - "list": List folder contents with optional stats and pagination

            new_name: For "rename": new folder name (single component, not full path).
                Example: "website-redesign" not "projects/website-redesign"
                Automatically validates against Windows reserved names (CON, PRN, etc.)
                and invalid characters (<>:"|?*).

            destination: For "move": destination folder path relative to vault root.
                Example: "archive/2024" to move folder into archive/2024/
                Creates destination parent directories automatically if needed.
                Detects and rejects circular moves (moving folder into itself).

            create_parents: For "create": whether to create parent directories.
                - True: Creates all missing parent directories (DEFAULT)
                    Example: "projects/2025/new-project" creates all levels
                - False: Fails if parent directory doesn't exist
                    Use when: You want to ensure parent structure exists first

            force: For "delete": whether to delete non-empty folders.
                - False: Only delete empty folders, error if contains files (DEFAULT - SAFER)
                - True: Delete folder and all contents recursively (USE WITH CAUTION)
                Safety: Always use False unless you're certain folder should be deleted.

            confirm_path: Required for "delete": must match path parameter exactly.
                Safety mechanism to prevent accidental deletions.
                Example: if path="old-projects", must set confirm_path="old-projects"
                Operation will fail if confirm_path doesn't match path.

            check_wikilinks: For "delete": whether to check for incoming wikilinks.
                - True: Scans vault for notes linking to folder contents, warns about broken links (DEFAULT)
                - False: Skip wikilink check (faster but may break links)
                Returns list of affected notes that would have broken links after deletion.

            update_wikilinks: For "rename"/"move": whether to update wikilinks in vault.
                - True: Automatically updates all wikilinks referencing folder contents (DEFAULT)
                    Scans all notes and replaces [[old-path/file]] with [[new-path/file]]
                - False: Skip wikilink updates (faster but will break links)
                Token cost: Scan limited to max_wikilink_scan_notes setting (default: 1000 notes)

            recursive: For "list": whether to list subfolders recursively.
                - False: Only immediate children (1 level) (DEFAULT)
                - True: Recursive listing up to max depth (5 levels for safety)
                Use False for quick folder overview, True for complete structure.

            include_stats: For "list": whether to include folder statistics.
                - True: Include note count, total size, modified date (DEFAULT)
                    ~20 tokens per folder (slower but informative)
                - False: Only folder names and paths (~10 tokens per folder)
                    Use when: Just need folder names, not statistics

            max_results: For "list": maximum folders to return (pagination).
                Range: 1-200, Default: 50
                Use lower values (10-20) for quick overview, higher for complete listing.
                Prevents token explosion on large vault structures.

            offset: For "list": number of results to skip (pagination).
                Default: 0 (start from beginning)
                Use with max_results for pagination: offset=50, max_results=50 for page 2

            dry_run: Simulate operation without making changes.
                - False: Execute operation normally (DEFAULT)
                - True: Show what would happen without modifying vault
                Use for: Testing rename/move operations before executing

            response_format: Control output verbosity to save tokens.
                - "minimal": Operation status only (~50 tokens)
                    Use when: Just need confirmation of success
                - "concise": Status + key metadata (~150 tokens)
                    Use when: Need summary of what changed (DEFAULT)
                - "detailed": Status + full metadata + folder listings (~300+ tokens)
                    Use when: Need complete operation details

        Returns:
            Formatted string with operation result:
            - Success/failure status
            - New path for rename/move operations
            - Wikilink update count for rename/move operations
            - Folder list with stats for list operation
            - Warnings about broken links for delete operation
            - Token estimate for optimization tracking

        Performance Notes:
            - CREATE: 10-50ms, ~50 tokens
            - RENAME: 50-500ms (depends on wikilink scan), ~80 tokens
            - MOVE: 50-500ms (depends on wikilink scan), ~80 tokens
            - DELETE: 50-200ms, ~50-100 tokens (more if wikilinks checked)
            - LIST minimal: 50-100ms, ~50 tokens + 10 per folder
            - LIST detailed: 100-500ms, ~150 tokens + 40 per folder
            - Wikilink updates: Limited to max_wikilink_scan_notes (default: 1000 notes)
            - LIST recursive: Depth limited to 5 levels (safety)
            - Max results: Capped at 200 folders per request

        Examples:
            # Create nested project structure
            obsidian_folder_manage(
                path="projects/2025/website-redesign",
                operation="create",
                create_parents=True
            )

            # Rename folder and update all wikilinks
            obsidian_folder_manage(
                path="projects/alpha",
                operation="rename",
                new_name="website-redesign",
                update_wikilinks=True
            )

            # Move folder to archive (with wikilink updates)
            obsidian_folder_manage(
                path="projects/completed-project",
                operation="move",
                destination="archive/2024",
                update_wikilinks=True
            )

            # Delete empty folder
            obsidian_folder_manage(
                path="drafts/old",
                operation="delete",
                confirm_path="drafts/old",
                force=False
            )

            # Delete non-empty folder with wikilink check
            obsidian_folder_manage(
                path="projects/abandoned",
                operation="delete",
                confirm_path="projects/abandoned",
                force=True,
                check_wikilinks=True
            )

            # List immediate children with stats
            obsidian_folder_manage(
                path="projects",
                operation="list",
                recursive=False,
                include_stats=True,
                response_format="concise"
            )

            # List all subfolders recursively (up to depth 5)
            obsidian_folder_manage(
                path="projects",
                operation="list",
                recursive=True,
                include_stats=True,
                max_results=100
            )

            # Quick folder overview without stats (minimal tokens)
            obsidian_folder_manage(
                path=".",
                operation="list",
                recursive=False,
                include_stats=False,
                response_format="minimal"
            )

            # Test rename operation without executing (dry run)
            obsidian_folder_manage(
                path="projects/test",
                operation="rename",
                new_name="test-renamed",
                dry_run=True
            )

            # Paginated listing (page 2: folders 51-100)
            obsidian_folder_manage(
                path="projects",
                operation="list",
                offset=50,
                max_results=50,
                include_stats=True
            )
        """
        settings = get_settings()

        # Validate operation
        try:
            folder_operation = FolderOperation(operation)
        except ValueError:
            return f"Invalid operation: {operation}. Must be one of: create, rename, move, delete, list"

        # Create request
        try:
            request = ManageFolderRequest(
                path=path,
                operation=folder_operation,
                new_name=new_name,
                destination=destination,
                create_parents=create_parents,
                force=force,
                confirm_path=confirm_path,
                check_wikilinks=check_wikilinks,
                update_wikilinks=update_wikilinks,
                recursive=recursive,
                include_stats=include_stats,
                max_results=max_results,
                offset=offset,
                dry_run=dry_run,
                response_format=response_format,  # type: ignore[arg-type]
            )
        except ValueError as e:
            logger.error("invalid_folder_request", error=str(e), path=path)
            return f"Invalid request: {e}"

        # Execute service
        try:
            result = await manage_folder_service(
                request=request,
                vault_path=ctx.deps.vault_path,
                max_folder_depth=settings.max_folder_depth,
                max_wikilink_scan_notes=settings.max_wikilink_scan_notes,
            )

            if not result.success:
                return f"Operation failed: {result.message}"

            # Format response
            response_parts = [
                f"✓ {result.message}",
                f"Operation: {result.operation.value}",
            ]

            # Add operation-specific details
            if result.new_path:
                response_parts.append(f"New path: {result.new_path}")

            # Add metadata based on operation
            if folder_operation in {FolderOperation.RENAME, FolderOperation.MOVE}:
                links_updated = result.metadata.get("links_updated", 0)
                if links_updated:
                    response_parts.append(f"Wikilinks updated: {links_updated} notes")

            elif folder_operation == FolderOperation.DELETE:
                affected_notes = result.metadata.get("affected_notes", [])
                affected_count = result.metadata.get("affected_notes_count", 0)
                if affected_count > 0:
                    response_parts.append(f"\n⚠️ Warning: {affected_count} notes have links to deleted folder")
                    if affected_notes:
                        response_parts.append("Affected notes (first 10):")
                        for note in affected_notes[:10]:
                            response_parts.append(f"  - {note}")

            elif folder_operation == FolderOperation.LIST:
                folders = result.metadata.get("folders", [])
                total = result.metadata.get("total_folders", 0)
                has_more = result.metadata.get("has_more", False)

                if response_format != "minimal":
                    response_parts.append(f"\nFolders ({total} total):")
                    for folder in folders:
                        folder_line = f"  - {folder['name']}"
                        if folder.get("note_count") is not None:
                            folder_line += f" ({folder['note_count']} notes"
                            if folder.get("total_size_bytes"):
                                size_mb = folder["total_size_bytes"] / (1024 * 1024)
                                folder_line += f", {size_mb:.1f}MB"
                            folder_line += ")"
                        response_parts.append(folder_line)

                    if has_more:
                        remaining = total - (result.metadata.get("offset", 0) + result.metadata.get("returned", 0))
                        response_parts.append(f"\n({remaining} more folders available - use offset to see more)")

            response_parts.append(f"\n(~{result.token_estimate} tokens)")

            return "\n".join(response_parts)

        except FileNotFoundError as e:
            logger.error("folder_not_found", path=path, error=str(e))
            return f"Folder not found: {path}"
        except ValueError as e:
            logger.error("folder_operation_error", path=path, error=str(e))
            return f"Error: {e}"
        except Exception as e:
            logger.exception("folder_operation_failed", path=path, operation=operation)
            return f"Operation failed: {e}"

    logger.info("tool_registered", tool="obsidian_folder_manager")
