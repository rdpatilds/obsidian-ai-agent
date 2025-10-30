# Obsidian AI Agent

OpenAI-compatible API agent for Obsidian CoPilot using FastAPI + Pydantic AI. Features high-level workflow tools designed for efficient agent interactions.

## Features

- **Workflow-Oriented Tools** - 4 high-level tools for note management, search, organization, and graph analysis
- **Token Efficiency** - Response format controls (minimal/concise/detailed) minimize API costs
- **Type-Safe** - Strict mypy configuration with complete type annotations
- **AI-Optimized Logging** - Structured logs designed for LLM debugging
- **Comprehensive Tests** - 248 tests with 100% pass rate

## Quick Start

### Installation

```bash
git clone https://github.com/Widinglabs/course-project-demo.git
cd course-project-demo
uv sync
cp .env.example .env
```

### Configuration

Edit `.env`:

```bash
OBSIDIAN_VAULT_PATH=/path/to/your/vault
ANTHROPIC_API_KEY=your-key-here
MODEL_NAME=anthropic:claude-haiku-4-5-20251001

# Optional: Tool toggles
ENABLE_OBSIDIAN_NOTE_MANAGER=true
ENABLE_OBSIDIAN_VAULT_QUERY=true
ENABLE_OBSIDIAN_VAULT_ORGANIZER=true
ENABLE_OBSIDIAN_GRAPH_ANALYZER=true
```

### Run

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8030 --reload
```

### Test

```bash
curl http://localhost:8030/health

curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": "Find all notes tagged #project and summarize them"
    }]
  }'
```

## Core Tools

### 1. obsidian_note_manage - Note Operations

Unified interface for reading, writing, patching, appending, and deleting notes.

```python
# Read with minimal format (50 tokens)
obsidian_note_manage(
    path="daily/2025-01-15.md",
    operation="read",
    response_format="minimal"
)

# Update content and metadata
obsidian_note_manage(
    path="projects/alpha.md",
    operation="update",
    content="# Project Alpha\n\nStatus: Complete",
    metadata_updates={"status": "completed", "priority": 1}
)

# Find and replace
obsidian_note_manage(
    path="notes/meeting.md",
    operation="patch",
    find_replace=("TODO", "DONE")
)
```

### 2. obsidian_vault_query - Search & Discovery

Search across full-text, properties, and tags with MongoDB-style operators.

```python
# Full-text search
obsidian_vault_query(
    query="machine learning",
    mode="fulltext",
    response_format="concise"
)

# Property filters
obsidian_vault_query(
    query="",
    mode="properties",
    property_filters={"status": "active", "priority": {"$gte": 5}}
)

# Tag search
obsidian_vault_query(
    query="",
    mode="tags",
    tag_filters=["project", "2025"]
)
```

### 3. obsidian_vault_organize - Batch Operations

Move, tag, archive, or delete multiple notes in a single operation.

```python
# Batch tag notes
obsidian_vault_organize(
    notes="note1.md, note2.md, note3.md",
    operation="tag",
    tags_to_add="reviewed, archived"
)

# Archive with auto-generated timestamp path
obsidian_vault_organize(
    notes="old-1.md, old-2.md",
    operation="archive"  # → archive/2025-10-18/
)

# Move to destination
obsidian_vault_organize(
    notes="draft1.md, draft2.md",
    operation="move",
    destination="projects/2025"
)
```

### 4. obsidian_graph_analyze - Knowledge Graph

Traverse wikilinks and backlinks with depth-based exploration.

```python
# Find immediate neighbors
obsidian_graph_analyze(
    center_note="research/ai-safety.md",
    depth=1,
    include_content_preview=True
)

# Explore extended network
obsidian_graph_analyze(
    center_note="projects/main.md",
    depth=2,
    filter_tags=["important"]
)
```

## Token Efficiency

All tools support `response_format` for cost optimization:

| Format       | Tokens | Best For                                |
| ------------ | ------ | --------------------------------------- |
| **minimal**  | ~50    | Metadata checks, existence verification |
| **concise**  | ~150   | Default, balanced info and efficiency   |
| **detailed** | ~1500+ | Full content analysis                   |

**Impact**: Reading 10 notes with `minimal` uses **500 tokens** vs **15,000+ tokens** with `detailed` (30x difference)

## Development

### Project Structure

```
src/
├── agent/          # Pydantic AI agent + tool registration
├── openai/         # OpenAI-compatible API endpoints
├── tools/          # Vertical slice architecture
│   ├── obsidian_note_manager/
│   ├── obsidian_vault_query/
│   ├── obsidian_vault_organizer/
│   └── obsidian_graph_analyzer/
└── shared/         # Config, logging, parsers

tests/
├── tools/          # Unit tests (mirror src/)
├── integration/    # Multi-tool workflows
└── evaluations/    # 30+ realistic scenarios
```

### Testing

```bash
# All tests
uv run pytest tests/ -v

# By type
uv run pytest tests/ -m unit
uv run pytest tests/ -m integration

# Specific tool
uv run pytest tests/tools/obsidian_note_manager/
```

### Linting

```bash
uv run ruff check src/          # Lint
uv run ruff check --fix src/    # Auto-fix
uv run mypy src/                # Type check
```

## Tool Design

```python
@agent.tool
async def tool_name(...) -> str:
    """Brief description.

    Use this when you need to:
    - Specific use case 1
    - Specific use case 2

    Do NOT use this for:
    - Use other_tool instead for X
    - Use another_tool for Y

    Performance Notes:
        - Minimal format: ~50 tokens
        - Concise format: ~150 tokens
        - Detailed format: ~1500+ tokens

    Examples:
        # Concrete example with realistic data
        tool_name(path="projects/alpha.md", ...)
    """
```

See `CLAUDE.md` for comprehensive guidelines.

## Logging

Structured logs optimized for AI debugging:

```python
logger.info("vault_query_completed",
    mode="tags",
    total_found=15,
    returned=10,
    duration_ms=45.2,
    correlation_id="abc-123"
)
```

Trace requests:

```bash
grep "correlation_id=abc-123" logs/*.json
```

## Principles

From `CLAUDE.md`:

1. **TYPE SAFETY IS NON-NEGOTIABLE** - Strict mypy, all functions typed
2. **KISS** - Simple solutions over abstractions
3. **YAGNI** - Build when needed
4. **Agent-Optimized Tool Docs** - Guide LLM tool selection
5. **Comprehensive Testing** - Every module has tests

## Resources

- [Pydantic AI Documentation](https://ai.pydantic.dev/)
- [Project Guidelines](./CLAUDE.md)

## License

MIT
