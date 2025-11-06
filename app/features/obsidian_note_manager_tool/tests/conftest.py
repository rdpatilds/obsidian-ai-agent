"""Test fixtures for Obsidian Note Manager Tool tests."""

from pathlib import Path

import pytest

from app.shared.vault.vault_manager import VaultManager


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Create temporary vault directory for testing.

    Args:
        tmp_path: pytest tmp_path fixture

    Returns:
        Path to temporary vault directory
    """
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir(parents=True, exist_ok=True)
    return vault_path


@pytest.fixture
def vault_manager(temp_vault: Path) -> VaultManager:
    """Create VaultManager instance for testing.

    Args:
        temp_vault: Path to temporary vault

    Returns:
        VaultManager instance pointing to temp vault
    """
    return VaultManager(vault_path=temp_vault)


@pytest.fixture
def sample_note(vault_manager: VaultManager) -> str:
    """Create a sample note for testing.

    Args:
        vault_manager: VaultManager instance

    Returns:
        Path to created sample note (relative to vault root)
    """
    note_path = "test_sample.md"
    content = "# Sample Note\n\nThis is a test note."
    metadata: dict[str, str | list[str] | int | float | bool] = {
        "tags": ["test", "sample"],
        "created": "2025-01-15",
    }
    vault_manager.write_note(note_path, content, metadata, overwrite=True)
    return note_path
