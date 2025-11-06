"""Business logic for Obsidian Note Manager Tool."""

from pathlib import Path

from app.core.logging import get_logger
from app.features.obsidian_note_manager_tool.obsidian_note_manager_tool_models import (
    ObsidianNoteManagerToolResult,
)
from app.shared.vault.vault_manager import VaultManager

logger = get_logger(__name__)


async def execute_create_note(
    vault_manager: VaultManager,
    target: str,
    content: str,
    metadata: dict[str, str | list[str] | int | float | bool] | None,
    create_folders: bool,
) -> ObsidianNoteManagerToolResult:
    """Create new note with optional frontmatter.

    Args:
        vault_manager: VaultManager instance
        target: Note path to create
        content: Note content
        metadata: Optional frontmatter metadata
        create_folders: Create parent folders if missing

    Returns:
        ObsidianNoteManagerToolResult with creation details
    """
    logger.info("vault.create_note_started", target=target)

    try:
        # Create parent folders if needed
        if create_folders:
            parent = str(Path(target).parent)
            if parent != ".":
                vault_manager.create_folder(parent, exist_ok=True)

        # Write note
        vault_manager.write_note(target, content, metadata, overwrite=False)

        logger.info("vault.create_note_completed", target=target)

        return ObsidianNoteManagerToolResult(
            success=True,
            operation="create_note",
            affected_count=1,
            affected_paths=[target],
            message=f"Created note: {target}",
        )

    except Exception as e:
        logger.error("vault.create_note_failed", target=target, error=str(e), exc_info=True)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="create_note",
            affected_count=0,
            affected_paths=[],
            message=f"Failed to create note: {e!s}",
        )


async def execute_update_note(
    vault_manager: VaultManager,
    target: str,
    content: str,
    metadata: dict[str, str | list[str] | int | float | bool] | None,
) -> ObsidianNoteManagerToolResult:
    """Update existing note, replacing content and optionally metadata.

    Args:
        vault_manager: VaultManager instance
        target: Note path to update
        content: New note content
        metadata: Optional new frontmatter metadata

    Returns:
        ObsidianNoteManagerToolResult with update details
    """
    logger.info("vault.update_note_started", target=target)

    try:
        # Check note exists
        note = vault_manager.read_note(target)

        # Use existing frontmatter if no new metadata provided
        if metadata is None and note.frontmatter:
            metadata_dict: dict[str, str | list[str] | int | float | bool] = {
                "tags": note.frontmatter.tags,
            }
            if note.frontmatter.title:
                metadata_dict["title"] = note.frontmatter.title
            if note.frontmatter.created:
                metadata_dict["created"] = note.frontmatter.created.isoformat()
            if note.frontmatter.modified:
                metadata_dict["modified"] = note.frontmatter.modified.isoformat()
            # Add custom fields
            for key, value in note.frontmatter.custom.items():
                metadata_dict[key] = value
            metadata = metadata_dict

        # Overwrite note
        vault_manager.write_note(target, content, metadata, overwrite=True)

        logger.info("vault.update_note_completed", target=target)

        return ObsidianNoteManagerToolResult(
            success=True,
            operation="update_note",
            affected_count=1,
            affected_paths=[target],
            message=f"Updated note: {target}",
        )

    except FileNotFoundError:
        logger.warning("vault.update_note_not_found", target=target)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="update_note",
            affected_count=0,
            affected_paths=[],
            message=f"Note not found: {target}",
        )
    except Exception as e:
        logger.error("vault.update_note_failed", target=target, error=str(e), exc_info=True)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="update_note",
            affected_count=0,
            affected_paths=[],
            message=f"Failed to update note: {e!s}",
        )


async def execute_append_note(
    vault_manager: VaultManager,
    target: str,
    content: str,
) -> ObsidianNoteManagerToolResult:
    """Append content to existing note.

    Args:
        vault_manager: VaultManager instance
        target: Note path to append to
        content: Content to append

    Returns:
        ObsidianNoteManagerToolResult with append details
    """
    logger.info("vault.append_note_started", target=target)

    try:
        vault_manager.append_to_note(target, content)

        logger.info("vault.append_note_completed", target=target)

        return ObsidianNoteManagerToolResult(
            success=True,
            operation="append_note",
            affected_count=1,
            affected_paths=[target],
            message=f"Appended to note: {target}",
        )

    except FileNotFoundError:
        logger.warning("vault.append_note_not_found", target=target)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="append_note",
            affected_count=0,
            affected_paths=[],
            message=f"Note not found: {target}",
        )
    except Exception as e:
        logger.error("vault.append_note_failed", target=target, error=str(e), exc_info=True)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="append_note",
            affected_count=0,
            affected_paths=[],
            message=f"Failed to append to note: {e!s}",
        )


async def execute_delete_note(
    vault_manager: VaultManager,
    target: str,
    confirm_destructive: bool,
) -> ObsidianNoteManagerToolResult:
    """Delete note with safety confirmation.

    Args:
        vault_manager: VaultManager instance
        target: Note path to delete
        confirm_destructive: Must be True to proceed

    Returns:
        ObsidianNoteManagerToolResult with deletion details
    """
    if not confirm_destructive:
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="delete_note",
            affected_count=0,
            affected_paths=[],
            message="Invalid operation: delete_note requires confirm_destructive=True to prevent accidental data loss.",
        )

    logger.info("vault.delete_note_started", target=target)

    try:
        vault_manager.delete_note(target)

        logger.info("vault.delete_note_completed", target=target)

        return ObsidianNoteManagerToolResult(
            success=True,
            operation="delete_note",
            affected_count=1,
            affected_paths=[target],
            message=f"Deleted note: {target}",
        )

    except FileNotFoundError:
        logger.warning("vault.delete_note_not_found", target=target)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="delete_note",
            affected_count=0,
            affected_paths=[],
            message=f"Note not found: {target}",
        )
    except Exception as e:
        logger.error("vault.delete_note_failed", target=target, error=str(e), exc_info=True)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="delete_note",
            affected_count=0,
            affected_paths=[],
            message=f"Failed to delete note: {e!s}",
        )


async def execute_move_note(
    vault_manager: VaultManager,
    target: str,
    destination: str,
    create_folders: bool,
) -> ObsidianNoteManagerToolResult:
    """Move note to new location.

    Args:
        vault_manager: VaultManager instance
        target: Current note path
        destination: Destination path
        create_folders: Create parent folders if missing

    Returns:
        ObsidianNoteManagerToolResult with move details
    """
    logger.info("vault.move_note_started", target=target, destination=destination)

    try:
        vault_manager.move_note(target, destination, create_folders=create_folders)

        logger.info("vault.move_note_completed", target=target, destination=destination)

        return ObsidianNoteManagerToolResult(
            success=True,
            operation="move_note",
            affected_count=1,
            affected_paths=[destination],
            message=f"Moved note from {target} to {destination}",
        )

    except FileNotFoundError as e:
        logger.warning("vault.move_note_not_found", target=target, error=str(e))
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="move_note",
            affected_count=0,
            affected_paths=[],
            message=f"Note not found or destination issue: {e!s}",
        )
    except Exception as e:
        logger.error(
            "vault.move_note_failed", target=target, destination=destination, error=str(e), exc_info=True
        )
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="move_note",
            affected_count=0,
            affected_paths=[],
            message=f"Failed to move note: {e!s}",
        )


async def execute_create_folder(
    vault_manager: VaultManager,
    target: str,
    exist_ok: bool,
) -> ObsidianNoteManagerToolResult:
    """Create folder in vault.

    Args:
        vault_manager: VaultManager instance
        target: Folder path to create
        exist_ok: If True, don't error if folder exists

    Returns:
        ObsidianNoteManagerToolResult with creation details
    """
    logger.info("vault.create_folder_started", target=target)

    try:
        vault_manager.create_folder(target, exist_ok=exist_ok)

        logger.info("vault.create_folder_completed", target=target)

        return ObsidianNoteManagerToolResult(
            success=True,
            operation="create_folder",
            affected_count=1,
            affected_paths=[target],
            message=f"Created folder: {target}",
        )

    except FileExistsError:
        logger.warning("vault.create_folder_exists", target=target)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="create_folder",
            affected_count=0,
            affected_paths=[],
            message=f"Folder already exists: {target}",
        )
    except Exception as e:
        logger.error("vault.create_folder_failed", target=target, error=str(e), exc_info=True)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="create_folder",
            affected_count=0,
            affected_paths=[],
            message=f"Failed to create folder: {e!s}",
        )


async def execute_delete_folder(
    vault_manager: VaultManager,
    target: str,
    confirm_destructive: bool,
    recursive: bool,
) -> ObsidianNoteManagerToolResult:
    """Delete folder with safety confirmation.

    Args:
        vault_manager: VaultManager instance
        target: Folder path to delete
        confirm_destructive: Must be True to proceed
        recursive: If True, delete non-empty folders

    Returns:
        ObsidianNoteManagerToolResult with deletion details
    """
    if not confirm_destructive:
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="delete_folder",
            affected_count=0,
            affected_paths=[],
            message="Invalid operation: delete_folder requires confirm_destructive=True to prevent accidental data loss.",
        )

    logger.info("vault.delete_folder_started", target=target, recursive=recursive)

    try:
        vault_manager.delete_folder(target, recursive=recursive)

        logger.info("vault.delete_folder_completed", target=target)

        return ObsidianNoteManagerToolResult(
            success=True,
            operation="delete_folder",
            affected_count=1,
            affected_paths=[target],
            message=f"Deleted folder: {target}",
        )

    except FileNotFoundError:
        logger.warning("vault.delete_folder_not_found", target=target)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="delete_folder",
            affected_count=0,
            affected_paths=[],
            message=f"Folder not found: {target}",
        )
    except OSError as e:
        logger.warning("vault.delete_folder_not_empty", target=target, error=str(e))
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="delete_folder",
            affected_count=0,
            affected_paths=[],
            message=f"Folder not empty (use recursive=True to delete): {target}",
        )
    except Exception as e:
        logger.error("vault.delete_folder_failed", target=target, error=str(e), exc_info=True)
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="delete_folder",
            affected_count=0,
            affected_paths=[],
            message=f"Failed to delete folder: {e!s}",
        )


async def execute_move_folder(
    vault_manager: VaultManager,
    target: str,
    destination: str,
) -> ObsidianNoteManagerToolResult:
    """Move folder to new location.

    Args:
        vault_manager: VaultManager instance
        target: Current folder path
        destination: Destination path

    Returns:
        ObsidianNoteManagerToolResult with move details
    """
    logger.info("vault.move_folder_started", target=target, destination=destination)

    try:
        vault_manager.move_folder(target, destination)

        logger.info("vault.move_folder_completed", target=target, destination=destination)

        return ObsidianNoteManagerToolResult(
            success=True,
            operation="move_folder",
            affected_count=1,
            affected_paths=[destination],
            message=f"Moved folder from {target} to {destination}",
        )

    except FileNotFoundError as e:
        logger.warning("vault.move_folder_not_found", target=target, error=str(e))
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="move_folder",
            affected_count=0,
            affected_paths=[],
            message=f"Folder not found or destination issue: {e!s}",
        )
    except Exception as e:
        logger.error(
            "vault.move_folder_failed", target=target, destination=destination, error=str(e), exc_info=True
        )
        return ObsidianNoteManagerToolResult(
            success=False,
            operation="move_folder",
            affected_count=0,
            affected_paths=[],
            message=f"Failed to move folder: {e!s}",
        )


async def execute_bulk_tag(
    vault_manager: VaultManager,
    targets: list[str],
    metadata: dict[str, str | list[str] | int | float | bool],
) -> ObsidianNoteManagerToolResult:
    """Add tags to multiple notes.

    Args:
        vault_manager: VaultManager instance
        targets: List of note paths to tag
        metadata: Metadata to add (typically contains 'tags' key)

    Returns:
        ObsidianNoteManagerToolResult with bulk operation details
    """
    logger.info("vault.bulk_tag_started", target_count=len(targets))

    succeeded: list[str] = []
    failed: list[dict[str, str]] = []

    for target in targets:
        try:
            # Read existing note
            note = vault_manager.read_note(target)

            # Merge tags (deduplicate)
            existing_tags = note.frontmatter.tags if note.frontmatter else []
            new_tags_raw = metadata.get("tags", [])

            # Normalize new_tags to list of strings
            new_tags: list[str] = []
            if isinstance(new_tags_raw, str):
                new_tags = [new_tags_raw]
            elif isinstance(new_tags_raw, list):
                new_tags = new_tags_raw

            merged_tags = list(set(existing_tags + new_tags))

            # Build metadata dict
            metadata_dict: dict[str, str | list[str] | int | float | bool] = {"tags": merged_tags}
            if note.frontmatter:
                if note.frontmatter.title:
                    metadata_dict["title"] = note.frontmatter.title
                if note.frontmatter.created:
                    metadata_dict["created"] = note.frontmatter.created.isoformat()
                if note.frontmatter.modified:
                    metadata_dict["modified"] = note.frontmatter.modified.isoformat()
                for key, value in note.frontmatter.custom.items():
                    if key not in metadata_dict:
                        metadata_dict[key] = value

            # Add any other metadata from input (besides tags)
            for key, value in metadata.items():
                if key != "tags":
                    metadata_dict[key] = value

            # Write back
            vault_manager.write_note(target, note.content, metadata_dict, overwrite=True)
            succeeded.append(target)

        except Exception as e:
            logger.warning("vault.bulk_tag_item_failed", target=target, error=str(e))
            failed.append({"path": target, "reason": str(e)})

    logger.info("vault.bulk_tag_completed", succeeded_count=len(succeeded), failed_count=len(failed))

    partial_success = len(succeeded) > 0 and len(failed) > 0

    return ObsidianNoteManagerToolResult(
        success=len(succeeded) > 0,
        operation="bulk_tag",
        affected_count=len(succeeded),
        affected_paths=succeeded,
        message=f"Tagged {len(succeeded)}/{len(targets)} notes",
        partial_success=partial_success if partial_success else None,
        failures=failed if failed else None,
    )


async def execute_bulk_move(
    vault_manager: VaultManager,
    targets: list[str],
    destination_folder: str,
    create_folders: bool,
) -> ObsidianNoteManagerToolResult:
    """Move multiple notes to a destination folder.

    Args:
        vault_manager: VaultManager instance
        targets: List of note paths to move
        destination_folder: Folder to move notes into
        create_folders: Create destination folder if missing

    Returns:
        ObsidianNoteManagerToolResult with bulk operation details
    """
    logger.info("vault.bulk_move_started", target_count=len(targets), destination=destination_folder)

    succeeded: list[str] = []
    failed: list[dict[str, str]] = []

    for target in targets:
        try:
            # Calculate destination path (preserve filename)
            from pathlib import Path

            filename = Path(target).name
            dest_path = f"{destination_folder}/{filename}"

            # Move note
            vault_manager.move_note(target, dest_path, create_folders=create_folders)
            succeeded.append(dest_path)

        except Exception as e:
            logger.warning("vault.bulk_move_item_failed", target=target, error=str(e))
            failed.append({"path": target, "reason": str(e)})

    logger.info("vault.bulk_move_completed", succeeded_count=len(succeeded), failed_count=len(failed))

    partial_success = len(succeeded) > 0 and len(failed) > 0

    return ObsidianNoteManagerToolResult(
        success=len(succeeded) > 0,
        operation="bulk_move",
        affected_count=len(succeeded),
        affected_paths=succeeded,
        message=f"Moved {len(succeeded)}/{len(targets)} notes to {destination_folder}",
        partial_success=partial_success if partial_success else None,
        failures=failed if failed else None,
    )


async def execute_bulk_update_metadata(
    vault_manager: VaultManager,
    targets: list[str],
    metadata: dict[str, str | list[str] | int | float | bool],
) -> ObsidianNoteManagerToolResult:
    """Update metadata for multiple notes.

    Args:
        vault_manager: VaultManager instance
        targets: List of note paths to update
        metadata: Metadata to apply to all notes

    Returns:
        ObsidianNoteManagerToolResult with bulk operation details
    """
    logger.info("vault.bulk_update_metadata_started", target_count=len(targets))

    succeeded: list[str] = []
    failed: list[dict[str, str]] = []

    for target in targets:
        try:
            # Read existing note
            note = vault_manager.read_note(target)

            # Build metadata dict (merge existing with new)
            metadata_dict: dict[str, str | list[str] | int | float | bool] = {}
            if note.frontmatter:
                metadata_dict["tags"] = note.frontmatter.tags
                if note.frontmatter.title:
                    metadata_dict["title"] = note.frontmatter.title
                if note.frontmatter.created:
                    metadata_dict["created"] = note.frontmatter.created.isoformat()
                if note.frontmatter.modified:
                    metadata_dict["modified"] = note.frontmatter.modified.isoformat()
                for key, value in note.frontmatter.custom.items():
                    metadata_dict[key] = value

            # Apply new metadata (overwrites existing keys)
            for key, value in metadata.items():
                metadata_dict[key] = value

            # Write back
            vault_manager.write_note(target, note.content, metadata_dict, overwrite=True)
            succeeded.append(target)

        except Exception as e:
            logger.warning("vault.bulk_update_metadata_item_failed", target=target, error=str(e))
            failed.append({"path": target, "reason": str(e)})

    logger.info(
        "vault.bulk_update_metadata_completed", succeeded_count=len(succeeded), failed_count=len(failed)
    )

    partial_success = len(succeeded) > 0 and len(failed) > 0

    return ObsidianNoteManagerToolResult(
        success=len(succeeded) > 0,
        operation="bulk_update_metadata",
        affected_count=len(succeeded),
        affected_paths=succeeded,
        message=f"Updated metadata for {len(succeeded)}/{len(targets)} notes",
        partial_success=partial_success if partial_success else None,
        failures=failed if failed else None,
    )
