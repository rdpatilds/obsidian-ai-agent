"""Service layer for Obsidian Folder Manager tool.

This module implements folder management operations including create, rename,
move, delete, and list with proper security validation and wikilink updates.
"""

import shutil
import time
from pathlib import Path

import aiofiles  # type: ignore[import-untyped]
import aioshutil

from src.shared.logging import get_logger
from src.shared.obsidian_parsers import extract_wikilinks
from src.shared.vault_security import (
    is_critical_folder,
    is_path_allowed,
    validate_folder_name,
    validate_vault_path,
)
from src.tools.obsidian_folder_manager.schemas import (
    FolderInfo,
    FolderOperation,
    FolderOperationResult,
    ManageFolderRequest,
)


logger = get_logger(__name__)


async def manage_folder_service(
    request: ManageFolderRequest,
    vault_path: str,
    max_folder_depth: int,
    max_wikilink_scan_notes: int,
) -> FolderOperationResult:
    """Execute folder management operation.

    Args:
        request: ManageFolderRequest with operation details.
        vault_path: Absolute path to Obsidian vault root.
        max_folder_depth: Maximum depth for recursive LIST operations.
        max_wikilink_scan_notes: Maximum notes to scan for wikilink updates.

    Returns:
        FolderOperationResult with operation result and metadata.

    Raises:
        ValueError: If path is invalid, blocked, or operation validation fails.
        FileNotFoundError: If folder doesn't exist for required operations.
        OSError: If file operations fail.
    """
    start_time = time.perf_counter()

    # Validate and resolve path
    full_path_str = validate_vault_path(vault_path, request.path)
    full_path = Path(full_path_str)
    vault_root = Path(vault_path).resolve()

    # Check if path is critical folder (for RENAME/DELETE/MOVE operations)
    if request.operation in {FolderOperation.RENAME, FolderOperation.DELETE, FolderOperation.MOVE}:
        if is_critical_folder(full_path, vault_root):
            logger.error(
                "critical_folder_operation_blocked",
                path=request.path,
                operation=request.operation.value,
            )
            msg = f"Cannot {request.operation.value} critical folder: {request.path}"
            raise ValueError(msg)

    logger.info(
        "folder_operation_started",
        path=request.path,
        operation=request.operation.value,
        dry_run=request.dry_run,
    )

    # Execute operation
    if request.operation == FolderOperation.CREATE:
        result = await _create_folder(full_path, request, vault_root)

    elif request.operation == FolderOperation.RENAME:
        result = await _rename_folder(
            full_path, request, vault_root, max_wikilink_scan_notes
        )

    elif request.operation == FolderOperation.MOVE:
        result = await _move_folder(
            full_path, request, vault_path, vault_root, max_wikilink_scan_notes
        )

    elif request.operation == FolderOperation.DELETE:
        result = await _delete_folder(full_path, request, vault_root)

    elif request.operation == FolderOperation.LIST:
        result = await _list_folder(full_path, request, vault_root, max_folder_depth)

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "folder_operation_completed",
        path=request.path,
        operation=request.operation.value,
        success=result.success,
        duration_ms=duration_ms,
    )

    return result


async def _create_folder(
    full_path: Path,
    request: ManageFolderRequest,
    vault_root: Path,
) -> FolderOperationResult:
    """Create a new folder with optional parent creation.

    Args:
        full_path: Absolute path to folder to create.
        request: Request with create parameters.
        vault_root: Vault root path for relative path calculation.

    Returns:
        FolderOperationResult with creation status.

    Raises:
        ValueError: If path exists as file or parent doesn't exist.
        OSError: If folder creation fails.
    """
    # Check if path already exists
    if full_path.exists():
        if full_path.is_dir():
            # Idempotent: folder already exists
            logger.info("folder_already_exists", path=str(full_path))
            return FolderOperationResult(
                success=True,
                path=request.path,
                operation=FolderOperation.CREATE,
                message=f"Folder already exists: {request.path}",
                metadata={"already_existed": True},
                token_estimate=50,
            )
        # Path exists as file
        msg = f"Path exists as file, not folder: {request.path}"
        raise ValueError(msg)

    # Dry run check
    if request.dry_run:
        return FolderOperationResult(
            success=True,
            path=request.path,
            operation=FolderOperation.CREATE,
            message=f"[DRY RUN] Would create folder: {request.path}",
            metadata={"dry_run": True, "parents": request.create_parents},
            token_estimate=50,
        )

    # Create folder
    try:
        full_path.mkdir(parents=request.create_parents, exist_ok=False)
        logger.info(
            "folder_created",
            path=str(full_path),
            parents_created=request.create_parents,
        )

        return FolderOperationResult(
            success=True,
            path=request.path,
            operation=FolderOperation.CREATE,
            message=f"Successfully created folder: {request.path}",
            metadata={"parents_created": request.create_parents},
            token_estimate=50,
        )

    except FileNotFoundError as e:
        msg = "Parent directory does not exist. Use create_parents=True to create parent folders."
        logger.error("folder_creation_failed", path=str(full_path), error=str(e))
        raise ValueError(msg) from e


async def _rename_folder(
    full_path: Path,
    request: ManageFolderRequest,
    vault_root: Path,
    max_wikilink_scan_notes: int,
) -> FolderOperationResult:
    """Rename a folder and update wikilinks.

    Args:
        full_path: Absolute path to folder to rename.
        request: Request with rename parameters (new_name).
        vault_root: Vault root path.
        max_wikilink_scan_notes: Maximum notes to scan for wikilink updates.

    Returns:
        FolderOperationResult with rename status and wikilink update count.

    Raises:
        FileNotFoundError: If folder doesn't exist.
        ValueError: If new_name is invalid or destination exists.
    """
    if not full_path.exists():
        msg = f"Folder not found: {request.path}"
        raise FileNotFoundError(msg)

    if not full_path.is_dir():
        msg = f"Path is not a folder: {request.path}"
        raise ValueError(msg)

    # Validate new folder name
    assert request.new_name is not None  # Validated by model_validator
    validate_folder_name(request.new_name)

    # Calculate new path (rename in same directory)
    new_path = full_path.parent / request.new_name.strip()

    # Check if destination exists (unless case-only rename on case-insensitive FS)
    if new_path.exists() and new_path.resolve() != full_path.resolve():
        msg = f"Destination already exists: {new_path.relative_to(vault_root)}"
        raise ValueError(msg)

    # Dry run check
    if request.dry_run:
        return FolderOperationResult(
            success=True,
            path=request.path,
            operation=FolderOperation.RENAME,
            message=f"[DRY RUN] Would rename {request.path} to {request.new_name}",
            new_path=str(new_path.relative_to(vault_root)),
            metadata={"dry_run": True, "update_wikilinks": request.update_wikilinks},
            token_estimate=50,
        )

    # Handle case-only rename (temp rename strategy)
    if new_path.resolve() == full_path.resolve():
        # Case-only rename on case-insensitive filesystem
        temp_path = full_path.parent / f"_temp_{request.new_name}_{int(time.time())}"
        await aioshutil.move(str(full_path), str(temp_path))
        full_path = temp_path

    # Rename folder
    await aioshutil.move(str(full_path), str(new_path))
    logger.info("folder_renamed", old_path=str(full_path), new_path=str(new_path))

    # Update wikilinks if requested
    links_updated = 0
    if request.update_wikilinks:
        old_relative = full_path.relative_to(vault_root)
        new_relative = new_path.relative_to(vault_root)
        links_updated = await _update_wikilinks_for_folder_rename(
            vault_root, old_relative, new_relative, max_wikilink_scan_notes
        )

    return FolderOperationResult(
        success=True,
        path=request.path,
        operation=FolderOperation.RENAME,
        message=f"Successfully renamed {request.path} to {request.new_name}",
        new_path=str(new_path.relative_to(vault_root)),
        metadata={"links_updated": links_updated},
        token_estimate=80,
    )


async def _move_folder(
    full_path: Path,
    request: ManageFolderRequest,
    vault_path: str,
    vault_root: Path,
    max_wikilink_scan_notes: int,
) -> FolderOperationResult:
    """Move a folder to a new location and update wikilinks.

    Args:
        full_path: Absolute path to folder to move.
        request: Request with move parameters (destination).
        vault_path: Vault path string for validation.
        vault_root: Vault root path.
        max_wikilink_scan_notes: Maximum notes to scan for wikilink updates.

    Returns:
        FolderOperationResult with move status and wikilink update count.

    Raises:
        FileNotFoundError: If source folder doesn't exist.
        ValueError: If destination is invalid or circular move detected.
    """
    if not full_path.exists():
        msg = f"Folder not found: {request.path}"
        raise FileNotFoundError(msg)

    if not full_path.is_dir():
        msg = f"Path is not a folder: {request.path}"
        raise ValueError(msg)

    # Validate and resolve destination
    assert request.destination is not None  # Validated by model_validator
    dest_path_str = validate_vault_path(vault_path, request.destination)
    dest_path = Path(dest_path_str)

    # Detect circular move (moving folder into itself)
    try:
        dest_path.relative_to(full_path)
        msg = f"Cannot move folder into itself: {request.path} -> {request.destination}"
        raise ValueError(msg)
    except ValueError:
        # dest_path is not relative to full_path, so it's safe
        pass

    # Calculate final destination path
    final_dest = dest_path / full_path.name

    # Check if destination already exists
    if final_dest.exists():
        msg = f"Destination already exists: {final_dest.relative_to(vault_root)}"
        raise ValueError(msg)

    # Dry run check
    if request.dry_run:
        return FolderOperationResult(
            success=True,
            path=request.path,
            operation=FolderOperation.MOVE,
            message=f"[DRY RUN] Would move {request.path} to {request.destination}",
            new_path=str(final_dest.relative_to(vault_root)),
            metadata={"dry_run": True, "update_wikilinks": request.update_wikilinks},
            token_estimate=50,
        )

    # Create destination parent if needed
    dest_path.mkdir(parents=True, exist_ok=True)

    # Move folder
    await aioshutil.move(str(full_path), str(final_dest))
    logger.info("folder_moved", old_path=str(full_path), new_path=str(final_dest))

    # Update wikilinks if requested
    links_updated = 0
    if request.update_wikilinks:
        old_relative = full_path.relative_to(vault_root)
        new_relative = final_dest.relative_to(vault_root)
        links_updated = await _update_wikilinks_for_folder_rename(
            vault_root, old_relative, new_relative, max_wikilink_scan_notes
        )

    return FolderOperationResult(
        success=True,
        path=request.path,
        operation=FolderOperation.MOVE,
        message=f"Successfully moved {request.path} to {request.destination}",
        new_path=str(final_dest.relative_to(vault_root)),
        metadata={"links_updated": links_updated},
        token_estimate=80,
    )


async def _delete_folder(
    full_path: Path,
    request: ManageFolderRequest,
    vault_root: Path,
) -> FolderOperationResult:
    """Delete a folder with confirmation and wikilink checking.

    Args:
        full_path: Absolute path to folder to delete.
        request: Request with delete parameters (force, confirm_path, check_wikilinks).
        vault_root: Vault root path.

    Returns:
        FolderOperationResult with deletion status and affected notes.

    Raises:
        FileNotFoundError: If folder doesn't exist.
        ValueError: If folder is non-empty without force or confirmation missing.
    """
    if not full_path.exists():
        msg = f"Folder not found: {request.path}"
        raise FileNotFoundError(msg)

    if not full_path.is_dir():
        msg = f"Path is not a folder: {request.path}"
        raise ValueError(msg)

    # Check if folder is empty
    contents = list(full_path.iterdir())
    is_empty = len(contents) == 0

    if not is_empty and not request.force:
        msg = f"Folder is not empty ({len(contents)} items). Use force=True to delete non-empty folder."
        raise ValueError(msg)

    # Check for incoming wikilinks if requested
    affected_notes: list[str] = []
    if request.check_wikilinks:
        affected_notes = await _check_incoming_wikilinks(full_path, vault_root)

    # Dry run check
    if request.dry_run:
        return FolderOperationResult(
            success=True,
            path=request.path,
            operation=FolderOperation.DELETE,
            message=f"[DRY RUN] Would delete folder: {request.path} ({len(contents)} items)",
            metadata={
                "dry_run": True,
                "item_count": len(contents),
                "affected_notes": affected_notes,
            },
            token_estimate=100 if affected_notes else 50,
        )

    # Delete folder
    if is_empty:
        full_path.rmdir()
    else:
        shutil.rmtree(str(full_path))

    logger.info(
        "folder_deleted",
        path=str(full_path),
        item_count=len(contents),
        affected_notes_count=len(affected_notes),
    )

    message = f"Successfully deleted folder: {request.path}"
    if affected_notes:
        message += f" (Warning: {len(affected_notes)} notes may have broken links)"

    return FolderOperationResult(
        success=True,
        path=request.path,
        operation=FolderOperation.DELETE,
        message=message,
        metadata={
            "item_count": len(contents),
            "affected_notes": affected_notes[:10],  # Limit to first 10
            "affected_notes_count": len(affected_notes),
        },
        token_estimate=100 if affected_notes else 50,
    )


async def _list_folder(
    full_path: Path,
    request: ManageFolderRequest,
    vault_root: Path,
    max_folder_depth: int,
) -> FolderOperationResult:
    """List folder contents with optional stats and pagination.

    Args:
        full_path: Absolute path to folder to list.
        request: Request with list parameters (recursive, include_stats, pagination).
        vault_root: Vault root path.
        max_folder_depth: Maximum depth for recursive listing (safety limit).

    Returns:
        FolderOperationResult with folder list and metadata.

    Raises:
        FileNotFoundError: If folder doesn't exist.
        ValueError: If path is not a folder.
    """
    if not full_path.exists():
        msg = f"Folder not found: {request.path}"
        raise FileNotFoundError(msg)

    if not full_path.is_dir():
        msg = f"Path is not a folder: {request.path}"
        raise ValueError(msg)

    # Collect folders
    folders: list[FolderInfo] = []

    if request.recursive:
        # Recursive listing with depth limit
        depth_limit = min(max_folder_depth, 5)  # Safety: max 5 levels
        folders = await _collect_folders_recursive(
            full_path, vault_root, depth_limit, request.include_stats
        )
    else:
        # Immediate children only
        for item in full_path.iterdir():
            if item.is_dir() and is_path_allowed(str(item)):
                folder_info = await _get_folder_info(item, vault_root, request.include_stats, 0)
                folders.append(folder_info)

    # Sort by path
    folders.sort(key=lambda f: f.path)

    # Pagination
    total_folders = len(folders)
    offset = request.offset
    max_results = request.max_results
    paginated_folders = folders[offset : offset + max_results]
    has_more = offset + max_results < total_folders

    # Token estimate based on format
    if request.response_format.value == "minimal":
        token_estimate = 50 + len(paginated_folders) * 10
    elif request.response_format.value == "concise":
        token_estimate = 100 + len(paginated_folders) * 20
    else:  # detailed
        token_estimate = 150 + len(paginated_folders) * 40

    message = f"Found {total_folders} folders"
    if request.recursive:
        message += " (recursive)"
    if has_more:
        message += f", showing {len(paginated_folders)} (offset {offset})"

    return FolderOperationResult(
        success=True,
        path=request.path,
        operation=FolderOperation.LIST,
        message=message,
        metadata={
            "folders": [folder.model_dump() for folder in paginated_folders],
            "total_folders": total_folders,
            "returned": len(paginated_folders),
            "has_more": has_more,
            "offset": offset,
            "max_results": max_results,
        },
        token_estimate=token_estimate,
    )


async def _collect_folders_recursive(
    folder_path: Path,
    vault_root: Path,
    max_depth: int,
    include_stats: bool,
    current_depth: int = 0,
) -> list[FolderInfo]:
    """Recursively collect folders up to max depth.

    Args:
        folder_path: Folder to list.
        vault_root: Vault root path.
        max_depth: Maximum depth to traverse.
        include_stats: Whether to include folder statistics.
        current_depth: Current recursion depth.

    Returns:
        List of FolderInfo objects.
    """
    folders: list[FolderInfo] = []

    if current_depth >= max_depth:
        return folders

    for item in folder_path.iterdir():
        if item.is_dir() and is_path_allowed(str(item)):
            folder_info = await _get_folder_info(item, vault_root, include_stats, current_depth)
            folders.append(folder_info)

            # Recurse
            subfolders = await _collect_folders_recursive(
                item, vault_root, max_depth, include_stats, current_depth + 1
            )
            folders.extend(subfolders)

    return folders


async def _get_folder_info(
    folder_path: Path,
    vault_root: Path,
    include_stats: bool,
    depth: int,
) -> FolderInfo:
    """Get information about a folder.

    Args:
        folder_path: Folder to get info for.
        vault_root: Vault root path.
        include_stats: Whether to include statistics.
        depth: Depth from listing root.

    Returns:
        FolderInfo object.
    """
    relative_path = folder_path.relative_to(vault_root)

    folder_info = FolderInfo(
        path=str(relative_path).replace("\\", "/"),  # Normalize for cross-platform
        name=folder_path.name,
        depth=depth,
    )

    if include_stats:
        # Count notes
        note_count = len(list(folder_path.glob("*.md")))

        # Calculate total size
        total_size = sum(f.stat().st_size for f in folder_path.rglob("*") if f.is_file())

        # Get modified time
        modified_timestamp = folder_path.stat().st_mtime

        folder_info.note_count = note_count
        folder_info.total_size_bytes = total_size
        folder_info.modified_timestamp = modified_timestamp

    return folder_info


async def _update_wikilinks_for_folder_rename(
    vault_root: Path,
    old_folder_path: Path,
    new_folder_path: Path,
    max_notes: int,
) -> int:
    """Update wikilinks in all vault notes after folder rename/move.

    This is a best-effort operation that scans notes and updates wikilinks
    that reference files in the renamed/moved folder.

    Args:
        vault_root: Vault root path.
        old_folder_path: Old folder path (relative to vault root).
        new_folder_path: New folder path (relative to vault root).
        max_notes: Maximum number of notes to scan (safety limit).

    Returns:
        Number of notes with updated wikilinks.
    """
    notes_updated = 0
    notes_scanned = 0

    # Normalize paths for comparison (use forward slashes)
    old_prefix = str(old_folder_path).replace("\\", "/")
    new_prefix = str(new_folder_path).replace("\\", "/")

    logger.info(
        "wikilink_update_started",
        old_prefix=old_prefix,
        new_prefix=new_prefix,
        max_notes=max_notes,
    )

    try:
        # Scan all markdown files in vault
        for note_path in vault_root.rglob("*.md"):
            if notes_scanned >= max_notes:
                logger.warning(
                    "wikilink_scan_limit_reached",
                    notes_scanned=notes_scanned,
                    max_notes=max_notes,
                )
                break

            notes_scanned += 1

            # Skip notes inside the moved folder itself
            try:
                note_path.relative_to(vault_root / new_folder_path)
                continue  # Note is inside moved folder, skip it
            except ValueError:
                pass

            # Read note content
            try:
                async with aiofiles.open(note_path, encoding="utf-8") as f:
                    content = await f.read()

                # Extract wikilinks
                wikilinks = extract_wikilinks(content)
                has_updates = False
                updated_content = content

                # Check each wikilink
                for link in wikilinks:
                    # Normalize target
                    target = link.target.replace("\\", "/")

                    # Check if target starts with old folder path
                    if target.startswith(old_prefix + "/") or target == old_prefix:
                        # Replace old path with new path
                        new_target = target.replace(old_prefix, new_prefix, 1)

                        # Build old and new wikilink syntax
                        if link.display_text:
                            old_link = f"[[{link.target}|{link.display_text}]]"
                            new_link = f"[[{new_target}|{link.display_text}]]"
                        elif link.heading:
                            old_link = f"[[{link.target}#{link.heading}]]"
                            new_link = f"[[{new_target}#{link.heading}]]"
                        else:
                            old_link = f"[[{link.target}]]"
                            new_link = f"[[{new_target}]]"

                        # Handle embeds
                        if link.is_embed:
                            old_link = "!" + old_link
                            new_link = "!" + new_link

                        # Replace in content
                        updated_content = updated_content.replace(old_link, new_link)
                        has_updates = True

                # Write updated content if changes were made
                if has_updates:
                    async with aiofiles.open(note_path, "w", encoding="utf-8") as f:
                        await f.write(updated_content)
                    notes_updated += 1
                    logger.debug(
                        "wikilinks_updated_in_note",
                        note_path=str(note_path.relative_to(vault_root)),
                    )

            except Exception as e:
                # Best-effort: log error but continue
                logger.warning(
                    "wikilink_update_error",
                    note_path=str(note_path),
                    error=str(e),
                )
                continue

        logger.info(
            "wikilink_update_completed",
            notes_scanned=notes_scanned,
            notes_updated=notes_updated,
        )

    except Exception as e:
        logger.exception("wikilink_update_failed", error=str(e))
        # Don't raise - this is best-effort

    return notes_updated


async def _check_incoming_wikilinks(
    folder_path: Path,
    vault_root: Path,
) -> list[str]:
    """Check for notes that link to files in the folder being deleted.

    Args:
        folder_path: Folder being deleted.
        vault_root: Vault root path.

    Returns:
        List of note paths (relative to vault) that have links to folder contents.
    """
    affected_notes: list[str] = []
    folder_relative = folder_path.relative_to(vault_root)
    folder_prefix = str(folder_relative).replace("\\", "/")

    try:
        # Scan all markdown files NOT in the folder being deleted
        for note_path in vault_root.rglob("*.md"):
            # Skip notes inside the folder being deleted
            try:
                note_path.relative_to(folder_path)
                continue  # Note is inside folder, skip
            except ValueError:
                pass

            # Read note content
            try:
                async with aiofiles.open(note_path, encoding="utf-8") as f:
                    content = await f.read()

                # Extract wikilinks
                wikilinks = extract_wikilinks(content)

                # Check if any wikilink targets files in the folder
                for link in wikilinks:
                    target = link.target.replace("\\", "/")
                    if target.startswith(folder_prefix + "/") or target == folder_prefix:
                        note_relative = str(note_path.relative_to(vault_root))
                        affected_notes.append(note_relative.replace("\\", "/"))
                        break  # Found a link, add note and move on

            except Exception as e:
                # Best-effort: log error but continue
                logger.warning(
                    "wikilink_check_error",
                    note_path=str(note_path),
                    error=str(e),
                )
                continue

    except Exception as e:
        logger.exception("wikilink_check_failed", error=str(e))

    return affected_notes
