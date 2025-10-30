# Web Search Tool Implementation Plan

## Overview

Add a web search capability to the Obsidian AI agent using Brave Search API (simple, no-auth free tier available).

**Key Requirements**:
- Search the web for information
- Return formatted results (title, snippet, URL)
- Token-efficient response formats (minimal/concise/detailed)
- Follow existing vertical slice architecture pattern

**Success Criteria**:
- Tool registered with agent and callable
- Returns relevant search results
- All tests pass (unit + integration)
- Strict mypy type checking passes
- Ruff linting passes

## Relevant Files

### New Files to Create

1. `src/tools/web_search/schemas.py` - Pydantic models for request/response
2. `src/tools/web_search/service.py` - Core search logic using httpx
3. `src/tools/web_search/tool.py` - Tool registration with agent
4. `tests/tools/web_search/test_schemas.py` - Schema unit tests
5. `tests/tools/web_search/test_service.py` - Service unit tests
6. `tests/tools/web_search/test_tool.py` - Tool integration tests

### Files to Modify

1. `src/agent/agent.py` - Add web search tool registration (lines 75-80 area)
2. `src/shared/config.py` - Add ENABLE_WEB_SEARCH config flag
3. `.env.example` - Add ENABLE_WEB_SEARCH=true example

## Dependencies

**New Dependencies**: None (use existing httpx)

**Existing Utilities to Reuse**:
- `src.shared.config.get_settings()` - Configuration access
- `src.shared.logging.get_logger()` - Structured logging
- `httpx.AsyncClient` - HTTP requests (already in dependencies)

**Configuration**:
- Add `ENABLE_WEB_SEARCH` boolean flag to config

## Step by Step Tasks

### Task 1: Create Web Search Schemas

**File**: `src/tools/web_search/schemas.py` (create new)

**Action**: Define Pydantic models for search requests and responses

**Details**:
- Create `WebSearchRequest` model:
  - `query: str` - Search query
  - `max_results: int = 5` - Number of results (1-10)
  - `response_format: str = "concise"` - minimal/concise/detailed
- Create `WebSearchResult` model:
  - `title: str`
  - `url: str`
  - `snippet: str`
- Create `WebSearchResponse` model:
  - `results: list[WebSearchResult]`
  - `total_found: int`
- Add proper type hints, docstrings, and validation

### Task 2: Implement Web Search Service

**File**: `src/tools/web_search/service.py` (create new)

**Action**: Implement search logic using DuckDuckGo HTML scraping (no API key needed)

**Details**:
- Create `async def search_web(request: WebSearchRequest) -> str` function
- Use httpx to query DuckDuckGo HTML (`https://html.duckduckgo.com/html/?q={query}`)
- Parse HTML results (simple regex or basic parsing)
- Format response based on response_format:
  - `minimal`: Title + URL only (~30 tokens per result)
  - `concise`: Title + URL + snippet (50 words) (~100 tokens per result)
  - `detailed`: Title + URL + full snippet (~200 tokens per result)
- Include structured logging (search_started, search_completed, search_failed)
- Add error handling for network issues
- Respect max_results parameter

### Task 3: Register Tool with Agent

**File**: `src/tools/web_search/tool.py` (create new)

**Action**: Create tool registration function following existing pattern

**Details**:
- Import dependencies: `RunContext`, `Agent`, `AgentDependencies`
- Create `register_web_search_tool(agent)` function
- Define `@agent.tool async def web_search(...)` with comprehensive docstring:
  - Include "Use this when" section (searching for current information, facts, news)
  - Include "Do NOT use this for" section (don't use for vault searches)
  - Document all parameters with examples
  - Add Performance Notes section (token costs by format)
  - Provide 2-3 realistic examples
- Call `search_web()` service function
- Add structured logging (tool_execution_started, tool_execution_completed)

**Related Files**: Pattern reference: `src/tools/obsidian_note_manager/tool.py`

### Task 4: Add Configuration Support

**File**: `src/shared/config.py` (modify existing)

**Action**: Add ENABLE_WEB_SEARCH configuration flag

**Details**:
- Add to Settings class around line 60-70 (with other ENABLE_ flags):
  ```python
  enable_web_search: bool = Field(
      default=True,
      description="Enable web search tool"
  )
  ```
- Follow existing pattern from other enable flags

### Task 5: Register Tool in Agent

**File**: `src/agent/agent.py` (modify existing)

**Action**: Add web search tool registration

**Details**:
- Add registration block around line 75-80 (after other tools):
  ```python
  if settings.enable_web_search:
      from src.tools.web_search.tool import register_web_search_tool
      register_web_search_tool(agent)
  ```
- Follow existing pattern from other tool registrations

### Task 6: Update Environment Example

**File**: `.env.example` (modify existing)

**Action**: Add web search configuration

**Details**:
- Add around line 58 (with other ENABLE_ flags):
  ```bash
  ENABLE_WEB_SEARCH=true  # Web search using DuckDuckGo
  ```

### Task 7: Create Schema Unit Tests

**File**: `tests/tools/web_search/test_schemas.py` (create new)

**Action**: Test Pydantic model validation

**Details**:
- Test `WebSearchRequest` validation (valid/invalid inputs)
- Test `WebSearchResult` model creation
- Test `WebSearchResponse` model creation
- Use `@pytest.mark.unit` decorator
- Follow pattern from `tests/tools/obsidian_note_manager/test_schemas.py`

### Task 8: Create Service Unit Tests

**File**: `tests/tools/web_search/test_service.py` (create new)

**Action**: Test search service with mocked HTTP

**Details**:
- Mock httpx responses
- Test successful search
- Test error handling (network errors, parsing errors)
- Test different response_format outputs
- Test max_results limiting
- Use `@pytest.mark.unit` decorator
- Follow pattern from `tests/tools/obsidian_note_manager/test_service.py`

### Task 9: Create Tool Integration Test

**File**: `tests/tools/web_search/test_tool.py` (create new)

**Action**: Test tool registration and execution

**Details**:
- Test tool registration with agent
- Test tool execution end-to-end (with mocked HTTP)
- Test error cases
- Use `@pytest.mark.integration` decorator
- Follow pattern from `tests/tools/obsidian_note_manager/test_tool.py`

## Testing Strategy

**Unit Tests**:
- Schema validation (test_schemas.py)
- Service logic with mocked HTTP (test_service.py)

**Integration Tests**:
- Tool registration and end-to-end execution (test_tool.py)

**Test Approach**:
- Mock HTTP requests (don't make real web requests in tests)
- Test all response formats (minimal/concise/detailed)
- Test error handling paths
- Verify structured logging output

## Validation Commands

Run these commands in order:

```bash
# Linting
uv run ruff check src/ tests/

# Type checking
uv run mypy src/

# Unit tests
uv run pytest tests/tools/web_search/ -m unit -v

# Integration tests
uv run pytest tests/tools/web_search/ -m integration -v

# All tests
uv run pytest tests/ -v
```

## Integration Notes

**How it Connects**:
- Follows existing vertical slice pattern (schemas.py, service.py, tool.py)
- Registered via agent.py using settings flag
- Uses existing httpx dependency (no new deps)
- Uses existing logging and config infrastructure

**No Breaking Changes**: This is a new additive feature

**Documentation**: Update README.md to add web_search to "Core Tools" section (optional, can do later)

## Implementation Notes

**Keep It Simple**:
- Use DuckDuckGo HTML (no API key required)
- Simple HTML parsing (regex or basic string operations)
- Focus on getting clean results quickly
- Don't over-engineer - follow existing patterns exactly
