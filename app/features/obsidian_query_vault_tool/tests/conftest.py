"""Test fixtures for obsidian_query_vault_tool."""

from pathlib import Path

import pytest

from app.core.agents import AgentDeps
from app.core.config import get_settings
from app.shared.vault.vault_manager import VaultManager


@pytest.fixture
def test_vault_path(tmp_path: Path) -> Path:
    """Create a temporary vault with test notes.

    Creates 3 test notes:
    - project_alpha.md: Note with frontmatter (tags, dates)
    - meeting_notes.md: Note with frontmatter (tags)
    - daily_journal.md: Note without frontmatter

    Args:
        tmp_path: Pytest fixture providing temporary directory.

    Returns:
        Path to test vault root.
    """
    vault_root = tmp_path / "test_vault"
    vault_root.mkdir()

    # Note 1: Project with frontmatter
    (vault_root / "project_alpha.md").write_text(
        """---
title: Project Alpha
tags:
  - project
  - ai
  - active
status: in-progress
created: 2024-01-15
---

# Project Alpha

This is a research project on AI agents and tool integration.

## Goals
- Implement query vault tool
- Add context retrieval
- Enable note modifications
"""
    )

    # Note 2: Meeting notes with frontmatter
    (vault_root / "meeting_notes.md").write_text(
        """---
title: Team Meeting Notes
tags:
  - meeting
  - planning
date: 2024-01-20
---

# Team Meeting - January 20

Discussed project roadmap and tool priorities.

Action items:
- Review PRD
- Design vault query interface
"""
    )

    # Note 3: Daily journal without frontmatter
    (vault_root / "daily_journal.md").write_text(
        """# Daily Journal

Random thoughts and observations.

Today I learned about Pydantic AI and how tool registration works.
"""
    )

    return vault_root


@pytest.fixture
def test_vault_manager(test_vault_path: Path) -> VaultManager:
    """Create VaultManager instance for testing.

    Args:
        test_vault_path: Path to test vault from test_vault_path fixture.

    Returns:
        VaultManager configured with test vault.
    """
    return VaultManager(vault_path=str(test_vault_path))


@pytest.fixture
def test_agent_deps(test_vault_manager: VaultManager) -> AgentDeps:
    """Create AgentDeps for tool testing.

    Args:
        test_vault_manager: VaultManager from test_vault_manager fixture.

    Returns:
        AgentDeps with test vault manager and settings.
    """
    settings = get_settings()
    return AgentDeps(vault_manager=test_vault_manager, settings=settings)
