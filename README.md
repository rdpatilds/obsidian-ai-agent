# Paddy - Obsidian AI Agent

AI agent for Obsidian using natural language to query, read, and manage your vault. Built with Pydantic AI + FastAPI, providing an OpenAI-compatible API for Obsidian Copilot.

**Self-hosted • Provider-agnostic • Type-safe • Production-ready**

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/yourusername/obsidian-ai-agent
cd obsidian-ai-agent
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env - set your vault path, LLM provider, and API keys

# 3. Start services (optional: database for conversation history)
docker-compose up -d

# 4. Run database migrations (if using database)
uv run alembic upgrade head

# 5. Start the agent
uv run uvicorn app.main:app --reload --port 8123
```

## Obsidian Setup

1. Install **Obsidian Copilot** plugin
2. Configure custom endpoint: `http://localhost:8123/v1/chat/completions`
3. Set API key (from your `.env` file)
4. Start chatting with your vault!

Visit `http://localhost:8123/docs` for API documentation.

## What's Inside

**AI Agent**

- Pydantic AI agent with tool orchestration
- OpenAI-compatible API (`/v1/chat/completions`)
- Provider-agnostic (Anthropic, OpenAI, Google, local models)
- 3 consolidated tools following Anthropic best practices
- Vault access via Docker volume mounting

**Core Infrastructure**

- FastAPI with async/await
- PostgreSQL (optional, for conversation history)
- SQLAlchemy + Alembic migrations
- Pydantic Settings with .env support
- Vertical Slice Architecture

**Developer Experience**

- Strict type checking (MyPy + Pyright)
- Ruff linting & formatting
- Structured logging optimized for AI debugging
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
# LLM Provider (choose one)
LLM_PROVIDER=anthropic        # anthropic | openai | google | ollama
LLM_MODEL=claude-sonnet-4-0   # Provider-specific model
LLM_API_KEY=sk-ant-...        # Your provider API key

# Vault Access
OBSIDIAN_VAULT_PATH=/absolute/path/to/your/vault

# API Authentication
API_KEY=your-secret-key       # For Obsidian Copilot

# CORS (for Obsidian)
ALLOWED_ORIGINS=app://obsidian.md,capacitor://localhost
```

**Optional: PostgreSQL (for conversation history)**

```bash
# Docker (default)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/paddy

# Cloud Providers: Supabase, Neon, Railway also supported
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

## Slash Commands

Built-in Claude Code commands for development:

- `/prime` - Prime agent with codebase understanding
- `/commit` - Create atomic commits with proper messages
- `/validate` - Run full validation suite (tests, types, linting, docker)

## Features

**Agent**
- 3 consolidated tools (query, context, management)
- OpenAI-compatible API endpoint
- Provider-agnostic LLM support
- Docker volume mounting for vault access
- Natural language vault interactions

**Engineering**
- Type safety: Strict MyPy + Pyright, zero suppressions
- Logging: JSON structured, AI-optimized debugging
- CORS: Configured for Obsidian app protocol
- Health checks: `/health`, `/health/db`, `/health/ready`
- Docker: Containerized deployment
- Testing: Integration + unit tests with pytest

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

## Tech Stack

**AI Agent**

- Pydantic AI 0.0.14+ (agent framework)
- Anthropic Claude / OpenAI / Google Gemini / Local models
- OpenAI-compatible API format

**Backend**

- Python 3.12+
- FastAPI 0.120+
- Pydantic 2.0+ (validation & settings)
- SQLAlchemy 2.0+ (async, optional)

**Database (Optional)**

- PostgreSQL 18+ (for conversation history)
- Alembic migrations
- asyncpg driver

**Dev Tools**

- uv (package manager)
- Ruff (linting/formatting)
- MyPy + Pyright (strict type checking)
- pytest (testing)
- Docker + Docker Compose

**Integration**

- Obsidian Copilot plugin (frontend)
- Docker volume mounting (vault access)

## Requirements

- **Python 3.12+**
- **uv** package manager (or pip)
- **LLM API Key** (Anthropic, OpenAI, Google, or local model)
- **Obsidian** with Copilot plugin
- **Docker** (optional, for database and containerized deployment)

## Documentation

- [PRD.md](.agents/PRD.md) - Product requirements and specifications
- [CLAUDE.md](CLAUDE.md) - Development guidelines for Claude Code
- [API Docs](http://localhost:8123/docs) - Interactive API documentation (when running)
