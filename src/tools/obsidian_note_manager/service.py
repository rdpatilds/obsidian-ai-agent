"""Service layer for Obsidian Note Manager tool.

This module implements the core business logic for consolidated note operations,
handling read, write, patch, append, and delete operations with proper security
and token-efficient response formatting.
"""

import time
from pathlib import Path
from typing import Any

import aiofiles  # type: ignore[import-untyped]
import frontmatter  # type: ignore[import-untyped]

from src.shared.logging import get_logger
from src.shared.obsidian_parsers import extract_frontmatter_safely
from src.shared.response_formatter import format_note_response
from src.shared.vault_security import is_path_allowed, validate_vault_path
from src.tools.obsidian_note_manager.schemas import (
    ManageNoteRequest,
    ManageNoteResponse,
    NoteOperation,
)


logger = get_logger(__name__)


async def manage_note_service(
    request: ManageNoteRequest,
    vault_path: str,
    max_file_size_mb: int,
) -> ManageNoteResponse:
    """Execute note management operation.

    This consolidates what would otherwise require multiple tool calls into
    a single unified operation with configurable response formatting.

    Args:
        request: ManageNoteRequest with operation details.
        vault_path: Absolute path to Obsidian vault root.
        max_file_size_mb: Maximum file size in MB for safety.

    Returns:
        ManageNoteResponse with operation result and formatted data.

    Raises:
        ValueError: If path is invalid, blocked, or operation validation fails.
        FileNotFoundError: If note doesn't exist for READ/PATCH/APPEND/DELETE.
        OSError: If file operations fail.
    """
    start_time = time.perf_counter()

    # Validate and resolve path
    full_path_str = validate_vault_path(vault_path, request.path)
    full_path = Path(full_path_str)

    if not is_path_allowed(full_path_str):
        logger.error(
            "note_operation_blocked",
            path=request.path,
            operation=request.operation.value,
        )
        raise ValueError(f"Path not allowed: {request.path}")

    logger.info(
        "note_operation_started",
        path=request.path,
        operation=request.operation.value,
        response_format=request.response_format.value,
    )

    # Execute operation
    if request.operation == NoteOperation.READ:
        result = await _read_note(full_path, request, max_file_size_mb)

    elif request.operation == NoteOperation.UPDATE:
        result = await _update_note(full_path, request)

    elif request.operation == NoteOperation.PATCH:
        result = await _patch_note(full_path, request)

    elif request.operation == NoteOperation.APPEND:
        result = await _append_note(full_path, request)

    elif request.operation == NoteOperation.DELETE:
        result = await _delete_note(full_path, request)

    else:
        raise ValueError(f"Unknown operation: {request.operation}")

    duration_ms = (time.perf_counter() - start_time) * 1000

    logger.info(
        "note_operation_completed",
        path=request.path,
        operation=request.operation.value,
        success=result.success,
        duration_ms=duration_ms,
        token_estimate=result.token_estimate,
    )

    return result


async def _read_note(
    full_path: Path,
    request: ManageNoteRequest,
    max_file_size_mb: int,
) -> ManageNoteResponse:
    """Read note with configurable response format."""
    if not full_path.exists():
        raise FileNotFoundError(f"Note not found: {request.path}")

    # Check file size
    size_mb = full_path.stat().st_size / (1024 * 1024)
    if size_mb > max_file_size_mb:
        raise ValueError(
            f"File too large: {size_mb:.1f}MB (max: {max_file_size_mb}MB)"
        )

    # Read file
    async with aiofiles.open(full_path, encoding="utf-8") as f:
        content = await f.read()

    # Parse frontmatter
    metadata, body = extract_frontmatter_safely(content)

    # Format response based on response_format
    note_data = {
        "title": full_path.stem,
        "content": body,
        "frontmatter": metadata,
        "tags": metadata.get("tags", []),
        "path": request.path,
    }

    formatted_data = format_note_response(note_data, request.response_format)

    # Estimate tokens
    token_estimate = {
        "minimal": 50,
        "concise": 150,
        "detailed": len(body.split()) * 1.3,  # Rough estimate
    }.get(request.response_format.value, 150)

    return ManageNoteResponse(
        success=True,
        path=request.path,
        operation=NoteOperation.READ,
        data=formatted_data,
        message=f"Read note: {request.path}",
        token_estimate=int(token_estimate),
    )


async def _update_note(
    full_path: Path,
    request: ManageNoteRequest,
) -> ManageNoteResponse:
    """Update note content, optionally merging metadata.

    Supports two modes:
    1. Full update: Provide content to replace note body
    2. Metadata-only update: Omit content to only update frontmatter
    """
    # Read existing content if file exists
    existing_metadata: dict[str, Any] = {}
    existing_body: str = ""

    if full_path.exists():
        async with aiofiles.open(full_path, encoding="utf-8") as f:
            existing_content = await f.read()
        existing_metadata, existing_body = extract_frontmatter_safely(existing_content)

    # Determine content to use
    if request.content is None:
        # Metadata-only update: preserve existing body
        if not full_path.exists():
            raise ValueError("content is required when creating a new note")
        clean_content = existing_body
        content_metadata: dict[str, Any] = {}
    else:
        # Full update: use provided content
        # IMPORTANT: Strip frontmatter from content if agent mistakenly included it
        # This prevents duplicate frontmatter blocks
        content_metadata, clean_content = extract_frontmatter_safely(request.content)

    # Merge metadata: existing → content metadata → explicit updates
    final_metadata = existing_metadata.copy()
    if content_metadata:
        logger.warning(
            "frontmatter_found_in_content",
            path=request.path,
            operation="update",
            message="Agent included frontmatter in content parameter - extracting and merging",
        )
        final_metadata.update(content_metadata)
    if request.metadata_updates:
        final_metadata.update(request.metadata_updates)

    # Create frontmatter post with CLEAN content (no embedded frontmatter)
    post = frontmatter.Post(clean_content, **final_metadata)
    new_content = frontmatter.dumps(post)

    # Write file (create parent dirs if needed)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
        await f.write(new_content)

    # Format response
    note_data = {
        "title": full_path.stem,
        "content": clean_content,  # Use clean_content (not request.content which may be None)
        "frontmatter": final_metadata,
        "tags": final_metadata.get("tags", []),
        "path": request.path,
    }

    formatted_data = format_note_response(note_data, request.response_format)

    return ManageNoteResponse(
        success=True,
        path=request.path,
        operation=NoteOperation.UPDATE,
        data=formatted_data,
        message=f"Updated note: {request.path}",
        token_estimate=150,
    )


async def _patch_note(
    full_path: Path,
    request: ManageNoteRequest,
) -> ManageNoteResponse:
    """Patch note with find-and-replace."""
    if not full_path.exists():
        raise FileNotFoundError(f"Note not found: {request.path}")

    if not request.find_replace:
        raise ValueError("find_replace is required for PATCH operation")

    find_text, replace_text = request.find_replace

    # Read existing content
    async with aiofiles.open(full_path, encoding="utf-8") as f:
        content = await f.read()

    # Parse frontmatter
    metadata, body = extract_frontmatter_safely(content)

    # Count occurrences
    occurrence_count = body.count(find_text)

    if occurrence_count == 0:
        return ManageNoteResponse(
            success=False,
            path=request.path,
            operation=NoteOperation.PATCH,
            data={"match_count": 0},
            message=f"No matches found for: {find_text[:50]}",
            token_estimate=50,
        )

    # Safety check for multiple matches
    if occurrence_count > 1 and not request.replace_all:
        return ManageNoteResponse(
            success=False,
            path=request.path,
            operation=NoteOperation.PATCH,
            data={"match_count": occurrence_count},
            message=(
                f"Found {occurrence_count} occurrences. "
                f"Set replace_all=true to replace all matches."
            ),
            token_estimate=50,
        )

    # Perform replacement
    if request.replace_all:
        updated_body = body.replace(find_text, replace_text)
    else:
        # Replace only first occurrence
        updated_body = body.replace(find_text, replace_text, 1)

    # Merge metadata updates if provided
    if request.metadata_updates:
        metadata.update(request.metadata_updates)

    # Write updated content
    post = frontmatter.Post(updated_body, **metadata)
    new_content = frontmatter.dumps(post)

    async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
        await f.write(new_content)

    # Format response
    note_data = {
        "title": full_path.stem,
        "content": updated_body,
        "frontmatter": metadata,
        "tags": metadata.get("tags", []),
        "path": request.path,
    }

    formatted_data = format_note_response(note_data, request.response_format)
    formatted_data["match_count"] = occurrence_count

    return ManageNoteResponse(
        success=True,
        path=request.path,
        operation=NoteOperation.PATCH,
        data=formatted_data,
        message=f"Patched note: replaced {occurrence_count} occurrence(s)",
        token_estimate=150,
    )


async def _append_note(
    full_path: Path,
    request: ManageNoteRequest,
) -> ManageNoteResponse:
    """Append content to note."""
    if request.content is None:
        raise ValueError("content is required for APPEND operation")

    # Read existing content
    if full_path.exists():
        async with aiofiles.open(full_path, encoding="utf-8") as f:
            existing_content = await f.read()
        metadata, body = extract_frontmatter_safely(existing_content)
    else:
        metadata = {}
        body = ""

    # IMPORTANT: Strip frontmatter from append content if agent mistakenly included it
    content_metadata, clean_append_content = extract_frontmatter_safely(request.content)

    if content_metadata:
        logger.warning(
            "frontmatter_found_in_append_content",
            path=request.path,
            operation="append",
            message="Agent included frontmatter in append content - extracting and merging",
        )
        metadata.update(content_metadata)

    # Append CLEAN content with separator (no embedded frontmatter)
    separator = "\n\n" if body and not body.endswith("\n\n") else ""
    updated_body = body + separator + clean_append_content

    # Merge metadata updates
    if request.metadata_updates:
        metadata.update(request.metadata_updates)

    # Write updated content
    post = frontmatter.Post(updated_body, **metadata)
    new_content = frontmatter.dumps(post)

    full_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiofiles.open(full_path, "w", encoding="utf-8") as f:
        await f.write(new_content)

    # Format response
    note_data = {
        "title": full_path.stem,
        "content": updated_body,
        "frontmatter": metadata,
        "tags": metadata.get("tags", []),
        "path": request.path,
    }

    formatted_data = format_note_response(note_data, request.response_format)

    return ManageNoteResponse(
        success=True,
        path=request.path,
        operation=NoteOperation.APPEND,
        data=formatted_data,
        message=f"Appended to note: {request.path}",
        token_estimate=150,
    )


async def _delete_note(
    full_path: Path,
    request: ManageNoteRequest,
) -> ManageNoteResponse:
    """Delete note with confirmation."""
    if not full_path.exists():
        raise FileNotFoundError(f"Note not found: {request.path}")

    # Require confirmation
    if request.confirm_path != request.path:
        return ManageNoteResponse(
            success=False,
            path=request.path,
            operation=NoteOperation.DELETE,
            data={},
            message=(
                f"Deletion requires confirmation. "
                f"Set confirm_path='{request.path}' to confirm."
            ),
            token_estimate=50,
        )

    # Delete file
    full_path.unlink()

    logger.warning(
        "note_deleted",
        path=request.path,
        full_path=str(full_path),
        confirmed=True,
    )

    return ManageNoteResponse(
        success=True,
        path=request.path,
        operation=NoteOperation.DELETE,
        data={"deleted": True},
        message=f"Deleted note: {request.path}",
        token_estimate=50,
    )
