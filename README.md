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
OBSIDIAN_VAULT_PATH=/home/user/projects/obsidian-ai-agent/obsdir
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

## Troubleshooting

### Common Setup Issues

**Python/UV Installation**
```bash
# Error: 'uv' command not found
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env  # Add to PATH

# Error: Python version incompatible
uv python install 3.12  # Install Python 3.12+
uv sync --python 3.12   # Use specific version
```

**Environment Configuration**
```bash
# Error: Missing required environment variables
cp .env.example .env
# Edit .env and set:
# - OBSIDIAN_VAULT_PATH (absolute path to your vault)
# - LLM_API_KEY (your provider API key)
# - LLM_MODEL (e.g., claude-sonnet-4-5)

# Error: Vault path not found
ls -la /path/to/your/vault  # Verify path exists
# Ensure path is absolute, not relative
```

**Database Issues**
```bash
# Error: PostgreSQL connection failed
docker-compose up -d postgres  # Start just PostgreSQL
docker-compose logs postgres   # Check for errors

# Error: Database doesn't exist
docker-compose exec postgres createdb -U postgres obsidian_db

# Error: Migration failed
uv run alembic stamp head     # Reset migration state
uv run alembic upgrade head   # Retry migration
```

### Common Runtime Issues

**Server Startup**
```bash
# Error: Port 8123 already in use
lsof -ti:8123 | xargs kill -9  # Kill existing process
# Or use different port:
uv run uvicorn app.main:app --reload --port 8124

# Error: Import errors
uv sync                        # Reinstall dependencies
uv run python -c "from app.main import app"  # Test imports
```

**Obsidian Integration**
```bash
# Error: Copilot can't connect to agent
# 1. Verify server is running: curl http://localhost:8123/health
# 2. Check Copilot settings:
#    - Custom endpoint: http://localhost:8123/v1/chat/completions
#    - API key: any-value (for local development)
# 3. Check CORS settings in .env:
#    ALLOWED_ORIGINS=app://obsidian.md,capacitor://localhost

# Error: Agent can't read vault
# 1. Check vault path permissions:
chmod -R 755 /path/to/vault
# 2. Verify OBSIDIAN_VAULT_PATH in .env is correct
# 3. Test vault access:
uv run python -c "from pathlib import Path; print(list(Path('${OBSIDIAN_VAULT_PATH}').glob('*.md')))"
```

**Performance Issues**
```bash
# Slow responses
# 1. Check LLM provider status
# 2. Reduce vault size for testing
# 3. Enable debug logging:
export LOG_LEVEL=DEBUG
uv run uvicorn app.main:app --reload --port 8123

# Memory issues
# 1. Limit concurrent requests
# 2. Restart server periodically
# 3. Monitor with: docker stats (if using Docker)
```

### Development Issues

**Type Checking**
```bash
# MyPy errors
uv run mypy app/ --no-error-summary  # See specific errors
uv run mypy app/ --install-types     # Install missing type stubs

# Pyright errors
uv run pyright app/ --verbose        # Detailed error info
```

**Testing Problems**
```bash
# Tests failing
uv run pytest -v --tb=short         # See failure details
uv run pytest -x                    # Stop on first failure

# Integration tests failing
docker-compose up -d postgres        # Ensure test DB is running
uv run pytest -v -m integration --tb=line
```

**Docker Issues**
```bash
# Container won't start
docker-compose logs app              # Check application logs
docker-compose logs postgres         # Check database logs

# Permission denied (vault mount)
# Linux: Fix permissions
sudo chown -R $USER:$USER /path/to/vault
# Docker Desktop: Enable file sharing for vault path

# Port conflicts
docker-compose down                  # Stop all containers
docker system prune -f              # Clean up
```

### Getting Help

1. **Check logs**: Server logs contain request IDs for debugging
2. **Health endpoints**: Visit `/health` and `/health/db` for system status
3. **API docs**: Visit `/docs` for interactive API testing
4. **GitHub Issues**: Report bugs with logs and environment details

## Documentation

- [PRD.md](.agents/PRD.md) - Product requirements and specifications
- [CLAUDE.md](CLAUDE.md) - Development guidelines for the coding assistant
- [API Docs](http://localhost:8123/docs) - Interactive API documentation (when running)
