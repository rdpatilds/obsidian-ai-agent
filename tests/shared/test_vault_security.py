"""Tests for vault security utilities."""

import pytest

from src.shared.vault_security import (
    SecurityError,
    is_critical_folder,
    is_path_allowed,
    validate_folder_name,
    validate_vault_path,
)


pytestmark = pytest.mark.unit


class TestValidateVaultPath:
    """Tests for validate_vault_path function."""

    def test_validates_simple_relative_path(self, tmp_path):
        """Test validation of simple relative path."""
        vault = str(tmp_path)
        result = validate_vault_path(vault, "test.md")
        expected = str(tmp_path / "test.md")
        assert result == expected

    def test_validates_nested_relative_path(self, tmp_path):
        """Test validation of nested relative path."""
        vault = str(tmp_path)
        result = validate_vault_path(vault, "folder/subfolder/note.md")
        expected = str(tmp_path / "folder" / "subfolder" / "note.md")
        assert result == expected

    def test_validates_absolute_path_within_vault(self, tmp_path):
        """Test validation of absolute path that is within vault."""
        vault = str(tmp_path)
        test_file = tmp_path / "test.md"
        result = validate_vault_path(vault, str(test_file))
        assert result == str(test_file)

    def test_prevents_directory_traversal_with_dotdot(self, tmp_path):
        """Test prevention of directory traversal using ../."""
        vault = str(tmp_path)
        with pytest.raises(SecurityError, match="outside vault root"):
            validate_vault_path(vault, "../secret.md")

    def test_prevents_directory_traversal_with_absolute_path(self, tmp_path):
        """Test prevention of access to absolute path outside vault."""
        vault = str(tmp_path)
        with pytest.raises(SecurityError, match="outside vault root"):
            validate_vault_path(vault, "/etc/passwd")

    def test_prevents_directory_traversal_complex(self, tmp_path):
        """Test prevention of directory traversal with complex path."""
        vault = str(tmp_path)
        with pytest.raises(SecurityError, match="outside vault root"):
            validate_vault_path(vault, "folder/../../etc/passwd")

    def test_raises_error_for_empty_vault_root(self):
        """Test error raised when vault root is empty."""
        with pytest.raises(ValueError, match="not configured"):
            validate_vault_path("", "test.md")

    def test_normalizes_paths_with_dot_segments(self, tmp_path):
        """Test normalization of paths with . and .. segments that stay in vault."""
        vault = str(tmp_path)
        result = validate_vault_path(vault, "folder/../test.md")
        expected = str(tmp_path / "test.md")
        assert result == expected


class TestIsPathAllowed:
    """Tests for is_path_allowed function."""

    def test_allows_markdown_files(self):
        """Test that .md files are allowed."""
        assert is_path_allowed("test.md") is True
        assert is_path_allowed("folder/test.md") is True
        assert is_path_allowed("/vault/test.md") is True

    def test_allows_markdown_files_alternate_extension(self):
        """Test that .markdown files are allowed."""
        assert is_path_allowed("test.markdown") is True

    def test_allows_txt_files(self):
        """Test that .txt files are allowed."""
        assert is_path_allowed("notes.txt") is True

    def test_blocks_obsidian_directory(self):
        """Test that .obsidian directory is blocked."""
        assert is_path_allowed(".obsidian/config.json") is False
        assert is_path_allowed(".obsidian/plugins/plugin.js") is False

    def test_blocks_git_directory(self):
        """Test that .git directory is blocked."""
        assert is_path_allowed(".git/config") is False
        assert is_path_allowed(".git/hooks/pre-commit") is False

    def test_blocks_trash_directory(self):
        """Test that .trash directory is blocked."""
        assert is_path_allowed(".trash/deleted.md") is False

    def test_blocks_node_modules_directory(self):
        """Test that node_modules directory is blocked."""
        assert is_path_allowed("node_modules/package/index.js") is False

    def test_blocks_unsupported_extensions(self):
        """Test that unsupported file extensions are blocked."""
        assert is_path_allowed("script.js") is False
        assert is_path_allowed("image.png") is False
        assert is_path_allowed("data.json") is False
        assert is_path_allowed("executable.exe") is False

    def test_allows_files_without_extension(self):
        """Test that files without extension are allowed (edge case)."""
        # Files without extension should be allowed (extension check only applies if there is one)
        assert is_path_allowed("README") is True

    def test_case_insensitive_extension_matching(self):
        """Test that extension matching is case-insensitive."""
        assert is_path_allowed("test.MD") is True
        assert is_path_allowed("test.Markdown") is True
        assert is_path_allowed("test.TXT") is True

    def test_nested_allowed_path(self):
        """Test that nested paths in allowed directories work."""
        assert is_path_allowed("folder/subfolder/note.md") is True
        assert is_path_allowed("folder/subfolder/nested/deep.md") is True


class TestValidateFolderName:
    """Tests for validate_folder_name function."""

    def test_validates_simple_folder_name(self):
        """Test validation of simple folder name."""
        validate_folder_name("projects")  # Should not raise
        validate_folder_name("my-folder")  # Should not raise
        validate_folder_name("folder_123")  # Should not raise

    def test_validates_folder_with_spaces(self):
        """Test validation of folder name with spaces."""
        validate_folder_name("My Projects")  # Should not raise
        validate_folder_name("Project Alpha")  # Should not raise

    def test_validates_folder_with_unicode(self):
        """Test validation of folder name with unicode characters."""
        validate_folder_name("日本語")  # Should not raise
        validate_folder_name("Café")  # Should not raise

    def test_rejects_empty_folder_name(self):
        """Test rejection of empty folder name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_folder_name("")

    def test_rejects_whitespace_only_folder_name(self):
        """Test rejection of whitespace-only folder name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_folder_name("   ")
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_folder_name("\t\n")

    def test_rejects_windows_reserved_names(self):
        """Test rejection of Windows reserved names."""
        reserved_names = ["CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9"]
        for name in reserved_names:
            with pytest.raises(ValueError, match="reserved Windows name"):
                validate_folder_name(name)

    def test_rejects_windows_reserved_names_case_insensitive(self):
        """Test rejection of Windows reserved names (case-insensitive)."""
        with pytest.raises(ValueError, match="reserved Windows name"):
            validate_folder_name("con")
        with pytest.raises(ValueError, match="reserved Windows name"):
            validate_folder_name("Con")
        with pytest.raises(ValueError, match="reserved Windows name"):
            validate_folder_name("NuL")

    def test_rejects_invalid_characters(self):
        """Test rejection of invalid characters in folder name."""
        invalid_chars = ["<", ">", ":", '"', "|", "?", "*", "/", "\\"]
        for char in invalid_chars:
            folder_name = f"folder{char}name"
            with pytest.raises(ValueError, match="invalid characters"):
                validate_folder_name(folder_name)

    def test_rejects_path_separator_in_name(self):
        """Test rejection of path separators in folder name."""
        with pytest.raises(ValueError, match="invalid characters"):
            validate_folder_name("folder/subfolder")
        with pytest.raises(ValueError, match="invalid characters"):
            validate_folder_name("folder\\subfolder")

    def test_accepts_dots_and_dashes(self):
        """Test that dots and dashes are allowed in folder name."""
        validate_folder_name("my.folder")  # Should not raise
        validate_folder_name("my-folder")  # Should not raise
        validate_folder_name("folder.2025")  # Should not raise


class TestIsCriticalFolder:
    """Tests for is_critical_folder function."""

    def test_vault_root_is_critical(self, tmp_path):
        """Test that vault root itself is critical."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        assert is_critical_folder(vault_root, vault_root) is True

    def test_obsidian_folder_is_critical(self, tmp_path):
        """Test that .obsidian folder is critical."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        obsidian_folder = vault_root / ".obsidian"
        obsidian_folder.mkdir()
        assert is_critical_folder(obsidian_folder, vault_root) is True

    def test_git_folder_is_critical(self, tmp_path):
        """Test that .git folder is critical."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        git_folder = vault_root / ".git"
        git_folder.mkdir()
        assert is_critical_folder(git_folder, vault_root) is True

    def test_trash_folder_is_critical(self, tmp_path):
        """Test that .trash folder is critical."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        trash_folder = vault_root / ".trash"
        trash_folder.mkdir()
        assert is_critical_folder(trash_folder, vault_root) is True

    def test_node_modules_folder_is_critical(self, tmp_path):
        """Test that node_modules folder is critical."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        nm_folder = vault_root / "node_modules"
        nm_folder.mkdir()
        assert is_critical_folder(nm_folder, vault_root) is True

    def test_normal_folder_is_not_critical(self, tmp_path):
        """Test that normal folders are not critical."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        normal_folder = vault_root / "projects"
        normal_folder.mkdir()
        assert is_critical_folder(normal_folder, vault_root) is False

    def test_nested_folder_is_not_critical(self, tmp_path):
        """Test that nested folders are not critical."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        nested_folder = vault_root / "projects" / "2025"
        nested_folder.mkdir(parents=True)
        assert is_critical_folder(nested_folder, vault_root) is False

    def test_folder_outside_vault_is_not_critical(self, tmp_path):
        """Test that folders outside vault are not critical."""
        vault_root = tmp_path / "vault"
        vault_root.mkdir()
        outside_folder = tmp_path / "other"
        outside_folder.mkdir()
        assert is_critical_folder(outside_folder, vault_root) is False
