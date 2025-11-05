"""Obsidian vault infrastructure - shared across all vault tools."""

from app.shared.vault.vault_manager import VaultManager
from app.shared.vault.vault_models import Frontmatter, Note, VaultPath

__all__ = ["Frontmatter", "Note", "VaultManager", "VaultPath"]
