"""Service layer for Obsidian Vault Organizer tool.

Implements batch organization operations: move, tag, archive, delete.
"""

import shutil
from datetime import datetime
from pathlib import Path

import aiofiles  # type: ignore
import frontmatter  # type: ignore

from src.shared.logging import get_logger
from src.shared.obsidian_parsers import extract_frontmatter_safely
from src.shared.vault_security import is_path_allowed, validate_vault_path
from src.tools.obsidian_vault_organizer.schemas import (
    NoteOperationResult,
    OrganizeOperation,
    OrganizeRequest,
    OrganizeResponse,
)


logger = get_logger(__name__)


async def organize_vault_service(
    request: OrganizeRequest,
    vault_path: str,
) -> OrganizeResponse:
    """Execute batch vault organization operation.

    Args:
        request: Organization request with operation and parameters.
        vault_path: Absolute path to Obsidian vault root.

    Returns:
        Organization response with results for each note.

    Raises:
        ValueError: If paths are invalid or security checks fail.
        FileNotFoundError: If note doesn't exist.
    """
    logger.info(
        "organize_vault_started",
        operation=request.operation.value,
        note_count=len(request.notes),
        dry_run=request.dry_run,
    )

    vault_root = Path(vault_path)
    if not vault_root.exists():
        raise ValueError(f"Vault path does not exist: {vault_path}")

    results: list[NoteOperationResult] = []
    succeeded_operations: list[tuple[Path, Path | None]] = []  # For rollback

    try:
        for note_path_str in request.notes:
            try:
                # Validate path security
                full_path_str = validate_vault_path(vault_path, note_path_str)
                full_path = Path(full_path_str)

                if not is_path_allowed(full_path_str):
                    results.append(
                        NoteOperationResult(
                            path=note_path_str,
                            success=False,
                            message="Path not allowed (blocked directory or unsupported file type)",
                        )
                    )
                    continue

                # Check file exists (except for dry-run)
                if not request.dry_run and not full_path.exists():
                    results.append(
                        NoteOperationResult(
                            path=note_path_str,
                            success=False,
                            message=f"File not found: {note_path_str}",
                        )
                    )
                    continue

                # Execute operation
                if request.operation == OrganizeOperation.MOVE:
                    result = await _execute_move(
                        full_path,
                        vault_root,
                        request.destination,  # type: ignore
                        note_path_str,
                        request.dry_run,
                    )
                elif request.operation == OrganizeOperation.TAG:
                    result = await _execute_tag(
                        full_path,
                        note_path_str,
                        request.tags_to_add or [],
                        request.tags_to_remove or [],
                        request.dry_run,
                    )
                elif request.operation == OrganizeOperation.ARCHIVE:
                    result = await _execute_archive(
                        full_path,
                        vault_root,
                        note_path_str,
                        request.destination,  # Optional: auto-generates if None
                        request.dry_run,
                    )
                else:  # request.operation == OrganizeOperation.DELETE
                    result = await _execute_delete(
                        full_path,
                        note_path_str,
                        request.require_confirmation,
                        request.dry_run,
                    )

                results.append(result)

                # Track successful operations for rollback
                if result.success and not request.dry_run:
                    if result.new_path:
                        succeeded_operations.append((full_path, Path(vault_root / result.new_path)))
                    else:
                        succeeded_operations.append((full_path, None))
                # If operation failed and we need atomic behavior, rollback
                elif request.operation in (OrganizeOperation.MOVE, OrganizeOperation.ARCHIVE):
                    if not request.dry_run and not result.success and succeeded_operations:
                        await _rollback_operations(succeeded_operations, request.operation)
                        logger.warning(
                            "batch_operation_rolled_back",
                            operation=request.operation.value,
                            rollback_count=len(succeeded_operations),
                            reason=result.message,
                        )
                        return OrganizeResponse(
                            operation=request.operation,
                            results=results,
                            total_requested=len(request.notes),
                            total_succeeded=0,
                            total_failed=len(results),
                            rolled_back=True,
                            dry_run=request.dry_run,
                            message=f"Operation failed and rolled back: {result.message}",
                        )

            except Exception as e:
                logger.exception(
                    "note_operation_failed",
                    note=note_path_str,
                    operation=request.operation.value,
                    error=str(e),
                )
                results.append(
                    NoteOperationResult(
                        path=note_path_str,
                        success=False,
                        message=f"Error: {e!s}",
                    )
                )

                # If any operation fails with exception, rollback for MOVE/ARCHIVE (atomic batch)
                if request.operation in (OrganizeOperation.MOVE, OrganizeOperation.ARCHIVE):
                    if not request.dry_run and succeeded_operations:
                        await _rollback_operations(succeeded_operations, request.operation)
                        logger.warning(
                            "batch_operation_rolled_back",
                            operation=request.operation.value,
                            rollback_count=len(succeeded_operations),
                        )
                        return OrganizeResponse(
                            operation=request.operation,
                            results=results,
                            total_requested=len(request.notes),
                            total_succeeded=0,
                            total_failed=len(request.notes),
                            rolled_back=True,
                            dry_run=request.dry_run,
                            message=f"Operation failed and rolled back: {e!s}",
                        )

        # Calculate totals
        total_succeeded = sum(1 for r in results if r.success)
        total_failed = len(results) - total_succeeded

        message = f"Batch operation completed: {total_succeeded} succeeded, {total_failed} failed"
        if request.dry_run:
            message = f"[DRY RUN] {message}"

        logger.info(
            "organize_vault_completed",
            operation=request.operation.value,
            total_requested=len(request.notes),
            total_succeeded=total_succeeded,
            total_failed=total_failed,
            dry_run=request.dry_run,
        )

        return OrganizeResponse(
            operation=request.operation,
            results=results,
            total_requested=len(request.notes),
            total_succeeded=total_succeeded,
            total_failed=total_failed,
            rolled_back=False,
            dry_run=request.dry_run,
            message=message,
        )

    except Exception:
        logger.exception("organize_vault_failed", operation=request.operation.value)
        raise


async def _execute_move(
    source: Path,
    vault_root: Path,
    destination: str,
    note_path_str: str,
    dry_run: bool,
) -> NoteOperationResult:
    """Execute MOVE operation."""
    dest_dir = vault_root / destination
    dest_path = dest_dir / source.name

    if dry_run:
        relative_dest = dest_path.relative_to(vault_root)
        return NoteOperationResult(
            path=note_path_str,
            success=True,
            message=f"[DRY RUN] Would move to {relative_dest}",
            new_path=str(relative_dest),
        )

    # Create destination directory if needed
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Check if destination already exists
    if dest_path.exists():
        return NoteOperationResult(
            path=note_path_str,
            success=False,
            message=f"Destination already exists: {destination}/{source.name}",
        )

    # Move file
    shutil.move(str(source), str(dest_path))
    relative_dest = dest_path.relative_to(vault_root)

    logger.info("note_moved", source=note_path_str, destination=str(relative_dest))

    return NoteOperationResult(
        path=note_path_str,
        success=True,
        message=f"Moved to {relative_dest}",
        new_path=str(relative_dest),
    )


async def _execute_tag(
    file_path: Path,
    note_path_str: str,
    tags_to_add: list[str],
    tags_to_remove: list[str],
    dry_run: bool,
) -> NoteOperationResult:
    """Execute TAG operation."""
    if dry_run:
        changes = []
        if tags_to_add:
            changes.append(f"add tags: {', '.join(tags_to_add)}")
        if tags_to_remove:
            changes.append(f"remove tags: {', '.join(tags_to_remove)}")
        return NoteOperationResult(
            path=note_path_str,
            success=True,
            message=f"[DRY RUN] Would {' and '.join(changes)}",
        )

    # Read note with frontmatter
    async with aiofiles.open(file_path, encoding="utf-8") as f:
        content = await f.read()

    metadata, body = extract_frontmatter_safely(content)

    # Get current tags (could be list or string)
    tags_value = metadata.get("tags", [])
    current_tags: list[str] = []
    if isinstance(tags_value, str):
        current_tags = [tags_value]
    elif isinstance(tags_value, list):
        current_tags = tags_value
    else:
        current_tags = []

    # Add new tags
    for tag in tags_to_add:
        tag_clean = tag.lstrip("#")
        if tag_clean not in current_tags:
            current_tags.append(tag_clean)

    # Remove tags
    for tag in tags_to_remove:
        tag_clean = tag.lstrip("#")
        if tag_clean in current_tags:
            current_tags.remove(tag_clean)

    # Update metadata
    metadata["tags"] = current_tags

    # Write back
    post = frontmatter.Post(body, **metadata)
    new_content = frontmatter.dumps(post)

    async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
        await f.write(new_content)

    logger.info(
        "note_tags_updated",
        note=note_path_str,
        added=tags_to_add,
        removed=tags_to_remove,
    )

    return NoteOperationResult(
        path=note_path_str,
        success=True,
        message=f"Tags updated: added {len(tags_to_add)}, removed {len(tags_to_remove)}",
    )


async def _execute_archive(
    source: Path,
    vault_root: Path,
    note_path_str: str,
    destination: str | None,
    dry_run: bool,
) -> NoteOperationResult:
    """Execute ARCHIVE operation.

    Args:
        source: Source file path.
        vault_root: Vault root directory.
        note_path_str: Note path string for logging.
        destination: Optional custom archive destination. If None, auto-generates archive/{YYYY-MM-DD}/.
        dry_run: Preview mode.

    Returns:
        Operation result.
    """
    # Auto-generate timestamp-based path if no destination provided
    if destination is None:
        timestamp = datetime.now().strftime("%Y-%m-%d")
        archive_dir = vault_root / "archive" / timestamp
    else:
        archive_dir = vault_root / destination

    archive_path = archive_dir / source.name

    if dry_run:
        relative_archive = archive_path.relative_to(vault_root)
        return NoteOperationResult(
            path=note_path_str,
            success=True,
            message=f"[DRY RUN] Would archive to {relative_archive}",
            new_path=str(relative_archive),
        )

    # Create archive directory
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Check if destination exists
    if archive_path.exists():
        return NoteOperationResult(
            path=note_path_str,
            success=False,
            message=f"Archive destination already exists: {archive_path.relative_to(vault_root)}",
        )

    # Move to archive
    shutil.move(str(source), str(archive_path))
    relative_archive = archive_path.relative_to(vault_root)

    logger.info("note_archived", source=note_path_str, destination=str(relative_archive))

    return NoteOperationResult(
        path=note_path_str,
        success=True,
        message=f"Archived to {relative_archive}",
        new_path=str(relative_archive),
    )


async def _execute_delete(
    file_path: Path,
    note_path_str: str,
    require_confirmation: bool,
    dry_run: bool,
) -> NoteOperationResult:
    """Execute DELETE operation."""
    if dry_run:
        return NoteOperationResult(
            path=note_path_str,
            success=True,
            message="[DRY RUN] Would delete this note",
        )

    if require_confirmation:
        return NoteOperationResult(
            path=note_path_str,
            success=False,
            message="DELETE requires confirmation (set require_confirmation=false to proceed)",
        )

    # Delete file
    file_path.unlink()

    logger.warning("note_deleted", path=note_path_str)

    return NoteOperationResult(
        path=note_path_str,
        success=True,
        message="Note deleted",
    )


async def _rollback_operations(
    operations: list[tuple[Path, Path | None]],
    operation_type: OrganizeOperation,
) -> None:
    """Rollback successful operations after a failure.

    Args:
        operations: List of (original_path, new_path) tuples to rollback.
        operation_type: Type of operation to rollback.
    """
    for original_path, new_path in reversed(operations):
        try:
            if operation_type in (OrganizeOperation.MOVE, OrganizeOperation.ARCHIVE):
                if new_path and new_path.exists():
                    # Move back to original location
                    shutil.move(str(new_path), str(original_path))
                    logger.info("rollback_move", from_path=str(new_path), to_path=str(original_path))
        except Exception as e:
            logger.exception("rollback_failed", original_path=str(original_path), error=str(e))
