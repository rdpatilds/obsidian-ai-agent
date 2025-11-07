# Paddy - Obsidian AI Agent

AI agent for Obsidian using natural language to query, read, and manage your vault. Built with Pydantic AI + FastAPI, providing an OpenAI-compatible API for Obsidian Copilot.

> This Obsidian Agent is a work in progress since we are building it together throughout the course!

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/dynamous-community/obsidian-ai-agent
cd obsidian-ai-agent
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env - set your vault path, LLM provider, and API keys

# 3. Start services (optional: database for RAG later in the course)
docker-compose up -d

# 4. Run database migrations (if using database)
uv run alembic upgrade head

# 5. Start the agent
uv run uvicorn app.main:app --reload --port 8123
```

## Obsidian Setup

1. Install **Obsidian Copilot** plugin
2. Configure custom endpoint: `http://localhost:8123/v1/chat/completions`
3. Set API key to any value (since this is just a local app right now)
4. Start chatting with your vault!

Visit `http://localhost:8123/docs` for API documentation.

## What's Inside

**AI Agent**

- Pydantic AI agent with tool orchestration
- OpenAI-compatible API (`/v1/chat/completions`)
- 3 consolidated tools following Anthropic best practices

**Core Infrastructure**

- FastAPI with async/await
- PostgreSQL (optional, for conversation history)
- SQLAlchemy + Alembic migrations
- Pydantic Settings with .env support
- Vertical Slice Architecture

**AI Optimized Codebase**

- Strict type checking (MyPy + Pyright)
- Strict testing standards
- Ruff linting & formatting
- Structured logging
- Health check endpoints
- Docker containerization

**Agent Capabilities**

- Natural language vault queries
- Semantic search across notes
- Context-aware note reading
- Note creation, updating, appending
- Bulk operations (tagging, moving, organizing)
- Folder management

## Project Structure

```
app/
├── core/              # Infrastructure
│   ├── agent.py       # Pydantic AI agent instance
│   ├── config.py      # Settings & environment
│   ├── database.py    # PostgreSQL connection
│   └── logging.py     # Structured logging
├── shared/            # Cross-feature utilities
│   └── vault/         # Vault access layer
│       ├── manager.py # File operations
│       └── models.py  # Domain models
├── features/          # Vertical slices
│   ├── chat/          # OpenAI-compatible chat endpoint
│   ├── vault_query/   # Discovery & search tool
│   ├── vault_context/ # Context-aware reading tool
│   └── vault_management/ # Modification operations tool
└── main.py            # FastAPI application entry
```

See [PRD.md](.agents/PRD.md) for detailed architecture and tool specifications.

## Configuration

**Required Environment Variables:**

```bash
# LLM Provider
LLM_MODEL=claude-sonnet-4-5   # Provider-specific model
LLM_API_KEY=sk-ant-...        # Your provider API key

# Vault Access
OBSIDIAN_VAULT_PATH=/absolute/path/to/your/vault
```

**Optional: PostgreSQL (for conversation history)**

```bash
# Docker (default)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/obsidian_db

# Cloud Providers: Any Postgres instance is supported!
```

## Commands

```bash
# Development
uv run uvicorn app.main:app --reload --port 8123

# Testing
uv run pytest -v                    # All tests
uv run pytest -v -m integration     # Integration tests only

# Type checking
uv run mypy app/
uv run pyright app/

# Linting
uv run ruff check .
uv run ruff format .

# Database
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
uv run alembic downgrade -1

# Docker
docker-compose up -d                # Start services
docker-compose logs -f app          # View logs
docker-compose down                 # Stop services
```

## Architecture Principles

**Vertical Slice Architecture**

- Each feature is self-contained: tools + models + routes
- Agent tools register via `@agent.tool` decorators
- Core infrastructure (agent, config, logging) is shared
- Vault operations abstracted in `shared/vault/`

**Single Agent Pattern**

- One Pydantic AI agent instance in `core/agent.py`
- Tools register via side-effect imports in `main.py`
- OpenAI compatibility layer converts formats
- Follows Anthropic's "fewer, smarter tools" principle

**AI-Optimized Development**

- Structured logging optimized for LLM debugging
- Tool docstrings guide LLM tool selection
- Type hints everywhere for AI code generation
- Fast feedback loops (strict type checking, tests)

## Documentation

- [PRD.md](.agents/PRD.md) - Product requirements and specifications
- [CLAUDE.md](CLAUDE.md) - Development guidelines for the coding assistant
- [API Docs](http://localhost:8123/docs) - Interactive API documentation (when running)
