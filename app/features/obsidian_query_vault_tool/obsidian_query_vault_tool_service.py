"""Business logic for Obsidian Query Vault Tool."""

from typing import Literal

from app.core.logging import get_logger
from app.features.obsidian_query_vault_tool.obsidian_query_vault_tool_models import (
    NoteInfo,
    ObsidianQueryVaultToolResult,
    SearchFilters,
)
from app.shared.vault.vault_manager import VaultManager
from app.shared.vault.vault_models import Note

logger = get_logger(__name__)


def _note_to_info(note: Note, response_format: str, relevance: float = 1.0) -> NoteInfo:
    """Convert Note to NoteInfo based on response format.

    Args:
        note: Note object from VaultManager.
        response_format: "concise" or "detailed".
        relevance: Relevance score (0.0-1.0).

    Returns:
        NoteInfo with fields populated based on format.
    """
    relative_path = str(note.path.relative_to(note.path.parent.parent))

    if response_format == "concise":
        return NoteInfo(
            path=relative_path,
            title=note.title,
            relevance=relevance,
        )
    else:  # detailed
        excerpt = note.content[:200] if note.content else None
        return NoteInfo(
            path=relative_path,
            title=note.title,
            relevance=relevance,
            excerpt=excerpt,
            tags=note.frontmatter.tags if note.frontmatter else None,
            created=(
                note.frontmatter.created.isoformat()
                if note.frontmatter and note.frontmatter.created
                else None
            ),
            modified=(
                note.frontmatter.modified.isoformat()
                if note.frontmatter and note.frontmatter.modified
                else None
            ),
        )


def _generate_suggestion(notes: list[Note], query: str, limit: int, truncated: bool) -> str | None:
    """Generate suggestion when results truncated or empty.

    Args:
        notes: Found notes.
        query: Original query.
        limit: Result limit.
        truncated: Whether results were truncated.

    Returns:
        Suggestion string or None.
    """
    if len(notes) == 0:
        return f"No notes found matching '{query}'. Try broader terms or check spelling."
    elif truncated:
        return f"Showing {limit} of many results. Try narrowing your search with specific tags or date ranges."
    return None


async def execute_semantic_search(
    vault_manager: VaultManager,
    query: str,
    limit: int,
    response_format: Literal["concise", "detailed"],
) -> ObsidianQueryVaultToolResult:
    """Execute semantic search across vault content.

    Args:
        vault_manager: VaultManager instance.
        query: Search query string.
        limit: Maximum number of results.
        response_format: "concise" or "detailed".

    Returns:
        ObsidianQueryVaultToolResult with matching notes.
    """
    logger.info("vault.semantic_search_started", query=query, limit=limit)

    # Use VaultManager.search_content()
    notes = vault_manager.search_content(query, limit=limit)

    # Convert to NoteInfo with appropriate fields based on response_format
    note_infos = [_note_to_info(n, response_format) for n in notes]

    truncated = len(notes) >= limit
    suggestion = _generate_suggestion(notes, query, limit, truncated)

    logger.info("vault.semantic_search_completed", result_count=len(note_infos))

    return ObsidianQueryVaultToolResult(
        results=note_infos,
        total_found=len(notes),
        truncated=truncated,
        suggestion=suggestion,
    )


async def execute_list_structure(
    vault_manager: VaultManager,
    path: str,
    limit: int,
    response_format: Literal["concise", "detailed"],
) -> ObsidianQueryVaultToolResult:
    """List vault/folder structure.

    Args:
        vault_manager: VaultManager instance.
        path: Folder path to list (empty for vault root).
        limit: Maximum number of results.
        response_format: "concise" or "detailed".

    Returns:
        ObsidianQueryVaultToolResult with note listings.
    """
    logger.info("vault.list_structure_started", path=path, limit=limit)

    # List notes in folder
    vault_paths = vault_manager.list_notes(folder=path, recursive=True)

    # Read each note to get info
    notes: list[Note] = []
    for vault_path in vault_paths[:limit]:
        relative_path = str(vault_path.relative_path)
        try:
            note = vault_manager.read_note(relative_path)
            notes.append(note)
        except Exception as e:
            logger.warning("vault.list_structure_read_failed", path=relative_path, error=str(e))
            continue

    # Convert to NoteInfo
    note_infos = [_note_to_info(n, response_format) for n in notes]

    truncated = len(vault_paths) > limit
    suggestion = (
        f"Showing {limit} of {len(vault_paths)} notes in folder. Try narrowing to a specific subfolder."
        if truncated
        else None
    )

    logger.info("vault.list_structure_completed", result_count=len(note_infos))

    return ObsidianQueryVaultToolResult(
        results=note_infos,
        total_found=len(vault_paths),
        truncated=truncated,
        suggestion=suggestion,
    )


async def execute_find_related(
    vault_manager: VaultManager,
    reference_note: str,
    max_related: int,
    response_format: Literal["concise", "detailed"],
) -> ObsidianQueryVaultToolResult:
    """Find notes related to reference note.

    Currently uses basic content-based similarity.
    Future: Could use links, backlinks, shared tags, etc.

    Args:
        vault_manager: VaultManager instance.
        reference_note: Path to reference note.
        max_related: Maximum number of related notes.
        response_format: "concise" or "detailed".

    Returns:
        ObsidianQueryVaultToolResult with related notes.
    """
    logger.info(
        "vault.find_related_started",
        reference_note=reference_note,
        max_related=max_related,
    )

    # Read reference note
    try:
        ref_note = vault_manager.read_note(reference_note)
    except FileNotFoundError:
        logger.warning("vault.find_related_reference_not_found", note=reference_note)
        return ObsidianQueryVaultToolResult(
            results=[],
            total_found=0,
            truncated=False,
            suggestion=f"Reference note '{reference_note}' not found.",
        )

    # Extract key terms from reference note (simple: take first 100 words)
    words = ref_note.content.split()[:100]
    query = " ".join(words)

    # Search for related content
    related_notes = vault_manager.search_content(query, limit=max_related + 1)

    # Exclude the reference note itself
    related_notes = [n for n in related_notes if n.path != ref_note.path][:max_related]

    # Convert to NoteInfo
    note_infos = [_note_to_info(n, response_format) for n in related_notes]

    logger.info("vault.find_related_completed", result_count=len(note_infos))

    return ObsidianQueryVaultToolResult(
        results=note_infos,
        total_found=len(related_notes),
        truncated=len(related_notes) >= max_related,
        suggestion=None,
    )


async def execute_search_by_metadata(
    vault_manager: VaultManager,
    filters: SearchFilters,
    limit: int,
    response_format: Literal["concise", "detailed"],
) -> ObsidianQueryVaultToolResult:
    """Search notes by metadata (tags, dates, folder).

    Args:
        vault_manager: VaultManager instance.
        filters: SearchFilters with tags, date_range, folder.
        limit: Maximum number of results.
        response_format: "concise" or "detailed".

    Returns:
        ObsidianQueryVaultToolResult with matching notes.
    """
    logger.info(
        "vault.metadata_search_started",
        tags=filters.tags,
        date_range=filters.date_range,
        folder=filters.folder,
        limit=limit,
    )

    # Extract date_range_days from filters
    date_range_days = None
    if filters.date_range:
        date_range_days = filters.date_range.get("days")

    # Use VaultManager.search_by_metadata()
    notes = vault_manager.search_by_metadata(
        tags=filters.tags,
        date_range_days=date_range_days,
        folder=filters.folder,
        limit=limit,
    )

    # Convert to NoteInfo
    note_infos = [_note_to_info(n, response_format) for n in notes]

    truncated = len(notes) >= limit
    suggestion = (
        f"Showing {limit} results. Add more specific filters to narrow down." if truncated else None
    )

    logger.info("vault.metadata_search_completed", result_count=len(note_infos))

    return ObsidianQueryVaultToolResult(
        results=note_infos,
        total_found=len(notes),
        truncated=truncated,
        suggestion=suggestion,
    )


async def execute_recent_changes(
    vault_manager: VaultManager,
    limit: int,
    response_format: Literal["concise", "detailed"],
) -> ObsidianQueryVaultToolResult:
    """Get recently modified notes.

    Args:
        vault_manager: VaultManager instance.
        limit: Maximum number of results.
        response_format: "concise" or "detailed".

    Returns:
        ObsidianQueryVaultToolResult with recent notes.
    """
    logger.info("vault.recent_changes_started", limit=limit)

    # Use VaultManager.get_recent_notes()
    notes = vault_manager.get_recent_notes(limit=limit)

    # Convert to NoteInfo
    note_infos = [_note_to_info(n, response_format) for n in notes]

    logger.info("vault.recent_changes_completed", result_count=len(note_infos))

    return ObsidianQueryVaultToolResult(
        results=note_infos,
        total_found=len(notes),
        truncated=False,  # get_recent_notes already limits
        suggestion=None,
    )
