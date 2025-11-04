# Feature: Implement Base Pydantic AI Agent with FastAPI Test Endpoint

## Feature Description

Create a foundational Pydantic AI agent integrated with Anthropic Claude Haiku 4.5, accessible through a FastAPI test endpoint. Establishes infrastructure for future tool registration following strict VSA architecture, type safety, and logging standards.

## User Story

As a **developer building the Paddy AI agent**
I want to **create a base Pydantic AI agent with proper infrastructure**
So that **I can validate agent functionality and have a foundation for adding tools**

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `app/core/agents/`, `app/agent/`, `app/core/config.py`, root `conftest.py`
**Dependencies**: `pydantic-ai-slim[anthropic]`, `python-dotenv`

---

## CONTEXT REFERENCES

### Must Read Before Implementing

- `app/core/config.py` (lines 1-61) - Pydantic Settings pattern
- `app/core/logging.py` (lines 75-148) - Logging setup and event naming
- `app/core/health.py` - FastAPI route pattern with dependencies
- `app/shared/schemas.py` - Pydantic schema patterns
- `app/tests/conftest.py` - Test fixture patterns
- `docs/logging-standard.md` - Event naming taxonomy (agent.* domain)
- `docs/mypy-standard.md` - Type annotation requirements
- `docs/pytest-standard.md` - Test structure patterns

### New Files to Create

```
app/core/agents/__init__.py          - Package with exports
app/core/agents/base.py              - Agent instance and AgentDeps
app/core/agents/types.py             - Type definitions
app/core/agents/tests/__init__.py    - Test package
app/core/agents/tests/test_agent.py  - Agent unit tests
app/agent/__init__.py                - Test feature package
app/agent/models.py                  - Request/response schemas
app/agent/routes.py                  - Test endpoint
app/agent/tests/__init__.py          - Test package
app/agent/tests/test_routes.py       - Endpoint integration tests
conftest.py (root)                   - Project-wide pytest config
```

### Key Patterns

**Logging** (from docs/logging-standard.md):
```python
logger.info("agent.chat.started", message_length=len(msg))
logger.info("agent.chat.completed", total_tokens=tokens)
logger.error("agent.chat.failed", error=str(e), exc_info=True)
```

**Route** (from app/core/health.py):
```python
router = APIRouter(prefix="/agent", tags=["agent"])

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Docstring with Args, Returns, Raises."""
    pass
```

**Error Handling**:
```python
try:
    result = await operation()
except Exception as exc:
    logger.error("event.failed", exc_info=True)
    raise HTTPException(status_code=500, detail=str(exc)) from exc
```

---

## STEP-BY-STEP TASKS

### Task 1: ADD dependencies

```bash
uv add "pydantic-ai-slim[anthropic]"
uv add python-dotenv
```

**VALIDATE**: `uv run python -c "import pydantic_ai; import anthropic; print('OK')"`

### Task 2: UPDATE app/core/config.py - Add LLM settings

Add after line 42:
```python
# LLM Configuration
anthropic_api_key: str
llm_model: str = "claude-haiku-4-5"
```

Add at top (after imports):
```python
from dotenv import load_dotenv

load_dotenv()
```

**VALIDATE**: `uv run python -c "from app.core.config import get_settings; print(get_settings().llm_model)"`

### Task 3: UPDATE .env.example

Add after ALLOWED_ORIGINS:
```bash
# LLM Configuration
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_MODEL=claude-haiku-4-5
```

### Task 4: CREATE app/core/agents/__init__.py

```python
"""Pydantic AI agent infrastructure."""

from app.core.agents.base import AgentDeps, vault_agent
from app.core.agents.types import AgentResponse, AgentUsage

__all__ = ["vault_agent", "AgentDeps", "AgentResponse", "AgentUsage"]
```

### Task 5: CREATE app/core/agents/types.py

```python
"""Type definitions for agent interactions."""

from pydantic import BaseModel, Field


class AgentUsage(BaseModel):
    """Token usage statistics."""

    request_tokens: int = Field(..., description="Tokens in request")
    response_tokens: int = Field(..., description="Tokens in response")
    total_tokens: int = Field(..., description="Total tokens used")


class AgentResponse(BaseModel):
    """Agent response with output and metadata."""

    output: str = Field(..., description="Agent response text")
    usage: AgentUsage = Field(..., description="Token usage")
```

**VALIDATE**: `uv run mypy app/core/agents/types.py`

### Task 6: CREATE app/core/agents/base.py

```python
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
```

**VALIDATE**: `uv run python -c "from app.core.agents import vault_agent; print(vault_agent.model)"`

### Task 7: CREATE app/agent/__init__.py

```python
"""Test endpoint for agent interaction."""
```

### Task 8: CREATE app/agent/models.py

```python
"""Schemas for agent testing endpoint."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request for agent chat."""

    message: str = Field(..., min_length=1, description="User message")


class ChatResponse(BaseModel):
    """Response from agent chat."""

    response: str = Field(..., description="Agent response")
    usage: dict[str, int] = Field(..., description="Token usage")
```

**VALIDATE**: `uv run mypy app/agent/models.py`

### Task 9: CREATE app/agent/routes.py

```python
"""Test endpoints for agent interaction."""

from fastapi import APIRouter, HTTPException, status

from app.agent.models import ChatRequest, ChatResponse
from app.core.agents import AgentDeps, vault_agent
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Test endpoint for agent interaction.

    Args:
        request: User message to send to agent.

    Returns:
        Agent response with usage statistics.

    Raises:
        HTTPException: 500 if agent execution fails.
    """
    logger.info("agent.chat.started", message_length=len(request.message))

    try:
        result = await vault_agent.run(request.message, deps=AgentDeps())

        logger.info(
            "agent.chat.completed",
            response_length=len(result.output),
            total_tokens=result.usage().total_tokens,
        )

        return ChatResponse(
            response=result.output,
            usage={
                "total_tokens": result.usage().total_tokens,
                "request_tokens": result.usage().request_tokens,
                "response_tokens": result.usage().response_tokens,
            },
        )

    except Exception as e:
        logger.error(
            "agent.chat.failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}",
        ) from e
```

**VALIDATE**: `uv run mypy app/agent/routes.py`

### Task 10: UPDATE app/main.py - Register agent router

Add after health router import (line 24):
```python
from app.agent.routes import router as agent_router
```

Add after health router registration (line 77):
```python
app.include_router(agent_router)
```

**VALIDATE**: `uv run python -c "from app.main import app; print('OK')"`

### Task 11: CREATE conftest.py (root)

```python
"""Project-wide pytest configuration and fixtures."""

from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.main import app


@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """FastAPI test client for endpoint testing."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
async def test_db_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Database engine for each test."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="function")
async def test_db_session(
    test_db_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Database session for each test."""
    async_session = async_sessionmaker(
        test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with async_session() as session:
        yield session
```

**VALIDATE**: `uv run pytest --collect-only`

### Task 12: CREATE app/core/agents/tests/__init__.py

```python
"""Tests for agent infrastructure."""
```

### Task 13: CREATE app/core/agents/tests/test_agent.py

```python
"""Unit tests for Pydantic AI agent."""

from dataclasses import is_dataclass

from app.core.agents import AgentDeps, vault_agent


def test_agent_initialization() -> None:
    """Test agent is properly initialized."""
    assert vault_agent is not None
    assert "anthropic" in str(vault_agent.model).lower()


def test_agent_deps_initialization() -> None:
    """Test AgentDeps instantiation."""
    deps = AgentDeps()
    assert deps is not None


def test_agent_deps_is_dataclass() -> None:
    """Test AgentDeps is dataclass."""
    assert is_dataclass(AgentDeps)
```

**VALIDATE**: `uv run pytest app/core/agents/tests/test_agent.py -v`

### Task 14: CREATE app/agent/tests/__init__.py

```python
"""Tests for agent test endpoint."""
```

### Task 15: CREATE app/agent/tests/test_routes.py

```python
"""Integration tests for agent test endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_chat_endpoint_exists(test_client: TestClient) -> None:
    """Test /agent/chat endpoint registered."""
    openapi = test_client.get("/openapi.json").json()
    assert "/agent/chat" in openapi["paths"]


@patch("app.agent.routes.vault_agent.run")
async def test_chat_success(mock_run: AsyncMock, test_client: TestClient) -> None:
    """Test successful chat interaction."""
    mock_result = MagicMock()
    mock_result.output = "I'm Paddy, an AI assistant."
    mock_usage = MagicMock()
    mock_usage.total_tokens = 45
    mock_usage.request_tokens = 20
    mock_usage.response_tokens = 25
    mock_result.usage.return_value = mock_usage
    mock_run.return_value = mock_result

    response = test_client.post("/agent/chat", json={"message": "Hello"})

    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "usage" in data
    assert data["usage"]["total_tokens"] == 45


def test_chat_validation_error(test_client: TestClient) -> None:
    """Test empty message validation."""
    response = test_client.post("/agent/chat", json={"message": ""})
    assert response.status_code == 422


@patch("app.agent.routes.vault_agent.run")
async def test_chat_agent_error(mock_run: AsyncMock, test_client: TestClient) -> None:
    """Test agent error handling."""
    mock_run.side_effect = Exception("API error")
    response = test_client.post("/agent/chat", json={"message": "Hello"})
    assert response.status_code == 500
    assert "Agent execution failed" in response.json()["detail"]
```

**VALIDATE**: `uv run pytest app/agent/tests/test_routes.py -v`

---

## VALIDATION COMMANDS

### Level 1: Syntax & Style

```bash
uv run ruff check . --fix && uv run ruff format .
```

### Level 2: Type Checking

```bash
uv run mypy app/ && uv run pyright app/
```

Expected: No errors

### Level 3: Tests

```bash
uv run pytest -v
```

Expected: All pass (7 new tests: 3 agent + 4 endpoint)

### Level 4: Manual

**Start server**:
```bash
uv run uvicorn app.main:app --reload --port 8123
```

**Test endpoint** (requires ANTHROPIC_API_KEY in .env):
```bash
curl -X POST http://localhost:8123/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, who are you?"}'
```

Expected: JSON with "response" and "usage" fields

**View docs**: http://localhost:8123/docs

### Level 5: Import Validation

```bash
uv run python -c "from app.core.agents import vault_agent, AgentDeps; print('✓')"
uv run python -c "from app.agent.routes import router; print('✓')"
```

---

## ACCEPTANCE CRITERIA

- [ ] Pydantic AI agent created with Anthropic Claude Haiku 4.5
- [ ] AgentDeps dataclass established for dependency injection
- [ ] Test endpoint POST /agent/chat works correctly
- [ ] All validation commands pass (ruff, mypy, pyright, pytest)
- [ ] 7 tests pass (3 agent unit + 4 endpoint integration)
- [ ] Structured logging follows `agent.chat.*` pattern
- [ ] Code follows VSA architecture (core infrastructure)
- [ ] Google-style docstrings on all functions
- [ ] .env.example updated with LLM config
- [ ] Root conftest.py provides shared fixtures
- [ ] Manual testing with real API confirms functionality

---

## COMPLETION CHECKLIST

- [ ] All 15 tasks completed in order
- [ ] Each task validation passed
- [ ] All validation commands green
- [ ] Test suite passes: `uv run pytest -v`
- [ ] No lint errors: `uv run ruff check .`
- [ ] No type errors: `uv run mypy app/ && uv run pyright app/`
- [ ] Manual test confirms agent responds
- [ ] All acceptance criteria checked

---

## NOTES

**Design Decisions**:
- Agent in `core/agents/` (infrastructure, not feature)
- Claude Haiku 4.5 (newest, fastest, cheapest)
- Empty AgentDeps (pattern established for future)
- Test endpoint temporary (validates before OpenAI endpoint)

**Trade-offs**:
- Mock API in tests (CI speed) vs real API (manual validation)
- Simple instructions (refine later with usage)
- No streaming (add with `agent.run_stream()` later)

**Next Steps**:
1. Add VaultManager to AgentDeps
2. Register first tool with `@vault_agent.tool`
3. Build OpenAI-compatible `/v1/chat/completions`
4. Add conversation history persistence

<!-- EOF -->
