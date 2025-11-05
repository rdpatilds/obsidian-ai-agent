"""VaultManager for Obsidian vault file operations."""

from datetime import UTC, datetime
from pathlib import Path

import frontmatter  # type: ignore[import-untyped]

from app.core.logging import get_logger
from app.shared.vault.vault_models import Frontmatter as FrontmatterModel
from app.shared.vault.vault_models import Note, VaultPath


class VaultManager:
    """Manages Obsidian vault file operations.

    Provides methods for reading notes, searching content, and querying metadata.
    All paths are validated to stay within vault_root for security.
    """

    def __init__(self, vault_path: str | Path) -> None:
        """Initialize VaultManager with vault root path.

        Args:
            vault_path: Path to Obsidian vault root directory.

        Raises:
            FileNotFoundError: If vault path doesn't exist.
            ValueError: If vault path is not a directory.
        """
        self.vault_root = Path(vault_path).resolve()
        if not self.vault_root.exists():
            raise FileNotFoundError(f"Vault not found: {self.vault_root}")
        if not self.vault_root.is_dir():
            raise ValueError(f"Vault path is not a directory: {self.vault_root}")
        self.logger = get_logger(__name__)
        self.logger.info("vault.manager_initialized", vault_root=str(self.vault_root))

    def _validate_path(self, relative_path: str) -> Path:
        """Validate path is within vault and return absolute path.

        Args:
            relative_path: Relative path within vault.

        Returns:
            Absolute resolved path.

        Raises:
            ValueError: If path is outside vault (directory traversal attempt).
        """
        vault_path = VaultPath(vault_root=self.vault_root, relative_path=relative_path)
        vault_path.validate_within_vault()
        return vault_path.absolute_path

    def _parse_frontmatter(self, file_path: Path) -> tuple[FrontmatterModel | None, str]:
        """Parse frontmatter from markdown file.

        Args:
            file_path: Path to markdown file.

        Returns:
            Tuple of (parsed frontmatter or None, content without frontmatter).
        """
        try:
            with file_path.open("r", encoding="utf-8") as f:
                post = frontmatter.load(f)

            if post.metadata:
                # Convert frontmatter to our model
                tags = post.metadata.get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]

                # Handle dates
                created = post.metadata.get("created")
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created)
                    except (ValueError, TypeError):
                        created = None
                elif not isinstance(created, datetime):
                    created = None

                modified = post.metadata.get("modified")
                if isinstance(modified, str):
                    try:
                        modified = datetime.fromisoformat(modified)
                    except (ValueError, TypeError):
                        modified = None
                elif not isinstance(modified, datetime):
                    modified = None

                # Get other custom fields
                reserved_keys = {"tags", "title", "created", "modified"}
                custom = {
                    k: v
                    for k, v in post.metadata.items()
                    if k not in reserved_keys and isinstance(v, (str, int, float, bool, list))
                }

                fm = FrontmatterModel(
                    tags=tags,
                    title=post.metadata.get("title"),
                    created=created,
                    modified=modified,
                    custom=custom,
                )
                return fm, post.content
            return None, post.content
        except Exception as e:
            self.logger.warning(
                "vault.frontmatter_parse_failed",
                file=str(file_path),
                error=str(e),
            )
            # Fallback: read file without frontmatter parsing
            return None, file_path.read_text(encoding="utf-8")

    def read_note(self, relative_path: str) -> Note:
        """Read a single note with frontmatter parsing.

        Args:
            relative_path: Relative path to note (e.g., "Projects/ML.md").

        Returns:
            Note object with content and metadata.

        Raises:
            FileNotFoundError: If note doesn't exist.
            ValueError: If path is outside vault.
        """
        abs_path = self._validate_path(relative_path)

        if not abs_path.exists():
            raise FileNotFoundError(f"Note not found: {relative_path}")

        self.logger.debug("vault.read_note_started", path=relative_path)

        fm, content = self._parse_frontmatter(abs_path)

        # Extract title from frontmatter or filename
        title = (fm.title if fm else None) or abs_path.stem

        word_count = len(content.split())

        note = Note(
            path=abs_path,
            title=title,
            content=content,
            frontmatter=fm,
            word_count=word_count,
        )

        self.logger.debug("vault.read_note_completed", path=relative_path, word_count=word_count)

        return note

    def search_content(self, query: str, limit: int = 10) -> list[Note]:
        """Search note content for query string (case-insensitive).

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of matching notes, sorted by relevance (most matches first).
        """
        self.logger.info("vault.search_started", query=query, limit=limit)

        results: list[tuple[Note, int]] = []
        query_lower = query.lower()

        for md_file in self.vault_root.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                # Count occurrences for relevance
                occurrences = content.lower().count(query_lower)

                if occurrences > 0:
                    relative = md_file.relative_to(self.vault_root)
                    note = self.read_note(str(relative))
                    results.append((note, occurrences))

            except Exception as e:
                self.logger.warning("vault.search_file_skipped", file=str(md_file), error=str(e))
                continue

        # Sort by relevance (occurrences) descending
        results.sort(key=lambda x: x[1], reverse=True)

        notes = [note for note, _ in results[:limit]]

        self.logger.info("vault.search_completed", result_count=len(notes))

        return notes

    def list_notes(self, folder: str = "", recursive: bool = True) -> list[VaultPath]:
        """List all notes in folder.

        Args:
            folder: Relative folder path (empty string for vault root).
            recursive: If True, include subdirectories.

        Returns:
            List of VaultPath objects for each note.
        """
        self.logger.info("vault.list_started", folder=folder, recursive=recursive)

        if folder:
            start_path = self._validate_path(folder)
        else:
            start_path = self.vault_root

        paths: list[VaultPath] = []

        pattern = "**/*.md" if recursive else "*.md"
        for md_file in start_path.glob(pattern):
            try:
                relative = md_file.relative_to(self.vault_root)
                vault_path = VaultPath(vault_root=self.vault_root, relative_path=str(relative))
                paths.append(vault_path)
            except Exception as e:
                self.logger.warning("vault.list_file_skipped", file=str(md_file), error=str(e))
                continue

        self.logger.info("vault.list_completed", result_count=len(paths))

        return paths

    def search_by_metadata(
        self,
        tags: list[str] | None = None,
        date_range_days: int | None = None,
        folder: str | None = None,
        limit: int = 10,
    ) -> list[Note]:
        """Search notes by frontmatter metadata.

        Args:
            tags: Filter by tags (any match).
            date_range_days: Filter by modified date (last N days).
            folder: Filter by folder path.
            limit: Maximum number of results.

        Returns:
            List of matching notes.
        """
        self.logger.info(
            "vault.metadata_search_started",
            tags=tags,
            date_range_days=date_range_days,
            folder=folder,
            limit=limit,
        )

        results: list[Note] = []

        # Determine search scope
        if folder:
            search_path = self._validate_path(folder)
        else:
            search_path = self.vault_root

        # Calculate date threshold
        date_threshold = None
        if date_range_days:
            date_threshold = datetime.now(UTC).timestamp() - (date_range_days * 24 * 60 * 60)

        for md_file in search_path.rglob("*.md"):
            try:
                # Check date filter first (cheap check)
                if date_threshold:
                    file_mtime = md_file.stat().st_mtime
                    if file_mtime < date_threshold:
                        continue

                # Read note to check tags
                relative = md_file.relative_to(self.vault_root)
                note = self.read_note(str(relative))

                # Check tag filter
                if tags and note.frontmatter:
                    note_tags = note.frontmatter.tags
                    if not any(tag in note_tags for tag in tags):
                        continue
                elif tags and not note.frontmatter:
                    # Has tag filter but note has no frontmatter
                    continue

                results.append(note)

                if len(results) >= limit:
                    break

            except Exception as e:
                self.logger.warning(
                    "vault.metadata_search_file_skipped",
                    file=str(md_file),
                    error=str(e),
                )
                continue

        self.logger.info("vault.metadata_search_completed", result_count=len(results))

        return results

    def get_recent_notes(self, limit: int = 10) -> list[Note]:
        """Get recently modified notes.

        Args:
            limit: Maximum number of results.

        Returns:
            List of notes sorted by modification time (most recent first).
        """
        self.logger.info("vault.recent_notes_started", limit=limit)

        notes_with_mtime: list[tuple[Path, float]] = []

        for md_file in self.vault_root.rglob("*.md"):
            try:
                mtime = md_file.stat().st_mtime
                notes_with_mtime.append((md_file, mtime))
            except Exception as e:
                self.logger.warning(
                    "vault.recent_notes_file_skipped", file=str(md_file), error=str(e)
                )
                continue

        # Sort by mtime descending
        notes_with_mtime.sort(key=lambda x: x[1], reverse=True)

        # Read top N notes
        results: list[Note] = []
        for md_file, _ in notes_with_mtime[:limit]:
            try:
                relative = md_file.relative_to(self.vault_root)
                note = self.read_note(str(relative))
                results.append(note)
            except Exception as e:
                self.logger.warning(
                    "vault.recent_notes_read_failed", file=str(md_file), error=str(e)
                )
                continue

        self.logger.info("vault.recent_notes_completed", result_count=len(results))

        return results
