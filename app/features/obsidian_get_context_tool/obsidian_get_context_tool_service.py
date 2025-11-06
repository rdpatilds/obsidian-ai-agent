"""Business logic for Obsidian Get Context Tool."""

import re
from datetime import UTC, datetime
from typing import Literal

from app.core.logging import get_logger
from app.features.obsidian_get_context_tool.obsidian_get_context_tool_models import (
    BacklinkInfo,
    NoteContent,
    ObsidianGetContextToolResult,
)
from app.shared.vault.vault_manager import VaultManager
from app.shared.vault.vault_models import Note

logger = get_logger(__name__)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return len(text) // 4


def _note_to_content(note: Note, vault_manager: VaultManager, response_format: str) -> NoteContent:
    """Convert Note to NoteContent based on format."""
    relative_path = str(note.path.relative_to(vault_manager.vault_root))
    metadata: dict[str, str | list[str] | int | float | bool] | None = None
    if response_format == "detailed" and note.frontmatter:
        metadata_dict: dict[str, str | list[str] | int | float | bool] = {}
        if note.frontmatter.tags:
            metadata_dict["tags"] = note.frontmatter.tags
        if note.frontmatter.title:
            metadata_dict["title"] = note.frontmatter.title
        if note.frontmatter.created:
            metadata_dict["created"] = note.frontmatter.created.isoformat()
        if note.frontmatter.modified:
            metadata_dict["modified"] = note.frontmatter.modified.isoformat()
        # Add custom fields that match our type constraints
        for key, value in note.frontmatter.custom.items():
            # Filter out unsupported types (pyright: this isinstance is necessary for runtime safety)
            if isinstance(value, (str, list, int, float, bool)):
                metadata_dict[key] = value
        metadata = metadata_dict
    return NoteContent(
        path=relative_path,
        title=note.title,
        content=note.content,
        metadata=metadata,
        word_count=note.word_count,
    )


def _find_backlinks(vault_manager: VaultManager, target_note_name: str) -> list[BacklinkInfo]:
    """Find all notes with wikilinks to target note."""
    backlinks: list[BacklinkInfo] = []
    wikilink_pattern = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")

    all_notes = vault_manager.list_notes(folder="", recursive=True)
    for vault_path in all_notes:
        try:
            note = vault_manager.read_note(str(vault_path.relative_path))
            matches = wikilink_pattern.finditer(note.content)
            for match in matches:
                linked_note = match.group(1).strip()
                if linked_note == target_note_name or f"{linked_note}.md" == target_note_name:
                    start = max(0, match.start() - 50)
                    end = min(len(note.content), match.end() + 50)
                    context = note.content[start:end].strip()
                    backlinks.append(
                        BacklinkInfo(
                            note_path=str(vault_path.relative_path),
                            note_title=note.title,
                            context=context,
                        )
                    )
                    break
        except Exception as e:
            logger.warning(
                "vault.backlink_search_failed", path=str(vault_path.relative_path), error=str(e)
            )
    return backlinks


async def execute_read_note(
    vault_manager: VaultManager, target: str, response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Read single note with metadata."""
    logger.info("vault.read_note_started", target=target)
    note = vault_manager.read_note(target)
    note_content = _note_to_content(note, vault_manager, response_format)
    token_estimate = _estimate_tokens(note_content.content)
    logger.info("vault.read_note_completed", path=target, word_count=note.word_count)
    return ObsidianGetContextToolResult(primary_note=note_content, token_estimate=token_estimate)


async def execute_read_multiple(
    vault_manager: VaultManager, targets: list[str], response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Read multiple notes together."""
    logger.info("vault.read_multiple_started", count=len(targets))
    notes: list[NoteContent] = []
    total_tokens = 0
    primary_note = None

    for i, target in enumerate(targets):
        try:
            note = vault_manager.read_note(target)
            note_content = _note_to_content(note, vault_manager, response_format)
            if i == 0:
                primary_note = note_content
            else:
                notes.append(note_content)
            total_tokens += _estimate_tokens(note_content.content)
        except Exception as e:
            logger.warning("vault.read_multiple_failed", target=target, error=str(e))

    if not primary_note:
        raise ValueError("No notes could be read from targets list")

    logger.info("vault.read_multiple_completed", count=len(notes) + 1)
    return ObsidianGetContextToolResult(
        primary_note=primary_note,
        related_notes=notes if notes else None,
        token_estimate=total_tokens,
    )


async def execute_gather_related(
    vault_manager: VaultManager,
    target: str,
    max_related: int,
    response_format: Literal["concise", "detailed"],
) -> ObsidianGetContextToolResult:
    """Read note and its related notes."""
    logger.info("vault.gather_related_started", target=target, max_related=max_related)

    primary = vault_manager.read_note(target)
    primary_content = _note_to_content(primary, vault_manager, response_format)

    # Find related notes (mirror execute_find_related pattern)
    words = primary.content.split()[:100]
    query = " ".join(words)
    related_notes_raw = vault_manager.search_content(query, limit=max_related + 1)
    related_notes_raw = [n for n in related_notes_raw if n.path != primary.path][:max_related]

    related_contents = [
        _note_to_content(n, vault_manager, response_format) for n in related_notes_raw
    ]

    total_tokens = _estimate_tokens(primary_content.content)
    total_tokens += sum(_estimate_tokens(n.content) for n in related_contents)

    logger.info("vault.gather_related_completed", related_count=len(related_contents))
    return ObsidianGetContextToolResult(
        primary_note=primary_content,
        related_notes=related_contents if related_contents else None,
        token_estimate=total_tokens,
    )


async def execute_daily_note(
    vault_manager: VaultManager, date: str | None, response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Get daily note for specific date or today."""
    logger.info("vault.daily_note_started", date=date)

    if date == "today" or date is None:
        target_date = datetime.now(tz=UTC)  # UTC for consistent daily note paths
    else:
        target_date = datetime.fromisoformat(date)

    date_str = target_date.strftime("%Y-%m-%d")
    possible_paths = [
        f"Daily/{date_str}.md",
        f"daily/{date_str}.md",
        f"{date_str}.md",
        f"Journal/{date_str}.md",
    ]

    for path in possible_paths:
        try:
            note = vault_manager.read_note(path)
            note_content = _note_to_content(note, vault_manager, response_format)
            token_estimate = _estimate_tokens(note_content.content)
            logger.info("vault.daily_note_completed", path=path, date=date_str)
            return ObsidianGetContextToolResult(
                primary_note=note_content, token_estimate=token_estimate
            )
        except FileNotFoundError:
            continue

    raise FileNotFoundError(
        f"Daily note not found for {date_str}. Tried: {', '.join(possible_paths)}"
    )


async def execute_note_with_backlinks(
    vault_manager: VaultManager, target: str, response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Read note with all backlinks."""
    logger.info("vault.note_with_backlinks_started", target=target)

    primary = vault_manager.read_note(target)
    primary_content = _note_to_content(primary, vault_manager, response_format)

    target_name = primary.path.stem
    backlinks = _find_backlinks(vault_manager, target_name)

    related_contents: list[NoteContent] = []
    for backlink in backlinks:
        try:
            note = vault_manager.read_note(backlink.note_path)
            related_contents.append(_note_to_content(note, vault_manager, response_format))
        except Exception as e:
            logger.warning("vault.backlink_read_failed", path=backlink.note_path, error=str(e))

    total_tokens = _estimate_tokens(primary_content.content)
    total_tokens += sum(_estimate_tokens(n.content) for n in related_contents)
    total_tokens += sum(_estimate_tokens(b.context) for b in backlinks)

    logger.info("vault.note_with_backlinks_completed", backlink_count=len(backlinks))
    return ObsidianGetContextToolResult(
        primary_note=primary_content,
        related_notes=related_contents if related_contents else None,
        backlinks=backlinks if backlinks else None,
        token_estimate=total_tokens,
    )
