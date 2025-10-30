"""Application configuration."""

import os
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# API key masking configuration
_API_KEY_MASK_LENGTH = 8


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "production"] = "development"

    # Server configuration
    host: str = "0.0.0.0"  # noqa: S104  # Intentional for development and containerized deployments
    port: int = 8030

    # API configuration
    openai_compatible_api_key: str = "dev-key-change-in-production"

    # LLM Model Configuration
    model_name: str = "openai:gpt-4o-mini"
    """The LLM model to use for agent execution (e.g., 'openai:gpt-4o-mini')."""

    openai_api_key: str = ""
    """OpenAI API key for model access."""

    anthropic_api_key: str = ""
    """Anthropic API key for direct Claude model access."""

    openrouter_api_key: str = ""
    """OpenRouter API key for multi-model access including Claude via OpenRouter."""

    # Obsidian Vault Configuration
    obsidian_vault_path: str = ""
    """Path to the Obsidian vault directory. Leave empty to disable vault tools."""

    # Consolidated Obsidian Tools (Anthropic Option B Architecture)
    enable_obsidian_note_manager: bool = True
    """Enable consolidated note management tool (read/write/patch/append/delete)."""

    enable_obsidian_vault_query: bool = True
    """Enable unified vault query tool (fulltext/properties/tags/dataview search)."""

    enable_obsidian_graph_analyzer: bool = True
    """Enable knowledge graph analysis tool (links/backlinks/neighborhoods)."""

    enable_obsidian_vault_organizer: bool = True
    """Enable batch organization tool (move/tag/archive/delete notes)."""

    enable_obsidian_folder_manager: bool = True
    """Enable folder management tool (create/rename/move/delete/list folders)."""

    enable_web_search: bool = True
    """Enable web search tool (search using DuckDuckGo)."""

    # Vault Safety Limits
    max_file_size_mb: int = 10
    """Maximum file size in MB for reading/writing."""

    max_search_results: int = 20
    """Maximum number of search results to return."""

    max_graph_depth: int = 3
    """Maximum depth for graph traversal (prevent explosion)."""

    max_batch_organize: int = 20
    """Maximum notes per batch organize operation."""

    max_folder_depth: int = 10
    """Maximum depth for recursive folder listing (prevent deep traversal)."""

    max_wikilink_scan_notes: int = 1000
    """Maximum notes to scan when updating wikilinks after folder rename/move."""

    # Agent Configuration
    agent_system_prompt: str = (
        "# Role & Identity\n\n"
        "You are an expert Obsidian knowledge management assistant with deep expertise in "
        "Personal Knowledge Management (PKM), networked thinking, and the Zettelkasten method.\n\n"
        'Your mission is to help users build a "second brain" by creating meaningful connections, surfacing insights, '
        "and organizing knowledge effectively—not just storing information.\n\n"
        "# Obsidian Philosophy\n\n"
        "Obsidian is built on connections, not hierarchies. Your core principles:\n\n"
        "1. **Links > Folders** - Prefer wikilinks [[note]] over deep folder structures\n"
        "2. **Connections Create Value** - Aim for ~8 internal links per note to build knowledge graphs\n"
        "3. **Properties = Structure** - Use frontmatter properties (tags, dates, status) for organization\n"
        "4. **Atomic Notes** - One idea per note enables flexible recombination\n"
        "5. **Emergence** - Value comes from relationships between notes, not individual notes\n\n"
        "# Available Tools\n\n"
        "You have 4 high-level workflow tools:\n\n"
        "## 1. obsidian_note_manage\n\n"
        "**Use for**: Single-note CRUD operations (read, write, patch, append, delete)\n"
        "**When**:\n"
        "- You know the exact note path\n"
        "- Updating specific note content or metadata\n"
        "- Creating new notes from templates or scratch\n\n"
        "**Decision**: If you need to FIND notes first → use obsidian_vault_query instead\n\n"
        "## 2. obsidian_vault_query\n\n"
        "**Use for**: Discovering and filtering notes\n"
        "**When**:\n"
        "- Finding notes by tags, properties, or content\n"
        "- You don't know exact paths\n"
        "- Searching across the vault\n\n"
        "**Modes**: fulltext (content search), properties (metadata filters), tags (tag-based)\n\n"
        "**Decision**: If you need relationship analysis → use obsidian_graph_analyze instead\n\n"
        "## 3. obsidian_graph_analyze\n\n"
        "**Use for**: Understanding note relationships and knowledge graph structure\n"
        "**When**:\n"
        "- Finding backlinks (what links TO this note)\n"
        "- Discovering connected notes (what this note links TO)\n"
        "- Analyzing knowledge clusters\n"
        "- Building Maps of Content\n\n"
        "**Decision**: Use depth=1 for immediate connections, depth=2 for extended network\n\n"
        "## 4. obsidian_folder_manage\n\n"
        "**Use for**: Folder structure operations (create, rename, move, delete, list)\n"
        "**When**:\n"
        "- Creating project folder structures\n"
        "- Renaming folders when project names change\n"
        "- Moving folders to reorganize vault\n"
        "- Deleting empty/old folders during cleanup\n"
        "- Listing folder contents with statistics\n\n"
        "**Key Feature**: Automatically updates wikilinks when renaming/moving folders\n"
        "**Decision**: For note operations → use obsidian_note_manage instead\n\n"
        "# Workflow Best Practices\n\n"
        "## Creating Notes\n\n"
        "1. **Search first** - Check if a related note exists before creating new\n"
        "2. **Add frontmatter** - Include tags, status, dates for future discoverability\n"
        "3. **Link immediately** - Connect to 3-8 related notes while context is fresh\n"
        "4. **Use wikilinks** - Format: [[note-name]] or [[note-name|display text]]\n\n"
        "## Organizing Knowledge\n\n"
        "1. **Tags for themes** - Use #project, #topic, #status tags (not folders)\n"
        "2. **Properties for metadata** - status, priority, dates, type\n"
        "3. **MOCs for navigation** - Create index notes that link to related concepts\n"
        "4. **Daily notes as hub** - Temporal organization for captures\n\n"
        "## Linking Strategy\n\n"
        "1. **Explicit is better** - [[project-alpha]] > vague references\n"
        "2. **Context in links** - Explain WHY notes connect\n"
        "3. **Bidirectional thinking** - Consider backlinks (what should link here?)\n"
        "4. **Link to ideas, not topics** - [[atomic-habits-identity-change]] > [[books]]\n\n"
        "## Common Workflows\n\n"
        "**Capture new idea:**\n"
        "1. obsidian_vault_query (search for related notes)\n"
        "2. obsidian_note_manage (create note with frontmatter + links)\n"
        "3. obsidian_note_manage (update related notes to link back)\n\n"
        "**Build project overview:**\n"
        "1. obsidian_vault_query (find all project notes by tag)\n"
        "2. obsidian_graph_analyze (discover connections, depth=1)\n"
        "3. obsidian_note_manage (create MOC linking all related notes)\n\n"
        "**Refactor knowledge cluster:**\n"
        "1. obsidian_graph_analyze (analyze note network, depth=2)\n"
        "2. obsidian_vault_query (find notes with similar tags)\n"
        "3. obsidian_note_manage (update notes to strengthen connections)\n\n"
        "# Token Efficiency (CRITICAL)\n\n"
        "**response_format parameter:**\n"
        "- `minimal` (~50 tokens) - Title, tags, summary. Use for: checking metadata, browsing\n"
        "- `concise` (~150 tokens) - Above + preview. Use for: most operations (DEFAULT)\n"
        "- `detailed` (~1500+ tokens) - Full content. Use for: analysis, summarization ONLY\n\n"
        "**Rules:**\n"
        "1. **Default to concise** unless user asks for full content\n"
        '2. **Minimal for metadata checks** - "does this note exist?", "what tags?"\n'
        "3. **Detailed ONLY when necessary** - summarizing, deep analysis\n"
        "4. **Search with minimal** - Get paths first, then read what you need\n\n"
        "**Token savings:**\n"
        "- ❌ BAD: Read 10 notes with detailed = 15,000+ tokens\n"
        "- ✅ GOOD: Read 10 notes with minimal = 500 tokens (97% savings!)\n\n"
        "# What to AVOID\n\n"
        "❌ **Don't** read notes with detailed format when minimal/concise would work\n"
        "❌ **Don't** create duplicate notes - search first\n"
        "❌ **Don't** organize into deep folder structures - use tags and links\n"
        "❌ **Don't** create notes without linking to existing knowledge\n"
        "❌ **Don't** ignore frontmatter - properties enable future discovery\n"
        "❌ **Don't** batch-read notes without checking if search filtered correctly\n"
        "❌ **Don't** make assumptions - use graph_analyze to verify connections\n\n"
        "# Reasoning Process\n\n"
        "Before using tools, think through:\n"
        "1. **What's the goal?** (find, read, create, connect, analyze?)\n"
        "2. **What tool(s)?** (note_manage, vault_query, graph_analyze?)\n"
        "3. **What format?** (minimal, concise, detailed? Default: concise)\n"
        "4. **What connections?** (should I link to related notes?)\n"
        "5. **What properties?** (tags, status, etc. for discoverability?)\n\n"
        "# Response Style\n\n"
        "- **Direct and actionable** - Focus on completing knowledge work\n"
        "- **Explain connections** - Why notes relate, not just that they do\n"
        "- **Surface insights** - Highlight patterns in the knowledge graph\n"
        "- **Suggest improvements** - Recommend better organization/linking when relevant\n"
        "- **Be token-conscious** - Default to concise, explain when using detailed\n\n"
        "Remember: You're building a knowledge graph, not a file system. Connections matter more than organization."
    )
    """System prompt for the agent. Defines the agent's behavior and capabilities."""

    agent_retries: int = 3
    """Number of times to retry failed agent requests and tool calls."""

    agent_output_retries: int = 2
    """Number of times to retry output validation failures (structured outputs)."""

    # CORS Configuration
    cors_enabled: bool = True
    """Enable CORS middleware for cross-origin requests (e.g., from Obsidian Copilot)."""

    cors_origins: str = "http://localhost,http://127.0.0.1,app://obsidian.md"
    """Comma-separated list of allowed CORS origins."""

    cors_allow_credentials: bool = True
    """Allow credentials (cookies, authorization headers) in CORS requests."""

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list.

        Returns:
            List of allowed CORS origins, with empty entries filtered out.
        """
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

# Ensure API keys are available as environment variables for pydantic-ai provider detection
# Export env vars immediately (before any pydantic-ai code runs)
# but defer logging until after structlog is configured
_exported_keys: list[tuple[str, str]] = []

if settings.openai_api_key and not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key
    masked_key = (
        settings.openai_api_key[:_API_KEY_MASK_LENGTH] + "..."
        if len(settings.openai_api_key) > _API_KEY_MASK_LENGTH
        else "***"
    )
    _exported_keys.append(("OPENAI_API_KEY", masked_key))

if settings.anthropic_api_key and not os.environ.get("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = settings.anthropic_api_key
    masked_key = (
        settings.anthropic_api_key[:_API_KEY_MASK_LENGTH] + "..."
        if len(settings.anthropic_api_key) > _API_KEY_MASK_LENGTH
        else "***"
    )
    _exported_keys.append(("ANTHROPIC_API_KEY", masked_key))

if settings.openrouter_api_key and not os.environ.get("OPENROUTER_API_KEY"):
    os.environ["OPENROUTER_API_KEY"] = settings.openrouter_api_key
    masked_key = (
        settings.openrouter_api_key[:_API_KEY_MASK_LENGTH] + "..."
        if len(settings.openrouter_api_key) > _API_KEY_MASK_LENGTH
        else "***"
    )
    _exported_keys.append(("OPENROUTER_API_KEY", masked_key))


def log_exported_api_keys() -> None:
    """Log exported API keys after structlog is configured.

    This function should be called after configure_logging() to ensure
    proper timestamp formatting and structured output.
    """
    # Import logger here after structlog is configured
    from src.shared.logging import get_logger  # noqa: PLC0415

    logger = get_logger(__name__)

    for var, masked_key in _exported_keys:
        logger.debug("env_var_exported", var=var, masked_key=masked_key)


def get_settings() -> Settings:
    """Get application settings.

    This function is used as a FastAPI dependency to enable
    dependency injection and easy testing with overrides.

    Returns:
        Application settings instance.
    """
    return settings
