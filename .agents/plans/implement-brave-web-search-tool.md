# Feature: Brave Web Search Tool for Obsidian Agent

Validate documentation and codebase patterns before implementing. Pay special attention to naming of existing utils, types, and models. Import from the right files.

## Feature Description

Add web search capability to the Obsidian AI agent using the Brave Search API, enabling users to search the internet for current information, fact-checking, and research while working in their Obsidian vault. This tool complements the existing vault-focused tools by providing access to external knowledge.

## User Story

As an Obsidian vault user
I want to search the web for current information without leaving my AI assistant conversation
So that I can fact-check claims, research topics, and access up-to-date information while working with my notes

## Problem Statement

The Obsidian agent currently has no way to access external information beyond the vault contents. Users need to manually switch to a web browser to research topics, verify facts, or find current information, breaking their workflow and context.

## Solution Statement

Implement a Brave Web Search tool following the existing VSA pattern used by obsidian_query_vault_tool, obsidian_note_manager_tool, and obsidian_get_context_tool. The tool will use the official brave-search-python-client SDK to perform web searches and return formatted results optimized for LLM consumption.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Low-Medium
**Primary Systems Affected**: Agent tools, configuration, tool registry
**Dependencies**: brave-search-python-client (pip package)

---

## CONTEXT REFERENCES

### Relevant Codebase Files - MUST READ BEFORE IMPLEMENTING!

- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool.py` (all) - Pattern for tool registration with @vault_agent.tool decorator
- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_models.py` (all) - Pattern for Pydantic models (args/returns)
- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_service.py` (all) - Pattern for service layer async functions
- `app/features/obsidian_query_vault_tool/tests/test_obsidian_query_vault_tool.py` (all) - Pattern for service layer testing
- `app/core/agents/base.py` (lines 25-116) - Agent instructions that need updating with new tool
- `app/core/agents/tool_registry.py` (all) - Side-effect import pattern (CRITICAL: preserve order)
- `app/core/config.py` (all) - Settings pattern for adding API keys
- `.agents/reference/adding_tools_guide.md` (all) - Agent-optimized docstring requirements (7 elements)
- `.env.example` (all) - Environment variable documentation pattern

### New Files to Create

- `app/features/brave_web_search_tool/__init__.py` - Package initialization
- `app/features/brave_web_search_tool/brave_web_search_tool.py` - Tool registration with @vault_agent.tool
- `app/features/brave_web_search_tool/brave_web_search_tool_models.py` - Pydantic models for SearchQuery and SearchResult
- `app/features/brave_web_search_tool/brave_web_search_tool_service.py` - Business logic with Brave API integration
- `app/features/brave_web_search_tool/tests/__init__.py` - Test package initialization
- `app/features/brave_web_search_tool/tests/conftest.py` - Test fixtures (if needed)
- `app/features/brave_web_search_tool/tests/test_brave_web_search_tool_service.py` - Unit tests

### Relevant Documentation - READ BEFORE IMPLEMENTING!

- [Brave Search API Documentation](https://api-dashboard.search.brave.com/app/documentation/web-search/query)
  - Specific section: Query parameters (q, count, offset, safesearch)
  - Why: Required for understanding API request structure
- [Brave Search Python Client](https://brave-search-python-client.readthedocs.io/)
  - Specific section: WebSearchRequest and async usage
  - Why: Official SDK usage patterns and async integration
- [Adding Tools Guide](.agents/reference/adding_tools_guide.md)
  - Specific section: Required Elements (7-element structure)
  - Why: Agent-optimized docstring requirements for tool selection

### Patterns to Follow

**Tool Registration Pattern:**
```python
# From app/features/obsidian_query_vault_tool/obsidian_query_vault_tool.py
from pydantic_ai import RunContext
from app.core.agents import AgentDeps, vault_agent

@vault_agent.tool
async def tool_name(
    ctx: RunContext[AgentDeps],
    param1: str,
    param2: int = 10
) -> ResultModel:
    """Agent-optimized docstring with 7 required elements."""
    vault_manager = ctx.deps.vault_manager
    settings = ctx.deps.settings
    # Delegate to service layer
    return await service.execute_function(vault_manager, settings, param1, param2)
```

**Model Definition Pattern:**
```python
# From app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_models.py
from pydantic import BaseModel, Field

class SearchResult(BaseModel):
    """Search result item."""
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str | None = Field(default=None, description="Text excerpt")

class ToolResult(BaseModel):
    """Result returned by tool."""
    results: list[SearchResult] = Field(..., description="List of results")
    total: int = Field(..., description="Total results found")
    query: str = Field(..., description="Original query")
```

**Service Layer Pattern:**
```python
# From app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_service.py
from app.core.logging import get_logger

logger = get_logger(__name__)

async def execute_search(
    settings: Settings,
    query: str,
    count: int
) -> ToolResult:
    """Pure async business logic - no RunContext dependency."""
    logger.info("brave.search_started", query=query, count=count)
    try:
        # Implementation here
        logger.info("brave.search_completed", result_count=len(results))
        return ToolResult(...)
    except Exception as e:
        logger.error("brave.search_failed", error=str(e), exc_info=True)
        raise
```

**Logging Pattern:**
```python
# Format: domain.operation.phase
logger.info("brave.search_started", query=query, count=count)
logger.info("brave.search_completed", result_count=5, total_found=100)
logger.error("brave.search_failed", error=str(e), error_type=type(e).__name__, exc_info=True)
```

**Testing Pattern:**
```python
# From app/features/obsidian_query_vault_tool/tests/test_obsidian_query_vault_tool.py
@pytest.mark.asyncio
async def test_search_basic(test_settings: Settings) -> None:
    """Test basic search functionality."""
    result = await execute_search(
        settings=test_settings,
        query="Python programming",
        count=5
    )
    assert result.total > 0
    assert len(result.results) <= 5
```

**Error Handling Pattern:**
```python
# Raise ValueError for invalid inputs (caught by agent)
if not query or len(query.strip()) == 0:
    raise ValueError("query cannot be empty")

# Let API exceptions propagate with context
try:
    response = await client.search(query)
except BraveSearchAPIError as e:
    logger.error("brave.api_error", error=str(e), exc_info=True)
    raise
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation (Dependencies & Configuration)

Install Brave Search Python client and configure API key access.

**Tasks:**
- Install brave-search-python-client package
- Add BRAVE_API_KEY to Settings class
- Update .env.example with Brave API key documentation

### Phase 2: Core Implementation (Models & Service)

Create Pydantic models and implement business logic with Brave API integration.

**Tasks:**
- Define SearchResult and BraveWebSearchToolResult models
- Implement execute_web_search service function
- Add structured logging for search operations
- Implement error handling for API failures

### Phase 3: Tool Registration

Register tool with agent using @vault_agent.tool decorator and agent-optimized docstring.

**Tasks:**
- Create brave_web_search_tool with RunContext wrapper
- Write 7-element agent-optimized docstring
- Import in tool_registry.py (preserve order)
- Update vault_agent instructions in base.py

### Phase 4: Testing & Validation

Implement tests and validate against all project standards.

**Tasks:**
- Write unit tests for service layer
- Run type checking (mypy + pyright)
- Run linting (ruff)
- Manual validation with real API calls

---

## STEP-BY-STEP TASKS

### CREATE app/features/brave_web_search_tool/__init__.py

- **IMPLEMENT**: Empty package initialization file
- **PATTERN**: Mirror `app/features/obsidian_query_vault_tool/__init__.py`
- **VALIDATE**: File exists and is empty

### CREATE app/features/brave_web_search_tool/brave_web_search_tool_models.py

- **IMPLEMENT**: Pydantic models for search args and results
- **PATTERN**: Follow `obsidian_query_vault_tool_models.py` (lines 1-41)
- **IMPORTS**: `from pydantic import BaseModel, Field`
- **MODELS**:
  - `SearchResult(BaseModel)` - Individual search result with title, url, snippet, page_age
  - `BraveWebSearchToolResult(BaseModel)` - Tool return with results list, query, total_found
- **GOTCHA**: Use `Field(..., description="")` for all fields (helps LLM understand response structure)
- **VALIDATE**: `uv run mypy app/features/brave_web_search_tool/`

### CREATE app/features/brave_web_search_tool/brave_web_search_tool_service.py

- **IMPLEMENT**: Business logic for Brave Search API integration
- **PATTERN**: Follow `obsidian_query_vault_tool_service.py` structure
- **IMPORTS**:
  ```python
  from brave_search_client import BraveSearchClient, WebSearchRequest
  from app.core.config import Settings
  from app.core.logging import get_logger
  from app.features.brave_web_search_tool.brave_web_search_tool_models import (
      SearchResult, BraveWebSearchToolResult
  )
  ```
- **FUNCTION**: `async def execute_web_search(settings: Settings, query: str, count: int, safesearch: str) -> BraveWebSearchToolResult`
- **LOGIC**:
  1. Initialize BraveSearchClient with settings.brave_api_key
  2. Create WebSearchRequest(q=query, count=count, safesearch=safesearch)
  3. Execute await client.search(request)
  4. Parse response.web.results to SearchResult objects
  5. Return BraveWebSearchToolResult
- **LOGGING**: Use "brave.search_started", "brave.search_completed", "brave.search_failed"
- **ERROR HANDLING**: Catch BraveSearchAPIError, log with exc_info=True, re-raise
- **GOTCHA**: Brave API returns nested structure - access via response.web.results
- **VALIDATE**: `uv run mypy app/features/brave_web_search_tool/`

### CREATE app/features/brave_web_search_tool/brave_web_search_tool.py

- **IMPLEMENT**: Tool registration with @vault_agent.tool decorator
- **PATTERN**: Follow `obsidian_query_vault_tool.py` (lines 1-195) exactly
- **IMPORTS**:
  ```python
  from typing import Literal
  from pydantic_ai import RunContext
  from app.core.agents import AgentDeps, vault_agent
  from app.core.logging import get_logger
  from app.features.brave_web_search_tool import brave_web_search_tool_service as service
  from app.features.brave_web_search_tool.brave_web_search_tool_models import BraveWebSearchToolResult
  ```
- **SIGNATURE**:
  ```python
  @vault_agent.tool
  async def brave_web_search_tool(
      ctx: RunContext[AgentDeps],
      query: str,
      count: int = 10,
      safesearch: Literal["off", "moderate", "strict"] = "moderate"
  ) -> BraveWebSearchToolResult:
  ```
- **DOCSTRING**: CRITICAL - Must include all 7 required elements from adding_tools_guide.md:
  1. One-line summary: "Search the web using Brave Search API for current information and research."
  2. Use this when:
     - Finding current events or recent information not in vault
     - Fact-checking claims against web sources
     - Researching topics requiring up-to-date information
     - Gathering external references for note creation
  3. Do NOT use this for:
     - Searching vault notes (use obsidian_query_vault_tool instead)
     - Reading existing notes (use obsidian_get_context_tool instead)
     - Finding local files or folders (use obsidian_query_vault_tool with list_structure)
  4. Args with guidance:
     - query: Natural language search query (max 400 chars). Examples: "latest Python 3.12 features", "climate change research 2025"
     - count: Results to return (1-20, default 10). Use 5 for quick lookups, 10-20 for comprehensive research
     - safesearch: Filter explicit content. "moderate" (default) for general use, "strict" for sensitive topics, "off" for research
  5. Returns: BraveWebSearchToolResult with results list, query, total_found
  6. Performance Notes:
     - API call latency: 200-500ms typical
     - Token cost: ~100-200 tokens per result (title + snippet)
     - Rate limits: Free tier 1 req/sec, monitor X-RateLimit-Remaining header
     - Cost: Free tier 2K/month, see https://brave.com/search/api/ for pricing
  7. Examples: (3-4 realistic examples with comments)
- **IMPLEMENTATION**: Extract settings, call service.execute_web_search, wrap with logging
- **LOGGING**: "agent.tool.execution_started", "agent.tool.execution_completed", "agent.tool.execution_failed"
- **VALIDATE**: `uv run mypy app/features/brave_web_search_tool/`

### UPDATE app/core/config.py

- **IMPLEMENT**: Add brave_api_key field to Settings class
- **PATTERN**: Follow anthropic_api_key pattern (line 54)
- **ADD**: `brave_api_key: str` after llm_model field
- **GOTCHA**: Field is required by default - no default value needed
- **VALIDATE**: `uv run mypy app/core/`

### UPDATE .env.example

- **IMPLEMENT**: Add Brave API key section
- **PATTERN**: Follow LLM Configuration section pattern (lines 1-9)
- **ADD**: After OBSIDIAN_VAULT_PATH section:
  ```
  # =============================================================================
  # Brave Search API Configuration
  # =============================================================================

  # Brave API Key - Get from: https://api-dashboard.search.brave.com/app/keys
  # Free tier: 2,000 searches/month, 1 req/sec
  # Paid tiers: https://brave.com/search/api/
  BRAVE_API_KEY=your-brave-api-key-here
  ```
- **VALIDATE**: File syntax check (no tools, manual review)

### UPDATE app/core/agents/tool_registry.py

- **IMPLEMENT**: Add import for brave_web_search_tool
- **PATTERN**: CRITICAL - Preserve import order (side-effect imports)
- **ADD**: After line 20 (obsidian_get_context_tool import):
  ```python
  import app.features.brave_web_search_tool.brave_web_search_tool
  ```
- **GOTCHA**: Import order matters for circular dependency prevention
- **VALIDATE**: `uv run python -c "from app.main import app; print('OK')"`

### UPDATE app/core/agents/base.py

- **IMPLEMENT**: Add Brave search tool to agent instructions
- **PATTERN**: Follow existing tool documentation format (lines 32-55)
- **ADD**: After "### 3. obsidian_get_context_tool" section, before "## Tool Selection":
  ```python
  ### 4. brave_web_search_tool (WEB SEARCH)
  Search the web for current information and external research.
  - Use for: Finding recent events, fact-checking, researching topics, gathering external references
  - Parameters: query, count (1-20), safesearch (off/moderate/strict)
  - Rate limits: Free tier 1 req/sec, 2K/month
  - Token cost: ~100-200 tokens per result
  ```
- **UPDATE**: "## Tool Selection" section to include web search:
  - Add: **Search Web** → Use `brave_web_search_tool` (external information)
- **UPDATE**: Workflow Patterns section with new "Research Pattern":
  ```python
  ### Research Pattern
  1. Search web for current information via brave_web_search_tool
  2. Create or update vault notes with findings via note_manager_tool
  Example: "Research latest AI developments and create a summary note"
    - First: brave_web_search_tool with query "latest AI developments 2025"
    - Then: note_manager_tool with create_note to save findings
  ```
- **VALIDATE**: Read file to confirm formatting is correct

### CREATE app/features/brave_web_search_tool/tests/__init__.py

- **IMPLEMENT**: Empty test package initialization
- **PATTERN**: Mirror `app/features/obsidian_query_vault_tool/tests/__init__.py`
- **VALIDATE**: File exists and is empty

### CREATE app/features/brave_web_search_tool/tests/test_brave_web_search_tool_service.py

- **IMPLEMENT**: Unit tests for service layer
- **PATTERN**: Follow `test_obsidian_query_vault_tool.py` structure
- **IMPORTS**:
  ```python
  import pytest
  from unittest.mock import AsyncMock, MagicMock
  from app.core.config import Settings
  from app.features.brave_web_search_tool.brave_web_search_tool_service import execute_web_search
  ```
- **TESTS**:
  1. `test_web_search_basic` - Mock API response, verify result parsing
  2. `test_web_search_with_count` - Test count parameter handling
  3. `test_web_search_safesearch_modes` - Test safesearch parameter
  4. `test_web_search_empty_query` - Verify ValueError raised
  5. `test_web_search_api_error` - Mock API error, verify exception handling
- **MOCKING**: Mock BraveSearchClient to avoid real API calls in tests
- **GOTCHA**: Use AsyncMock for async client methods
- **VALIDATE**: `uv run pytest -v app/features/brave_web_search_tool/tests/`

### VALIDATE Level 1: Install Dependencies

- **COMMAND**: `uv add brave-search-python-client`
- **EXPECTED**: Package installed successfully, pyproject.toml updated
- **GOTCHA**: Ensure uv.lock is updated (automatic)

### VALIDATE Level 2: Type Checking

- **COMMAND**: `uv run mypy app/`
- **EXPECTED**: Success: no issues found
- **GOTCHA**: All functions must have type hints including return types
- **COMMAND**: `uv run pyright app/`
- **EXPECTED**: 0 errors, 0 warnings

### VALIDATE Level 3: Linting & Formatting

- **COMMAND**: `uv run ruff check .`
- **EXPECTED**: All checks passed
- **COMMAND**: `uv run ruff format .`
- **EXPECTED**: Files formatted (if needed)

### VALIDATE Level 4: Unit Tests

- **COMMAND**: `uv run pytest -v app/features/brave_web_search_tool/tests/`
- **EXPECTED**: All tests pass
- **COMMAND**: `uv run pytest -v`
- **EXPECTED**: All project tests pass (no regressions)

### VALIDATE Level 5: Manual Testing

- **SETUP**: Add BRAVE_API_KEY to .env file (get from https://api-dashboard.search.brave.com/app/keys)
- **COMMAND**: `uv run uvicorn app.main:app --reload --port 8123`
- **TEST**: Use Obsidian Copilot to send query: "Search the web for Python 3.12 new features"
- **EXPECTED**: Agent uses brave_web_search_tool, returns formatted results
- **VERIFY**: Check logs for "brave.search_started" and "brave.search_completed" events
- **GOTCHA**: Free tier has 1 req/sec rate limit - wait between tests

---

## TESTING STRATEGY

### Unit Tests (Service Layer)

**Scope**: Test business logic in isolation using mocks
**Framework**: pytest with pytest-asyncio
**Coverage Target**: 80%+ for service layer

**Test Cases**:
1. Basic search - mock successful API response, verify parsing
2. Parameter validation - empty query raises ValueError
3. Count parameter - verify request includes correct count
4. Safesearch modes - test all three options
5. API errors - mock BraveSearchAPIError, verify handling
6. Empty results - mock zero results, verify result structure

**Mocking Strategy**:
```python
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_web_search_basic(mock_settings):
    # Mock BraveSearchClient
    mock_client = MagicMock()
    mock_client.search = AsyncMock(return_value=mock_response)

    result = await execute_web_search(
        settings=mock_settings,
        query="test query",
        count=5
    )

    assert result.total_found > 0
```

### Integration Tests

**Scope**: Optional - requires real Brave API key
**Note**: Skip in CI/CD, run manually during development
**Marker**: `@pytest.mark.integration` (can be deselected)

### Edge Cases

**Test Coverage**:
- Empty query string → ValueError
- Query exceeding 400 chars → Truncate or error
- Count outside 1-20 range → Clamp to valid range
- API rate limit exceeded → Propagate error with context
- Network timeout → Propagate with exc_info=True
- Invalid API key → Propagate authentication error

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check .          # Linting (must pass)
uv run ruff format .         # Auto-format code
uv run mypy app/             # Type checking strict mode (must pass)
uv run pyright app/          # Microsoft type checker (must pass)
```

### Level 2: Unit Tests

```bash
uv run pytest -v app/features/brave_web_search_tool/tests/  # Feature tests
uv run pytest -v                                             # All tests (no regressions)
uv run pytest --cov=app/features/brave_web_search_tool       # Coverage check (80%+)
```

### Level 3: Integration Tests

```bash
# Verify tool registry imports correctly
uv run python -c "from app.main import app; print('OK')"

# Start server
uv run uvicorn app.main:app --reload --port 8123

# Test via Obsidian Copilot or curl
curl -X POST http://localhost:8123/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"paddy","messages":[{"role":"user","content":"Search the web for Python 3.12 features"}]}'
```

### Level 4: Manual Validation

**Prerequisites**:
- Brave API key in .env (get from https://api-dashboard.search.brave.com/app/keys)
- Obsidian Copilot configured to http://localhost:8123/v1/chat/completions

**Test Scenarios**:
1. **Basic search**: "Search the web for recent AI developments"
   - Verify: Returns results with titles, URLs, snippets
   - Verify: Logs show brave.search_started and brave.search_completed
2. **Research workflow**: "Search for Python async best practices and create a note"
   - Verify: Uses brave_web_search_tool then obsidian_note_manager_tool
3. **Tool selection**: "Find my notes about Python" (should use vault search, not web search)
   - Verify: Agent uses obsidian_query_vault_tool, NOT brave_web_search_tool
4. **Error handling**: Set invalid API key, trigger search
   - Verify: Error logged with exc_info=True, user gets clear error message

---

## ACCEPTANCE CRITERIA

- [x] Feature implements web search via Brave Search API
- [x] All validation commands pass with zero errors
- [x] Unit test coverage meets 80%+ for service layer
- [x] Type checking (mypy + pyright) passes in strict mode
- [x] Code follows project conventions (VSA, structured logging, error handling)
- [x] No regressions in existing functionality (full test suite passes)
- [x] Agent instructions updated to include new tool
- [x] Tool registry preserves import order
- [x] Configuration includes BRAVE_API_KEY
- [x] README updated with Brave search capability (keep concise)
- [x] Agent-optimized docstring includes all 7 required elements
- [x] Performance characteristics documented (latency, token costs, rate limits)
- [x] Tool selection guidance prevents confusion with vault search tools

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit tests)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability
- [ ] Tool registry import verified with python -c check
- [ ] Agent correctly selects tool for web vs vault queries

---

## NOTES

### Design Decisions

**Why Brave Search over alternatives?**
- Privacy-focused (no tracking)
- Generous free tier (2,000/month)
- Official Python SDK available
- Clean, well-structured API responses

**Why service layer pattern?**
- Testable without Pydantic AI RunContext complexity
- Pure async functions with clear dependencies
- Mirrors existing tool architecture for consistency

**Token efficiency considerations:**
- Default count=10 balances comprehensiveness with token usage
- Each result ~100-200 tokens (title + snippet)
- Total response typically 1,000-2,000 tokens
- Agent can request fewer results (count=3-5) for quick lookups

### Rate Limiting Strategy

Free tier: 1 request/second
- No built-in rate limiting in service layer (rely on agent's retry logic)
- Monitor X-RateLimit-Remaining header in logs
- Document rate limits clearly in tool docstring for agent awareness

### Security Considerations

- API key stored in environment variables (never hardcoded)
- safesearch parameter defaults to "moderate" (content filtering)
- Query length validated (Brave max 400 chars)
- No sensitive data logging (queries are logged for debugging, not full responses)

### Performance Optimization

- Use async client for non-blocking API calls
- Brave API typically responds in 200-500ms
- No caching layer needed initially (each query likely unique)
- Consider caching if duplicate queries become common (future enhancement)

### Future Enhancements

- Add image search capability (Brave supports images, news, videos)
- Implement query suggestions (Brave /suggest/search endpoint)
- Add response caching for duplicate queries
- Support advanced search operators (site:, intitle:, etc.)
- Add location-based search (country parameter)
