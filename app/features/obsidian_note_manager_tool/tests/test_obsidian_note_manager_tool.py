"""Integration tests for Obsidian Note Manager Tool."""

from unittest.mock import Mock

import pytest

from app.core.agents import AgentDeps
from app.core.config import get_settings
from app.features.obsidian_note_manager_tool.obsidian_note_manager_tool import (
    obsidian_note_manager_tool,
)
from app.shared.vault.vault_manager import VaultManager


@pytest.mark.asyncio
async def test_tool_create_note(vault_manager: VaultManager) -> None:
    """Test tool routing to create_note service."""
    deps = AgentDeps(vault_manager=vault_manager, settings=get_settings())
    ctx = Mock()
    ctx.deps = deps

    result = await obsidian_note_manager_tool(
        ctx,
        operation="create_note",
        target="test.md",
        content="# Test\n\nContent here.",
        metadata={"tags": ["test"]},
    )

    assert result.success is True
    assert result.operation == "create_note"

    # Verify file created
    note = vault_manager.read_note("test.md")
    assert note.content == "# Test\n\nContent here."


@pytest.mark.asyncio
async def test_tool_missing_required_param(vault_manager: VaultManager) -> None:
    """Test tool error when required parameter missing."""
    deps = AgentDeps(vault_manager=vault_manager, settings=get_settings())
    ctx = Mock()
    ctx.deps = deps

    with pytest.raises(ValueError, match="requires target and content"):
        await obsidian_note_manager_tool(
            ctx,
            operation="create_note",
            target="test.md",
            # Missing content parameter
        )


@pytest.mark.asyncio
async def test_tool_invalid_operation(vault_manager: VaultManager) -> None:
    """Test tool error with invalid operation."""
    deps = AgentDeps(vault_manager=vault_manager, settings=get_settings())
    ctx = Mock()
    ctx.deps = deps

    with pytest.raises(ValueError, match="Unknown operation"):
        await obsidian_note_manager_tool(
            ctx,
            operation="invalid_op",  # type: ignore[arg-type]
            target="test.md",
        )


@pytest.mark.asyncio
async def test_tool_update_note(vault_manager: VaultManager) -> None:
    """Test tool routing to update_note service."""
    # Create initial note
    vault_manager.write_note("update.md", "initial content", None, overwrite=True)

    deps = AgentDeps(vault_manager=vault_manager, settings=get_settings())
    ctx = Mock()
    ctx.deps = deps

    result = await obsidian_note_manager_tool(
        ctx,
        operation="update_note",
        target="update.md",
        content="updated content",
    )

    assert result.success is True
    assert result.operation == "update_note"

    # Verify content updated
    note = vault_manager.read_note("update.md")
    assert note.content == "updated content"


@pytest.mark.asyncio
async def test_tool_bulk_tag(vault_manager: VaultManager) -> None:
    """Test tool routing to bulk_tag service."""
    # Create test notes
    vault_manager.write_note("bulk1.md", "content1", None, overwrite=True)
    vault_manager.write_note("bulk2.md", "content2", None, overwrite=True)

    deps = AgentDeps(vault_manager=vault_manager, settings=get_settings())
    ctx = Mock()
    ctx.deps = deps

    result = await obsidian_note_manager_tool(
        ctx,
        operation="bulk_tag",
        targets=["bulk1.md", "bulk2.md"],
        metadata={"tags": ["bulk_test"]},
    )

    assert result.success is True
    assert result.operation == "bulk_tag"
    assert result.affected_count == 2

    # Verify tags added
    note1 = vault_manager.read_note("bulk1.md")
    assert "bulk_test" in (note1.frontmatter.tags if note1.frontmatter else [])
