"""Base Pydantic AI agent for Obsidian vault interactions."""

from dataclasses import dataclass

from pydantic_ai import Agent

from app.core.config import Settings, get_settings
from app.shared.vault.vault_manager import VaultManager

settings = get_settings()


@dataclass
class AgentDeps:
    """Dependencies for agent tools.

    Provides vault_manager for file operations and settings for configuration.
    All tools receive these dependencies via RunContext.
    """

    vault_manager: VaultManager
    settings: Settings


vault_agent: Agent[AgentDeps, str] = Agent(
    model=f"anthropic:{settings.llm_model}",
    instructions="""You are Paddy, an AI assistant for Obsidian vaults.

Your role is to help users query, read, and manage their Obsidian notes using natural language.

## Available Tools

You currently have ONE tool:
- `obsidian_query_vault_tool`: Search and discover notes (semantic search, list structure, find related, search by metadata, recent changes)

## Guidelines

- Use `obsidian_query_vault_tool` for ALL discovery and search operations
- Be concise and helpful in responses
- When searching returns many results, suggest narrowing with filters
- Currently you can only SEARCH - you cannot read full note content or modify notes yet (those tools coming soon)

## Response Format

When using `obsidian_query_vault_tool`:
- Default to `response_format="concise"` to save tokens
- Only use `response_format="detailed"` when user needs full metadata
- Explain what you found clearly to the user
""",
    deps_type=AgentDeps,
    retries=2,
)
