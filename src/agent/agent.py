"""Pydantic AI agent initialization and configuration.

This module creates and manages the global agent instance with:
- Model configuration from settings
- Tool registration system
- Singleton pattern for efficient resource usage
"""

from pydantic_ai import Agent

from src.agent.schemas import AgentDependencies
from src.shared.config import Settings, get_settings
from src.shared.logging import get_logger


logger = get_logger(__name__)

# Global agent instance
_agent: Agent[AgentDependencies, str] | None = None


def create_agent(settings: Settings | None = None) -> Agent[AgentDependencies, str]:
    """Create and configure Pydantic AI agent with tools.

    Args:
        settings: Application settings. If None, uses get_settings().

    Returns:
        Configured agent instance with registered tools.

    Raises:
        UserError: If the required API key for the selected provider is not configured.
    """
    if settings is None:
        settings = get_settings()

    # Extract provider prefix from model name (e.g., "anthropic" from "anthropic:claude-3-5-sonnet")
    provider_prefix = settings.model_name.split(":")[0] if ":" in settings.model_name else "unknown"

    logger.info(
        "agent_creation_started",
        model=settings.model_name,
        provider=provider_prefix,
    )

    agent = Agent(
        model=settings.model_name,
        deps_type=AgentDependencies,
        system_prompt=settings.agent_system_prompt,
        retries=settings.agent_retries,
        output_retries=settings.agent_output_retries,
    )

    # Register tools (lazy import to avoid circular dependency)
    # Consolidated Obsidian Tools (Anthropic Option B Architecture)
    if settings.enable_obsidian_note_manager:
        from src.tools.obsidian_note_manager.tool import register_obsidian_note_manager_tool  # noqa: PLC0415

        register_obsidian_note_manager_tool(agent)

    if settings.enable_obsidian_vault_query:
        from src.tools.obsidian_vault_query.tool import register_obsidian_vault_query_tool  # noqa: PLC0415

        register_obsidian_vault_query_tool(agent)

    if settings.enable_obsidian_graph_analyzer:
        from src.tools.obsidian_graph_analyzer.tool import register_obsidian_graph_analyzer_tool  # noqa: PLC0415

        register_obsidian_graph_analyzer_tool(agent)

    if settings.enable_obsidian_vault_organizer:
        from src.tools.obsidian_vault_organizer.tool import register_obsidian_vault_organizer_tool  # noqa: PLC0415

        register_obsidian_vault_organizer_tool(agent)

    if settings.enable_obsidian_folder_manager:
        from src.tools.obsidian_folder_manager.tool import register_obsidian_folder_manager_tool  # noqa: PLC0415

        register_obsidian_folder_manager_tool(agent)

    if settings.enable_web_search:
        from src.tools.web_search.tool import register_web_search_tool  # noqa: PLC0415

        register_web_search_tool(agent)

    logger.info(
        "agent_created",
        model=settings.model_name,
        provider=provider_prefix,
    )
    logger.debug(
        "agent_provider_initialized",
        provider=provider_prefix,
        model_full_name=settings.model_name,
    )
    return agent


def get_agent(settings: Settings | None = None) -> Agent[AgentDependencies, str]:
    """Get or create the global agent instance.

    Args:
        settings: Application settings. If None, uses get_settings().

    Returns:
        The configured agent instance.
    """
    global _agent  # noqa: PLW0603
    if _agent is None:
        _agent = create_agent(settings)
    return _agent
