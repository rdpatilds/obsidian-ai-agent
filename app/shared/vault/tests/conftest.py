"""Test fixtures for vault tests."""

from pathlib import Path

import pytest

from app.shared.vault.vault_manager import VaultManager


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Create temporary vault with sample notes.

    Creates a test vault structure:
    - note1.md (with frontmatter: tags, title)
    - note2.md (with frontmatter: tags only)
    - projects/project1.md (no frontmatter)
    """
    vault = tmp_path / "test_vault"
    vault.mkdir()

    # Note with full frontmatter
    note1 = vault / "note1.md"
    note1.write_text(
        """---
tags: [python, testing]
title: Note 1
---
# Note 1
This is a test note about Python programming and testing.""",
        encoding="utf-8",
    )

    # Note with partial frontmatter
    note2 = vault / "note2.md"
    note2.write_text(
        """---
tags: [obsidian]
---
# Note 2
Another test note about Obsidian vaults.""",
        encoding="utf-8",
    )

    # Note without frontmatter in subfolder
    projects = vault / "projects"
    projects.mkdir()
    note3 = projects / "project1.md"
    note3.write_text(
        "# Project 1\nNo frontmatter here. Just project documentation.",
        encoding="utf-8",
    )

    return vault


@pytest.fixture
def vault_manager(temp_vault: Path) -> VaultManager:
    """Create VaultManager with temp vault."""
    return VaultManager(temp_vault)
