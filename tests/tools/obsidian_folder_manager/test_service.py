"""Tests for folder manager service layer."""

import pytest

from src.tools.obsidian_folder_manager.schemas import (
    FolderOperation,
    ManageFolderRequest,
    ResponseFormat,
)
from src.tools.obsidian_folder_manager.service import manage_folder_service


pytestmark = pytest.mark.unit


class TestCreateFolderOperation:
    """Tests for CREATE folder operation."""

    async def test_create_simple_folder(self, tmp_path):
        """Test creating a simple folder."""
        vault = tmp_path / "vault"
        vault.mkdir()

        request = ManageFolderRequest(
            path="projects",
            operation=FolderOperation.CREATE,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert (vault / "projects").exists()
        assert (vault / "projects").is_dir()

    async def test_create_nested_folder_with_parents(self, tmp_path):
        """Test creating nested folder with parent creation."""
        vault = tmp_path / "vault"
        vault.mkdir()

        request = ManageFolderRequest(
            path="projects/2025/new-project",
            operation=FolderOperation.CREATE,
            create_parents=True,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert (vault / "projects" / "2025" / "new-project").exists()

    async def test_create_folder_idempotent(self, tmp_path):
        """Test creating folder that already exists is idempotent."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "existing").mkdir()

        request = ManageFolderRequest(
            path="existing",
            operation=FolderOperation.CREATE,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert result.metadata["already_existed"] is True

    async def test_create_dry_run(self, tmp_path):
        """Test dry run does not create folder."""
        vault = tmp_path / "vault"
        vault.mkdir()

        request = ManageFolderRequest(
            path="projects",
            operation=FolderOperation.CREATE,
            dry_run=True,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert not (vault / "projects").exists()
        assert result.metadata["dry_run"] is True


class TestRenameFolderOperation:
    """Tests for RENAME folder operation."""

    async def test_rename_simple_folder(self, tmp_path):
        """Test renaming a folder."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "old-name").mkdir()

        request = ManageFolderRequest(
            path="old-name",
            operation=FolderOperation.RENAME,
            new_name="new-name",
            update_wikilinks=False,  # Disable for simple test
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert not (vault / "old-name").exists()
        assert (vault / "new-name").exists()
        assert result.new_path == "new-name"

    async def test_rename_with_wikilink_updates(self, tmp_path):
        """Test renaming folder updates wikilinks."""
        vault = tmp_path / "vault"
        vault.mkdir()

        # Create folder with a note
        folder = vault / "old-folder"
        folder.mkdir()
        (folder / "note.md").write_text("# Note")

        # Create a note that links to the folder contents
        (vault / "index.md").write_text("See [[old-folder/note]]")

        request = ManageFolderRequest(
            path="old-folder",
            operation=FolderOperation.RENAME,
            new_name="new-folder",
            update_wikilinks=True,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert (vault / "new-folder").exists()

        # Check wikilink was updated
        index_content = (vault / "index.md").read_text()
        assert "[[new-folder/note]]" in index_content
        assert "[[old-folder/note]]" not in index_content

    async def test_rename_rejects_invalid_name(self, tmp_path):
        """Test renaming with invalid folder name is rejected."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "folder").mkdir()

        request = ManageFolderRequest(
            path="folder",
            operation=FolderOperation.RENAME,
            new_name="CON",  # Windows reserved name
        )

        with pytest.raises(ValueError, match="reserved Windows name"):
            await manage_folder_service(
                request=request,
                vault_path=str(vault),
                max_folder_depth=10,
                max_wikilink_scan_notes=1000,
            )


class TestMoveFolderOperation:
    """Tests for MOVE folder operation."""

    async def test_move_folder_to_existing_destination(self, tmp_path):
        """Test moving folder to existing destination."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "source").mkdir()
        (vault / "dest").mkdir()

        request = ManageFolderRequest(
            path="source",
            operation=FolderOperation.MOVE,
            destination="dest",
            update_wikilinks=False,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert not (vault / "source").exists()
        assert (vault / "dest" / "source").exists()

    async def test_move_detects_circular_move(self, tmp_path):
        """Test that circular move is detected and rejected."""
        vault = tmp_path / "vault"
        vault.mkdir()
        parent = vault / "parent"
        parent.mkdir()
        (parent / "child").mkdir()

        request = ManageFolderRequest(
            path="parent",
            operation=FolderOperation.MOVE,
            destination="parent/child",  # Circular!
        )

        # Either our code or shutil.move will catch this
        with pytest.raises((ValueError, Exception)):
            await manage_folder_service(
                request=request,
                vault_path=str(vault),
                max_folder_depth=10,
                max_wikilink_scan_notes=1000,
            )


class TestDeleteFolderOperation:
    """Tests for DELETE folder operation."""

    async def test_delete_empty_folder(self, tmp_path):
        """Test deleting empty folder."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "empty").mkdir()

        request = ManageFolderRequest(
            path="empty",
            operation=FolderOperation.DELETE,
            confirm_path="empty",
            force=False,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert not (vault / "empty").exists()

    async def test_delete_non_empty_requires_force(self, tmp_path):
        """Test deleting non-empty folder requires force."""
        vault = tmp_path / "vault"
        vault.mkdir()
        folder = vault / "nonempty"
        folder.mkdir()
        (folder / "file.md").write_text("content")

        request = ManageFolderRequest(
            path="nonempty",
            operation=FolderOperation.DELETE,
            confirm_path="nonempty",
            force=False,
        )

        with pytest.raises(ValueError, match="not empty"):
            await manage_folder_service(
                request=request,
                vault_path=str(vault),
                max_folder_depth=10,
                max_wikilink_scan_notes=1000,
            )

    async def test_delete_with_force_deletes_contents(self, tmp_path):
        """Test deleting non-empty folder with force."""
        vault = tmp_path / "vault"
        vault.mkdir()
        folder = vault / "nonempty"
        folder.mkdir()
        (folder / "file.md").write_text("content")
        (folder / "subfolder").mkdir()

        request = ManageFolderRequest(
            path="nonempty",
            operation=FolderOperation.DELETE,
            confirm_path="nonempty",
            force=True,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert not (vault / "nonempty").exists()

    async def test_delete_requires_confirmation(self, tmp_path):
        """Test delete requires confirm_path to match."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "folder").mkdir()

        # This should be caught by model validator
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="must match"):
            ManageFolderRequest(
                path="folder",
                operation=FolderOperation.DELETE,
                confirm_path="wrong-path",  # Doesn't match!
                force=True,
            )

    async def test_delete_critical_folder_blocked(self, tmp_path):
        """Test deleting critical folders is blocked."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()

        request = ManageFolderRequest(
            path=".obsidian",
            operation=FolderOperation.DELETE,
            confirm_path=".obsidian",
            force=True,
        )

        with pytest.raises(ValueError, match="critical folder"):
            await manage_folder_service(
                request=request,
                vault_path=str(vault),
                max_folder_depth=10,
                max_wikilink_scan_notes=1000,
            )


class TestListFolderOperation:
    """Tests for LIST folder operation."""

    async def test_list_immediate_children(self, tmp_path):
        """Test listing immediate children."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "folder1").mkdir()
        (vault / "folder2").mkdir()
        (vault / "folder3").mkdir()

        request = ManageFolderRequest(
            path=".",
            operation=FolderOperation.LIST,
            recursive=False,
            include_stats=False,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        folders = result.metadata["folders"]
        assert len(folders) == 3
        folder_names = [f["name"] for f in folders]
        assert "folder1" in folder_names
        assert "folder2" in folder_names
        assert "folder3" in folder_names

    async def test_list_with_stats(self, tmp_path):
        """Test listing with statistics."""
        vault = tmp_path / "vault"
        vault.mkdir()
        folder = vault / "folder"
        folder.mkdir()
        (folder / "note1.md").write_text("content")
        (folder / "note2.md").write_text("more content")

        request = ManageFolderRequest(
            path=".",
            operation=FolderOperation.LIST,
            recursive=False,
            include_stats=True,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        folders = result.metadata["folders"]
        folder_info = folders[0]
        assert folder_info["note_count"] == 2
        assert folder_info["total_size_bytes"] > 0

    async def test_list_recursive(self, tmp_path):
        """Test recursive folder listing."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "level1").mkdir()
        (vault / "level1" / "level2").mkdir()
        (vault / "level1" / "level2" / "level3").mkdir()

        request = ManageFolderRequest(
            path=".",
            operation=FolderOperation.LIST,
            recursive=True,
            include_stats=False,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        folders = result.metadata["folders"]
        assert len(folders) == 3  # All nested folders

    async def test_list_pagination(self, tmp_path):
        """Test folder listing pagination."""
        vault = tmp_path / "vault"
        vault.mkdir()

        # Create 10 folders
        for i in range(10):
            (vault / f"folder{i}").mkdir()

        request = ManageFolderRequest(
            path=".",
            operation=FolderOperation.LIST,
            recursive=False,
            max_results=5,
            offset=0,
        )

        result = await manage_folder_service(
            request=request,
            vault_path=str(vault),
            max_folder_depth=10,
            max_wikilink_scan_notes=1000,
        )

        assert result.success is True
        assert result.metadata["total_folders"] == 10
        assert result.metadata["returned"] == 5
        assert result.metadata["has_more"] is True


class TestSecurityValidation:
    """Tests for security validation."""

    async def test_rejects_path_traversal(self, tmp_path):
        """Test that path traversal is rejected."""
        vault = tmp_path / "vault"
        vault.mkdir()

        request = ManageFolderRequest(
            path="../etc",
            operation=FolderOperation.CREATE,
        )

        with pytest.raises(Exception):  # SecurityError or ValueError
            await manage_folder_service(
                request=request,
                vault_path=str(vault),
                max_folder_depth=10,
                max_wikilink_scan_notes=1000,
            )

    async def test_cannot_rename_critical_folder(self, tmp_path):
        """Test that critical folders cannot be renamed."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / ".obsidian").mkdir()

        request = ManageFolderRequest(
            path=".obsidian",
            operation=FolderOperation.RENAME,
            new_name="obsidian-renamed",
        )

        with pytest.raises(ValueError, match="critical folder"):
            await manage_folder_service(
                request=request,
                vault_path=str(vault),
                max_folder_depth=10,
                max_wikilink_scan_notes=1000,
            )
