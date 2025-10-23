"""Vault security utilities for path validation and access control.

This module provides security functions to:
- Validate paths to prevent directory traversal attacks
- Block access to sensitive directories (.obsidian, .git, etc.)
- Enforce file type restrictions for vault operations
"""

from pathlib import Path

from src.shared.logging import get_logger


logger = get_logger(__name__)

# Directories that should never be accessed
BLOCKED_PATTERNS: list[str] = [
    ".obsidian/**",
    ".git/**",
    ".trash/**",
    "node_modules/**",
]

# File extensions allowed for vault operations
ALLOWED_EXTENSIONS: set[str] = {".md", ".markdown", ".txt"}

# Windows reserved folder/file names
WINDOWS_RESERVED_NAMES: set[str] = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

# Invalid characters for folder names (Windows + Unix restrictions)
INVALID_FOLDER_CHARS: set[str] = {"<", ">", ":", '"', "|", "?", "*", "/", "\\"}

# Critical folders that cannot be operated on
CRITICAL_FOLDERS: set[str] = {".obsidian", ".git", ".trash", "node_modules"}


class SecurityError(Exception):
    """Raised when a security violation is detected."""


def validate_vault_path(vault_root: str, requested_path: str) -> str:
    """Validate and resolve a path within the vault.

    Args:
        vault_root: Absolute path to the vault root directory.
        requested_path: Relative path requested by user (or absolute path to validate).

    Returns:
        Absolute canonical path to the file/directory.

    Raises:
        SecurityError: If path is outside vault or validation fails.
        ValueError: If vault_root is empty or invalid.
    """
    if not vault_root:
        logger.error("vault_path_validation_failed", reason="empty_vault_root")
        msg = "Vault root path is not configured"
        raise ValueError(msg)

    try:
        # Canonicalize vault root
        vault_root_path = Path(vault_root).resolve(strict=False)

        # Handle requested path
        if Path(requested_path).is_absolute():
            # If absolute path provided, resolve it
            full_path = Path(requested_path).resolve(strict=False)
        else:
            # If relative path, join with vault root
            full_path = (vault_root_path / requested_path).resolve(strict=False)

        # Check if path is within vault (prevent directory traversal)
        try:
            full_path.relative_to(vault_root_path)
        except ValueError:
            logger.warning(
                "path_traversal_attempt",
                vault_root=str(vault_root_path),
                requested_path=requested_path,
                resolved_path=str(full_path),
            )
            msg = f"Path '{requested_path}' is outside vault root"
            raise SecurityError(msg) from None

        logger.debug(
            "path_validated",
            vault_root=str(vault_root_path),
            requested_path=requested_path,
            resolved_path=str(full_path),
        )

        return str(full_path)

    except (OSError, RuntimeError) as e:
        logger.exception(
            "path_validation_error",
            vault_root=vault_root,
            requested_path=requested_path,
            error=str(e),
        )
        msg = f"Failed to validate path: {e}"
        raise SecurityError(msg) from e


def is_path_allowed(path: str) -> bool:
    """Check if a path is allowed based on security rules.

    Args:
        path: Path to check (can be relative or absolute).

    Returns:
        True if path is allowed, False if blocked.
    """
    file_path = Path(path)

    # Check file extension
    if file_path.suffix and file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        logger.debug(
            "path_blocked_extension",
            path=path,
            extension=file_path.suffix,
            allowed_extensions=list(ALLOWED_EXTENSIONS),
        )
        return False

    # Check against blocked patterns
    path_str = str(file_path).replace("\\", "/")  # Normalize for Windows
    for pattern in BLOCKED_PATTERNS:
        # Simple glob pattern matching (supports ** wildcards)
        pattern_base = pattern.removesuffix("/**")
        pattern_parts = pattern_base.split("/")
        path_parts = path_str.split("/")

        # Check if any part of path matches blocked pattern
        for i in range(len(path_parts)):
            if path_parts[i : i + len(pattern_parts)] == pattern_parts:
                logger.debug("path_blocked_pattern", path=path, pattern=pattern)
                return False

    return True


def validate_folder_name(folder_name: str) -> None:
    """Validate a folder name against security and filesystem rules.

    This function ensures folder names are safe for cross-platform use by:
    - Blocking Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
    - Blocking invalid characters (<>:"|?*) and path separators (/, \\)
    - Blocking empty or whitespace-only names
    - Trimming leading/trailing whitespace

    Args:
        folder_name: The folder name to validate (single component, not full path).

    Raises:
        ValueError: If folder_name is invalid (empty, reserved, or contains invalid chars).

    Examples:
        >>> validate_folder_name("my-project")  # OK
        >>> validate_folder_name("CON")  # Raises ValueError (Windows reserved)
        >>> validate_folder_name("folder/subfolder")  # Raises ValueError (contains separator)
        >>> validate_folder_name("")  # Raises ValueError (empty)
    """
    # Strip whitespace
    name = folder_name.strip()

    # Check for empty name
    if not name:
        logger.warning("folder_name_validation_failed", reason="empty_name", folder_name=folder_name)
        msg = "Folder name cannot be empty or whitespace-only"
        raise ValueError(msg)

    # Check for Windows reserved names (case-insensitive)
    if name.upper() in WINDOWS_RESERVED_NAMES:
        logger.warning(
            "folder_name_validation_failed",
            reason="reserved_name",
            folder_name=name,
            reserved_names=list(WINDOWS_RESERVED_NAMES),
        )
        msg = f"Folder name '{name}' is a reserved Windows name and cannot be used"
        raise ValueError(msg)

    # Check for invalid characters
    invalid_chars_found = INVALID_FOLDER_CHARS & set(name)
    if invalid_chars_found:
        logger.warning(
            "folder_name_validation_failed",
            reason="invalid_characters",
            folder_name=name,
            invalid_chars=list(invalid_chars_found),
        )
        msg = f"Folder name '{name}' contains invalid characters: {', '.join(invalid_chars_found)}"
        raise ValueError(msg)

    logger.debug("folder_name_validated", folder_name=name)


def is_critical_folder(path: Path, vault_root: Path) -> bool:
    """Check if a path represents a critical folder that cannot be operated on.

    Critical folders include:
    - Vault root itself
    - .obsidian (Obsidian configuration)
    - .git (version control)
    - .trash (Obsidian trash)
    - node_modules (dependencies)

    Args:
        path: Path to check (resolved absolute path).
        vault_root: Vault root path (resolved absolute path).

    Returns:
        True if path is a critical folder, False otherwise.
    """
    # Check if path is vault root
    if path == vault_root:
        return True

    # Check if path is a critical folder
    try:
        relative_path = path.relative_to(vault_root)
        # Get first component of relative path
        parts = relative_path.parts
        if parts and parts[0] in CRITICAL_FOLDERS:
            return True
    except ValueError:
        # Path is not relative to vault_root
        pass

    return False
