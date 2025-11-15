"""Central tool registration for Obsidian AI Agent.

This module imports all feature tool modules to register tools with vault_agent
via side-effect imports. The @vault_agent.tool decorator registers tools when
the module is imported.

This provides a single location to see all available tools and ensures tools
are registered before the agent is used.

Pattern: Import tool modules with noqa: F401 (unused import) because we want
the side-effect of tool registration, not the actual functions.
"""

# Import feature tool modules for side-effect registration
# Side-effect imports for tool registration - suppress linting warnings
# ruff: noqa: F401, I001
# pyright: reportUnusedImport=false
import app.features.obsidian_query_vault_tool.obsidian_query_vault_tool
import app.features.obsidian_note_manager_tool.obsidian_note_manager_tool
import app.features.obsidian_get_context_tool.obsidian_get_context_tool
import app.features.brave_web_search_tool.brave_web_search_tool

__all__: list[str] = []  # No exports - side-effect only module
