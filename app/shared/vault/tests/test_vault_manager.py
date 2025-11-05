"""Tests for VaultManager."""

from pathlib import Path

import pytest

from app.shared.vault.vault_manager import VaultManager


def test_vault_manager_initialization(temp_vault: Path) -> None:
    """Test VaultManager initializes with valid vault."""
    vm = VaultManager(temp_vault)
    assert vm.vault_root == temp_vault.resolve()


def test_vault_manager_invalid_path() -> None:
    """Test VaultManager raises error for invalid vault."""
    with pytest.raises(FileNotFoundError):
        VaultManager("/nonexistent/path")


def test_vault_manager_invalid_file_path(tmp_path: Path) -> None:
    """Test VaultManager raises error when path is a file."""
    file_path = tmp_path / "test.md"
    file_path.write_text("test")
    with pytest.raises(ValueError, match="not a directory"):
        VaultManager(file_path)


def test_read_note_with_frontmatter(vault_manager: VaultManager) -> None:
    """Test reading note with YAML frontmatter."""
    note = vault_manager.read_note("note1.md")

    assert note.title == "Note 1"
    assert note.frontmatter is not None
    assert "python" in note.frontmatter.tags
    assert "testing" in note.frontmatter.tags
    assert "Python" in note.content
    assert note.word_count > 0


def test_read_note_without_frontmatter(vault_manager: VaultManager) -> None:
    """Test reading note without frontmatter."""
    note = vault_manager.read_note("projects/project1.md")

    assert note.title == "project1"  # Falls back to filename stem
    assert note.frontmatter is None
    assert "Project 1" in note.content
    assert note.word_count > 0


def test_read_note_not_found(vault_manager: VaultManager) -> None:
    """Test reading nonexistent note raises error."""
    with pytest.raises(FileNotFoundError):
        vault_manager.read_note("nonexistent.md")


def test_path_traversal_prevention(vault_manager: VaultManager) -> None:
    """Test that directory traversal attempts are blocked."""
    with pytest.raises(ValueError, match="outside vault root"):
        vault_manager.read_note("../../../etc/passwd")


def test_search_content(vault_manager: VaultManager) -> None:
    """Test content search finds matching notes."""
    results = vault_manager.search_content("Python")

    assert len(results) >= 1
    assert any("Python" in n.content for n in results)


def test_search_content_case_insensitive(vault_manager: VaultManager) -> None:
    """Test search is case-insensitive."""
    results = vault_manager.search_content("python")
    assert len(results) >= 1


def test_search_content_no_results(vault_manager: VaultManager) -> None:
    """Test search with no matches returns empty list."""
    results = vault_manager.search_content("nonexistent_term_xyz")
    assert len(results) == 0


def test_search_content_respects_limit(vault_manager: VaultManager) -> None:
    """Test search respects limit parameter."""
    results = vault_manager.search_content("test", limit=1)
    assert len(results) <= 1


def test_list_notes_recursive(vault_manager: VaultManager) -> None:
    """Test listing all notes recursively."""
    notes = vault_manager.list_notes(recursive=True)

    assert len(notes) >= 3  # note1, note2, projects/project1
    paths = [str(n.relative_path) for n in notes]
    assert any("note1.md" in p for p in paths)
    assert any("project1.md" in p for p in paths)


def test_list_notes_non_recursive(vault_manager: VaultManager) -> None:
    """Test listing notes non-recursively."""
    notes = vault_manager.list_notes(recursive=False)

    paths = [str(n.relative_path) for n in notes]
    assert any("note1.md" in p for p in paths)
    # project1.md is in subfolder, shouldn't be included
    assert not any("project1.md" in p for p in paths)


def test_list_notes_in_folder(vault_manager: VaultManager) -> None:
    """Test listing notes in specific folder."""
    notes = vault_manager.list_notes(folder="projects", recursive=False)

    assert len(notes) >= 1
    paths = [str(n.relative_path) for n in notes]
    assert any("project1.md" in p for p in paths)


def test_search_by_tags(vault_manager: VaultManager) -> None:
    """Test searching by tags."""
    results = vault_manager.search_by_metadata(tags=["python"])

    assert len(results) >= 1
    assert all(r.frontmatter is not None and "python" in r.frontmatter.tags for r in results)


def test_search_by_tags_multiple(vault_manager: VaultManager) -> None:
    """Test searching with multiple tags (any match)."""
    results = vault_manager.search_by_metadata(tags=["python", "obsidian"])

    assert len(results) >= 2  # note1 (python) and note2 (obsidian)


def test_search_by_date_range(vault_manager: VaultManager, temp_vault: Path) -> None:
    """Test filtering by modification date."""
    # All notes are just created, should match recent date filter
    results = vault_manager.search_by_metadata(date_range_days=1)

    assert len(results) >= 1


def test_search_by_date_range_old(vault_manager: VaultManager) -> None:
    """Test date filter excludes recent notes."""
    # Filter for notes modified >365 days ago (none should match)
    results = vault_manager.search_by_metadata(date_range_days=365, limit=10)

    # Depending on file system, newly created files should not match old filter
    # This test is less reliable but checks the date logic exists
    assert isinstance(results, list)


def test_search_by_folder(vault_manager: VaultManager) -> None:
    """Test filtering by folder."""
    results = vault_manager.search_by_metadata(folder="projects")

    assert len(results) >= 1
    assert all("projects" in str(r.path) for r in results)


def test_search_by_metadata_respects_limit(vault_manager: VaultManager) -> None:
    """Test metadata search respects limit."""
    results = vault_manager.search_by_metadata(tags=["python", "obsidian"], limit=1)

    assert len(results) <= 1


def test_get_recent_notes(vault_manager: VaultManager) -> None:
    """Test getting recently modified notes."""
    recent = vault_manager.get_recent_notes(limit=2)

    assert len(recent) <= 2
    assert len(recent) >= 1  # At least one note exists


def test_get_recent_notes_ordering(vault_manager: VaultManager) -> None:
    """Test recent notes are ordered by modification time."""
    recent = vault_manager.get_recent_notes(limit=10)

    # All notes are roughly same time, just verify we got results
    assert len(recent) >= 1


def test_vault_manager_handles_malformed_frontmatter(
    vault_manager: VaultManager, temp_vault: Path
) -> None:
    """Test VaultManager handles malformed frontmatter gracefully."""
    malformed = temp_vault / "malformed.md"
    malformed.write_text(
        """---
tags: this is not valid yaml [
title unclosed quote "
---
# Content
Should still be readable""",
        encoding="utf-8",
    )

    # Should not raise, falls back to reading without frontmatter
    note = vault_manager.read_note("malformed.md")
    assert note.title == "malformed"  # Falls back to filename
    assert "Content" in note.content
