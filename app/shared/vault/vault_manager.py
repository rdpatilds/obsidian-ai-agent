"""VaultManager for Obsidian vault file operations."""

import shutil
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
                tags_raw = post.metadata.get("tags", [])
                tags: list[str] = []
                if isinstance(tags_raw, str):
                    tags = [tags_raw]
                elif isinstance(tags_raw, list):
                    # Ensure all items are strings (type narrowing for untyped metadata)
                    tags_list: list[object] = tags_raw  # pyright: ignore[reportUnknownVariableType]
                    tags = [str(item) for item in tags_list]

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

                # Get other custom fields with proper type narrowing
                reserved_keys = {"tags", "title", "created", "modified"}
                custom: dict[str, str | int | float | bool | list[str]] = {}
                for k, v in post.metadata.items():
                    if k not in reserved_keys:
                        if isinstance(v, (str, int, float, bool)):
                            custom[k] = v
                        elif isinstance(v, list):
                            # Convert list items to strings (type narrowing for untyped metadata)
                            v_list: list[object] = v  # pyright: ignore[reportUnknownVariableType]
                            custom[k] = [str(item) for item in v_list]

                # Get title with type assertion
                title_raw = post.metadata.get("title")
                title: str | None = str(title_raw) if title_raw is not None else None

                fm = FrontmatterModel(
                    tags=tags,
                    title=title,
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

    def write_note(
        self,
        relative_path: str,
        content: str,
        metadata: dict[str, str | list[str] | int | float | bool] | None = None,
        overwrite: bool = False,
    ) -> Path:
        """Write note with optional frontmatter metadata.

        Creates parent directories if they don't exist.

        Args:
            relative_path: Path within vault (e.g., "Projects/note.md")
            content: Note content without frontmatter
            metadata: Optional frontmatter fields (tags, title, custom)
            overwrite: If False, raise error if file exists

        Returns:
            Absolute path to written file

        Raises:
            ValueError: If path outside vault or file exists and overwrite=False
            IOError: If write operation fails
        """
        abs_path = self._validate_path(relative_path)

        if abs_path.exists() and not overwrite:
            raise ValueError(
                f"Note already exists: {relative_path}. Set overwrite=True to replace."
            )

        self.logger.info("vault.write_note_started", path=relative_path, overwrite=overwrite)

        try:
            # Construct content with frontmatter if provided
            if metadata:
                # Untyped frontmatter library - suppress type checking
                post = frontmatter.Post(content, handler=None, **metadata)
                full_content = frontmatter.dumps(post)
            else:
                full_content = content

            # Create parent directories
            abs_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            abs_path.write_text(full_content, encoding="utf-8")

            self.logger.info("vault.write_note_completed", path=relative_path)
            return abs_path

        except Exception as e:
            self.logger.error(
                "vault.write_note_failed", path=relative_path, error=str(e), exc_info=True
            )
            raise

    def append_to_note(self, relative_path: str, content: str) -> Path:
        """Append content to existing note.

        Args:
            relative_path: Path to existing note
            content: Content to append (will add newline if needed)

        Returns:
            Absolute path to updated file

        Raises:
            FileNotFoundError: If note doesn't exist
            ValueError: If path outside vault
        """
        abs_path = self._validate_path(relative_path)

        if not abs_path.exists():
            raise FileNotFoundError(f"Cannot append to non-existent note: {relative_path}")

        self.logger.info("vault.append_note_started", path=relative_path)

        try:
            # Read existing note
            note = self.read_note(relative_path)

            # Append content (ensure newline before appending)
            new_content = note.content
            if not new_content.endswith("\n"):
                new_content += "\n"
            new_content += content

            # Preserve existing frontmatter
            metadata = None
            if note.frontmatter:
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

            # Write back with existing frontmatter
            result = self.write_note(relative_path, new_content, metadata, overwrite=True)

            self.logger.info("vault.append_note_completed", path=relative_path)
            return result

        except Exception as e:
            self.logger.error(
                "vault.append_note_failed", path=relative_path, error=str(e), exc_info=True
            )
            raise

    def search_content(self, query: str, limit: int = 10) -> list[Note]:
        """Search notes by filename, title, and content (case-insensitive hybrid search).

        Scoring strategy:
        - Filename matches: 100 points per occurrence (highest priority)
        - Title matches: 50 points per occurrence (high priority)
        - Content matches: 1 point per occurrence (base relevance)

        This ensures files like "Excal-4-GlobalRules.md" are found when
        searching for "GlobalRules", even if content doesn't match.

        Args:
            query: Search query string.
            limit: Maximum number of results.

        Returns:
            List of matching notes, sorted by relevance score (highest first).
        """
        self.logger.info("vault.search_started", query=query, limit=limit)

        results: list[tuple[Note, int]] = []
        query_lower = query.lower()

        for md_file in self.vault_root.rglob("*.md"):
            try:
                # Read file and parse note
                relative = md_file.relative_to(self.vault_root)
                note = self.read_note(str(relative))

                # Calculate relevance score with weighted matches
                score = 0

                # Check filename (stem without .md extension) - 100 points per match
                filename_lower = md_file.stem.lower()
                filename_matches = filename_lower.count(query_lower)
                score += filename_matches * 100

                # Check title (from frontmatter or filename) - 50 points per match
                title_lower = note.title.lower()
                title_matches = title_lower.count(query_lower)
                score += title_matches * 50

                # Check content - 1 point per match
                content_lower = note.content.lower()
                content_matches = content_lower.count(query_lower)
                score += content_matches

                if score > 0:
                    results.append((note, score))
                    self.logger.debug(
                        "vault.search_match",
                        path=str(relative),
                        score=score,
                        filename_matches=filename_matches,
                        title_matches=title_matches,
                        content_matches=content_matches,
                    )

            except Exception as e:
                self.logger.warning("vault.search_file_skipped", file=str(md_file), error=str(e))
                continue

        # Sort by relevance score descending
        results.sort(key=lambda x: x[1], reverse=True)

        notes = [note for note, _ in results[:limit]]

        self.logger.info("vault.search_completed", result_count=len(notes), total_matches=len(results))

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

    def delete_note(self, relative_path: str) -> None:
        """Delete a note file.

        Args:
            relative_path: Path to note to delete

        Raises:
            FileNotFoundError: If note doesn't exist
            ValueError: If path outside vault
        """
        abs_path = self._validate_path(relative_path)

        if not abs_path.exists():
            raise FileNotFoundError(f"Cannot delete non-existent note: {relative_path}")

        self.logger.info("vault.delete_note_started", path=relative_path)

        try:
            abs_path.unlink()
            self.logger.info("vault.delete_note_completed", path=relative_path)
        except Exception as e:
            self.logger.error(
                "vault.delete_note_failed", path=relative_path, error=str(e), exc_info=True
            )
            raise

    def move_note(
        self, source_path: str, dest_path: str, create_folders: bool = True
    ) -> Path:
        """Move note to new location.

        Args:
            source_path: Current note path
            dest_path: Destination path
            create_folders: Create parent folders if missing

        Returns:
            Absolute path to new location

        Raises:
            FileNotFoundError: If source doesn't exist
            ValueError: If paths outside vault or dest exists
        """
        source_abs = self._validate_path(source_path)
        dest_abs = self._validate_path(dest_path)

        if not source_abs.exists():
            raise FileNotFoundError(f"Cannot move non-existent note: {source_path}")

        if dest_abs.exists():
            raise ValueError(f"Destination already exists: {dest_path}")

        self.logger.info("vault.move_note_started", source=source_path, dest=dest_path)

        try:
            # Create parent directories if needed
            if create_folders:
                dest_abs.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            source_abs.rename(dest_abs)

            self.logger.info("vault.move_note_completed", source=source_path, dest=dest_path)
            return dest_abs

        except Exception as e:
            self.logger.error(
                "vault.move_note_failed",
                source=source_path,
                dest=dest_path,
                error=str(e),
                exc_info=True,
            )
            raise

    def create_folder(self, relative_path: str, exist_ok: bool = False) -> Path:
        """Create folder in vault.

        Args:
            relative_path: Folder path to create
            exist_ok: If True, don't error if folder exists

        Returns:
            Absolute path to created folder

        Raises:
            ValueError: If path outside vault or exists and exist_ok=False
        """
        abs_path = self._validate_path(relative_path)

        if abs_path.exists() and not exist_ok:
            raise ValueError(f"Folder already exists: {relative_path}")

        self.logger.info("vault.create_folder_started", path=relative_path)

        try:
            abs_path.mkdir(parents=True, exist_ok=exist_ok)
            self.logger.info("vault.create_folder_completed", path=relative_path)
            return abs_path
        except Exception as e:
            self.logger.error(
                "vault.create_folder_failed", path=relative_path, error=str(e), exc_info=True
            )
            raise

    def delete_folder(self, relative_path: str, recursive: bool = False) -> None:
        """Delete folder from vault.

        Args:
            relative_path: Folder path to delete
            recursive: If True, delete non-empty folders

        Raises:
            FileNotFoundError: If folder doesn't exist
            ValueError: If path outside vault or folder not empty and recursive=False
        """
        abs_path = self._validate_path(relative_path)

        if not abs_path.exists():
            raise FileNotFoundError(f"Cannot delete non-existent folder: {relative_path}")

        if not abs_path.is_dir():
            raise ValueError(f"Path is not a folder: {relative_path}")

        # Check if folder is empty
        if not recursive and any(abs_path.iterdir()):
            raise ValueError(
                f"Folder not empty: {relative_path}. Set recursive=True to delete."
            )

        self.logger.info("vault.delete_folder_started", path=relative_path, recursive=recursive)

        try:
            if recursive:
                shutil.rmtree(abs_path)
            else:
                abs_path.rmdir()
            self.logger.info("vault.delete_folder_completed", path=relative_path)
        except Exception as e:
            self.logger.error(
                "vault.delete_folder_failed", path=relative_path, error=str(e), exc_info=True
            )
            raise

    def move_folder(self, source_path: str, dest_path: str) -> Path:
        """Move folder to new location.

        Args:
            source_path: Current folder path
            dest_path: Destination path

        Returns:
            Absolute path to new location

        Raises:
            FileNotFoundError: If source doesn't exist
            ValueError: If paths outside vault or dest exists
        """
        source_abs = self._validate_path(source_path)
        dest_abs = self._validate_path(dest_path)

        if not source_abs.exists():
            raise FileNotFoundError(f"Cannot move non-existent folder: {source_path}")

        if not source_abs.is_dir():
            raise ValueError(f"Source is not a folder: {source_path}")

        if dest_abs.exists():
            raise ValueError(f"Destination already exists: {dest_path}")

        self.logger.info("vault.move_folder_started", source=source_path, dest=dest_path)

        try:
            source_abs.rename(dest_abs)
            self.logger.info("vault.move_folder_completed", source=source_path, dest=dest_path)
            return dest_abs
        except Exception as e:
            self.logger.error(
                "vault.move_folder_failed",
                source=source_path,
                dest=dest_path,
                error=str(e),
                exc_info=True,
            )
            raise
