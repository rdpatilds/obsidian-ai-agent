"""Domain models for Obsidian vault concepts."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class Frontmatter(BaseModel):
    """YAML frontmatter metadata from note."""

    tags: list[str] = Field(default_factory=list, description="Tags from frontmatter")
    title: str | None = Field(default=None, description="Title from frontmatter")
    created: datetime | None = Field(default=None, description="Creation date")
    modified: datetime | None = Field(default=None, description="Last modified date")
    custom: dict[str, str | int | float | bool | list[str]] = Field(
        default_factory=dict, description="Additional custom frontmatter fields"
    )


class Note(BaseModel):
    """Complete note representation."""

    path: Path = Field(..., description="Absolute path to note file")
    title: str = Field(..., description="Note title (from frontmatter or filename)")
    content: str = Field(..., description="Full note content (without frontmatter)")
    frontmatter: Frontmatter | None = Field(default=None, description="Parsed frontmatter metadata")
    word_count: int = Field(..., description="Number of words in content")

    @field_validator("path")
    @classmethod
    def validate_path_exists(cls, v: Path) -> Path:
        """Validate that path exists and is a file."""
        if not v.exists():
            raise ValueError(f"Note path does not exist: {v}")
        if not v.is_file():
            raise ValueError(f"Note path is not a file: {v}")
        return v


class VaultPath(BaseModel):
    """Validated vault path with root checking."""

    vault_root: Path = Field(..., description="Vault root directory")
    relative_path: str = Field(..., description="Relative path within vault")

    @property
    def absolute_path(self) -> Path:
        """Get absolute resolved path."""
        return (self.vault_root / self.relative_path).resolve()

    @field_validator("vault_root")
    @classmethod
    def validate_vault_root(cls, v: Path) -> Path:
        """Validate vault root exists and is directory."""
        if not v.exists():
            raise ValueError(f"Vault root does not exist: {v}")
        if not v.is_dir():
            raise ValueError(f"Vault root is not a directory: {v}")
        return v.resolve()

    def validate_within_vault(self) -> None:
        """Ensure path stays within vault_root (prevent directory traversal)."""
        abs_path = self.absolute_path
        if not str(abs_path).startswith(str(self.vault_root)):
            raise ValueError(f"Path {abs_path} is outside vault root {self.vault_root}")
