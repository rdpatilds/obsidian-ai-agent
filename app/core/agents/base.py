"""Base Pydantic AI agent for Obsidian vault interactions."""

from dataclasses import dataclass

from pydantic_ai import Agent

from app.core.config import get_settings

settings = get_settings()


@dataclass
class AgentDeps:
    """Dependencies for agent tools.

    Currently empty but establishes dependency injection pattern.
    Future: vault_manager, settings, etc.
    """

    pass


vault_agent: Agent[AgentDeps, str] = Agent(
    model=f"anthropic:{settings.llm_model}",
    instructions="""You are Paddy, an AI assistant for Obsidian vaults.

Your role is to help users query, read, and manage their Obsidian notes using natural language.

Guidelines:
- Be concise and helpful
- Provide clear explanations
- When you lack tools, explain what's needed

Currently, you have no tools but can discuss Obsidian workflows.
""",
    deps_type=AgentDeps,
    retries=2,
)
