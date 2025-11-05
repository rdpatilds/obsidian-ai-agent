# Feature: Obsidian Query Vault Tool

## Feature Description

Implement the first agent tool enabling natural language vault search and discovery. This establishes all patterns for future tools: VaultManager infrastructure, tool registration, agent-optimized docstrings, and testing patterns.

## User Story

As an Obsidian vault user
I want to search my vault using natural language queries
So that I can quickly find notes by content, tags, dates, or relationships

## Problem Statement

Agent has no vault access capabilities. Need to build: (1) vault file system infrastructure, (2) first tool following Pydantic AI patterns, (3) tool registration and dependency injection, (4) agent-optimized docstrings for LLM guidance.

## Solution Statement

Three-layer VSA architecture:
- **Shared Infrastructure** (`app/shared/vault/`): VaultManager, domain models (3+ feature rule)
- **Feature Slice** (`app/features/obsidian_query_vault_tool/`): Tool with @vault_agent.tool, service layer
- **Tool Registry** (`app/core/agents/tool_registry.py`): Central registration via side-effect imports

## Feature Metadata

**Type**: New Capability | **Complexity**: High (first tool) | **Systems**: Agent infrastructure, shared utilities, feature slices
**Dependencies**: `python-frontmatter>=1.1.0` (add to pyproject.toml)

---

## CONTEXT REFERENCES

### Must Read Files

**Agent Infrastructure:**
- `app/core/agents/base.py` (lines 12-38) - AgentDeps (empty, needs VaultManager), vault_agent instance
- `app/core/config.py` (lines 19-56) - Settings (add obsidian_vault_path)
- `docs/logging-standard.md` (lines 159-207) - Agent logging events: `agent.tool.*`

**Patterns:**
- `app/shared/utils.py` - Utility structure pattern
- `app/core/tests/test_logging.py` (lines 105-122) - JSON log parsing with capsys
- `app/agent/tests/test_routes.py` (lines 14-32) - Agent mocking pattern
- `docs/pytest-standard.md` (lines 100-166) - Async test patterns, fixtures

**Specifications:**
- `.agents/reference/mvp-tool-designs.md` (lines 39-145) - Complete tool spec (params, returns, examples)
- `.agents/reference/adding_tools_guide.md` - 7-element docstring structure (CRITICAL)
- `.agents/reference/vsa-patterns.md` (lines 42-140) - VSA decision rules

### New Files (17 total)

**Shared:** `app/shared/vault/{__init__,vault_manager,vault_models,tests/test_vault_manager,tests/conftest}.py`
**Feature:** `app/features/obsidian_query_vault_tool/{__init__,obsidian_query_vault_tool,obsidian_query_vault_tool_models,obsidian_query_vault_tool_service,tests/test_obsidian_query_vault_tool,tests/conftest}.py`
**Registry:** `app/core/agents/tool_registry.py`

### Files to Modify (6)

- `app/core/agents/base.py` - Add VaultManager to AgentDeps, update system prompt
- `app/core/agents/__init__.py` - Export tool_registry
- `app/core/config.py` - Add obsidian_vault_path setting
- `app/main.py` - Import tool_registry for registration
- `app/agent/routes.py` - Provide VaultManager in AgentDeps
- `pyproject.toml` - Add python-frontmatter dependency

### Key Patterns

**Naming (User Requirement - Verbose):**
`obsidian_query_vault_tool/`, `obsidian_query_vault_tool.py`, `ObsidianQueryVaultToolResult`

**Tool Registration:**
```python
from pydantic_ai import RunContext
from app.core.agents import vault_agent, AgentDeps

@vault_agent.tool
async def obsidian_query_vault_tool(
    ctx: RunContext[AgentDeps],
    query_type: Literal[...],
    ...
) -> ObsidianQueryVaultToolResult:
    """7-element docstring: summary, use when, do NOT use, args WHY, returns, perf notes, examples."""
    vault_manager = ctx.deps.vault_manager
    # Delegate to service
```

**Logging:** `agent.tool.execution_started/completed/failed` with tool/query_type context

**Testing:** Fixtures in conftest.py, temp vaults with tmp_path, async tests, RunContext mocking

---

## STEP-BY-STEP TASKS

### Phase 1: Vault Infrastructure

#### ADD dependency to `pyproject.toml`
- **IMPLEMENT**: `python-frontmatter>=1.1.0` in dependencies (after pydantic-settings)
- **VALIDATE**: `uv sync`

#### CREATE `app/shared/vault/vault_models.py`
- **IMPLEMENT**: `Frontmatter(BaseModel)` (tags, title, created, modified, custom), `Note(BaseModel)` (path, title, content, frontmatter, word_count), `VaultPath(BaseModel)` (vault_root, relative_path, absolute_path with validation)
- **PATTERN**: `app/shared/schemas.py` for Pydantic structure
- **VALIDATE**: `uv run python -c "from app.shared.vault.vault_models import Note; print('OK')"`

#### CREATE `app/shared/vault/vault_manager.py`
- **IMPLEMENT**: `VaultManager(vault_path)` with methods: `read_note()`, `search_content()`, `list_notes()`, `search_by_metadata()`, `get_recent_notes()`
- **IMPORTS**: `pathlib.Path, frontmatter, vault_models, get_logger`
- **PATTERN**: `app/shared/utils.py` for utility structure
- **GOTCHA**: Validate paths stay within vault_root (Path.resolve() + startswith check), handle missing frontmatter gracefully
- **VALIDATE**: `uv run python -c "from pathlib import Path; from app.shared.vault.vault_manager import VaultManager; VaultManager(Path.cwd()); print('OK')"`

#### CREATE `app/shared/vault/tests/conftest.py`
- **IMPLEMENT**: `temp_vault(tmp_path)` fixture creating test vault with 3 notes (with/without frontmatter, subfolder), `vault_manager(temp_vault)` fixture
- **PATTERN**: `app/shared/tests/conftest.py`
- **VALIDATE**: `uv run pytest app/shared/vault/tests/ --collect-only`

#### CREATE `app/shared/vault/tests/test_vault_manager.py`
- **IMPLEMENT**: 8+ tests: initialization, invalid path, read with/without frontmatter, search content, list notes, search by tags, recent notes
- **PATTERN**: `app/shared/tests/test_utils.py` for test structure
- **VALIDATE**: `uv run pytest app/shared/vault/tests/test_vault_manager.py -v`

### Phase 2: Configuration & Dependencies

#### UPDATE `app/core/config.py`
- **IMPLEMENT**: Add `obsidian_vault_path: str` after llm_model (required field)
- **VALIDATE**: `uv run python -c "from app.core.config import get_settings; print(get_settings().obsidian_vault_path)"`

#### UPDATE `.env.example` and `.env`
- **IMPLEMENT**: Add `OBSIDIAN_VAULT_PATH=/path/to/vault` with comment
- **GOTCHA**: Use absolute path, must exist before startup
- **VALIDATE**: Check file syntax

#### UPDATE `app/core/agents/base.py`
- **IMPLEMENT**: Replace `AgentDeps(pass)` with `vault_manager: VaultManager, settings: Settings`
- **UPDATE**: System instructions (lines 25-34) to mention `obsidian_query_vault_tool` available, mention concise/detailed formats, note read/modify tools not yet available
- **IMPORTS**: Add VaultManager, Settings
- **VALIDATE**: `uv run python -c "from app.core.agents import AgentDeps, vault_agent; print('OK')"`

### Phase 3: Tool Implementation

#### CREATE `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_models.py`
- **IMPLEMENT**: `SearchFilters(tags, date_range, folder)`, `NoteInfo(path, title, relevance, excerpt?, tags?, created?, modified?)`, `ObsidianQueryVaultToolResult(results, total_found, truncated, suggestion?)`
- **PATTERN**: `app/core/agents/types.py` for model structure
- **VALIDATE**: `uv run python -c "from app.features.obsidian_query_vault_tool.obsidian_query_vault_tool_models import NoteInfo; print('OK')"`

#### CREATE `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_service.py`
- **IMPLEMENT**: 5 async functions: `execute_semantic_search()`, `execute_list_structure()`, `execute_find_related()`, `execute_search_by_metadata()`, `execute_recent_changes()`, plus helpers `_note_to_info()`, `_generate_suggestion()`
- **PATTERN**: Service delegates to VaultManager, converts to NoteInfo based on response_format
- **GOTCHA**: Service functions async even if VaultManager sync (future-proofing)
- **VALIDATE**: `uv run python -c "from app.features.obsidian_query_vault_tool.obsidian_query_vault_tool_service import execute_semantic_search; print('OK')"`

#### CREATE `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool.py`
- **IMPLEMENT**: `@vault_agent.tool async def obsidian_query_vault_tool(ctx, query_type, query?, path?, reference_note?, filters?, limit=10, response_format="concise")` with 7-element docstring (see `.agents/reference/adding_tools_guide.md`)
- **DOCSTRING MUST INCLUDE**:
  1. Summary
  2. Use when: find notes, explore structure, discover related, filter metadata, recent changes
  3. Do NOT use: read full content (use obsidian_get_context_tool), modify (use vault_manager_tool), existence checks (use concise+limit=1)
  4. Args with WHY for each param and enum value
  5. Returns format (concise vs detailed fields)
  6. Performance: concise ~50 tokens, detailed ~200 tokens, typical execution times
  7. Examples (5 realistic examples)
- **PATTERN**: Tool routes by query_type to service functions, logs execution events
- **GOTCHA**: Validate required params (query for semantic_search, reference_note for find_related, filters for search_by_metadata)
- **VALIDATE**: `uv run python -c "from app.core.agents import vault_agent; print([t.name for t in vault_agent.tools])"`

### Phase 4: Tool Registry & Integration

#### CREATE `app/core/agents/tool_registry.py`
- **IMPLEMENT**: Import `obsidian_query_vault_tool` with `# noqa: F401`, docstring explaining side-effect pattern, `__all__ = []`
- **PATTERN**: PRD side-effect import pattern
- **VALIDATE**: `uv run python -c "from app.core.agents import tool_registry, vault_agent; print(len(vault_agent.tools))"`

#### UPDATE `app/core/agents/__init__.py`
- **IMPLEMENT**: Add `from app.core.agents import tool_registry  # noqa: F401` and to __all__
- **VALIDATE**: `uv run python -c "from app.core.agents import vault_agent; print(len(vault_agent.tools))"`

#### UPDATE `app/main.py`
- **IMPLEMENT**: Add `from app.core.agents import tool_registry  # noqa: F401` after other imports
- **VALIDATE**: `uv run python -c "import app.main; from app.core.agents import vault_agent; print(len(vault_agent.tools))"`

#### UPDATE `app/agent/routes.py`
- **IMPLEMENT**: Import VaultManager, get_settings; instantiate VaultManager with settings.obsidian_vault_path; pass to AgentDeps in agent.run() call (line 29)
- **GOTCHA**: VaultManager created per request; fails if vault_path invalid
- **VALIDATE**: `uv run pytest app/agent/tests/test_routes.py -v`

### Phase 5: Testing

#### CREATE `app/features/obsidian_query_vault_tool/tests/conftest.py`
- **IMPLEMENT**: `test_vault_path(tmp_path)` with 3 notes, `test_vault_manager()`, `test_agent_deps()` fixtures
- **VALIDATE**: `uv run pytest app/features/obsidian_query_vault_tool/tests/ --collect-only`

#### CREATE `app/features/obsidian_query_vault_tool/tests/test_obsidian_query_vault_tool.py`
- **IMPLEMENT**: 10+ tests: tool registered, semantic search, list structure, search by tags, recent changes, concise format, detailed format, missing params, truncation suggestion
- **PATTERN**: `app/agent/tests/test_routes.py` for async tests with mocking
- **GOTCHA**: Use RunContext with test AgentDeps, not full agent mocking
- **VALIDATE**: `uv run pytest app/features/obsidian_query_vault_tool/tests/test_obsidian_query_vault_tool.py -v`

#### CREATE `app/tests/test_tool_integration.py`
- **IMPLEMENT**: Integration test with `agent.run()` using temp vault, verify tool called and result includes search term
- **VALIDATE**: `uv run pytest app/tests/test_tool_integration.py -v`

---

## VALIDATION COMMANDS

### Type Checking
```bash
uv run mypy app/
uv run pyright app/
```
Expected: 0 errors (strict mode)

### Linting
```bash
uv run ruff format .
uv run ruff check .
```
Expected: 0 errors

### Unit Tests
```bash
uv run pytest -v
uv run pytest app/shared/vault/tests/ -v
uv run pytest app/features/obsidian_query_vault_tool/tests/ -v
```
Expected: All pass

### Coverage
```bash
uv run pytest --cov=app --cov-report=term-missing
```
Expected: >80% for new code

### Integration
```bash
uv run pytest app/tests/test_tool_integration.py -v
```
Expected: Agent uses tool successfully

### Manual - Start Server
```bash
uv run uvicorn app.main:app --reload --port 8123
```
Expected: Logs show "application.lifecycle_started", no errors

### Manual - Verify Registration
```python
from app.core.agents import vault_agent
print([t.name for t in vault_agent.tools])
# Expected: ['obsidian_query_vault_tool']
```

### Manual - Test Endpoint
```bash
curl -X POST http://localhost:8123/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find notes about Python"}'
```
Expected: JSON response with search results

---

## ACCEPTANCE CRITERIA

- [ ] VaultManager reads files, parses frontmatter, searches content
- [ ] Tool registered with @vault_agent.tool decorator
- [ ] Tool has 7-element agent-optimized docstring
- [ ] Supports all 5 query types (semantic_search, list_structure, find_related, search_by_metadata, recent_changes)
- [ ] Supports concise (~50 tokens) and detailed (~200 tokens) formats
- [ ] AgentDeps updated with VaultManager and Settings
- [ ] Agent system prompt mentions tool availability
- [ ] Tool registry uses side-effect import pattern
- [ ] All validation commands pass (type checking, linting, tests)
- [ ] Coverage >80% for new code
- [ ] Agent successfully calls tool via agent.run()
- [ ] Verbose naming convention followed throughout
- [ ] VSA structure (shared/features/registry)
- [ ] Logging uses agent.tool.* events
- [ ] Path validation prevents directory traversal
- [ ] OpenAI compatibility endpoint works

---

## COMPLETION CHECKLIST

- [ ] All 25+ tasks completed in order
- [ ] Each task validated immediately
- [ ] Type checking passes (mypy + pyright strict)
- [ ] All tests pass (unit + integration)
- [ ] Manual testing confirms tool works
- [ ] Code follows verbose naming convention
- [ ] Logging follows hybrid dotted namespace
- [ ] Tool docstring has all 7 elements
- [ ] No security issues (path validation)

---

## NOTES

### Design Decisions

**Verbose Naming:** Per user requirement - `obsidian_query_vault_tool/` not `vault_query/` for greppability

**Shared Vault Infrastructure:** VaultManager in `app/shared/vault/` passes "3+ feature rule" (used by all 3 future tools)

**Tool Registry Pattern:** Central visibility via side-effect imports, easy to add future tools

**Service Layer:** Business logic separate from tool interface for testability

**7-Element Docstring:** CRITICAL for LLM tool selection - includes "Do NOT use" to prevent tool confusion

### Implementation Risks

- **Vault path invalid at startup:** Validate in settings, consider health check
- **Large vaults slow:** Document performance, consider indexing later
- **Frontmatter parsing errors:** Handle gracefully (notes without YAML valid)
- **Path traversal:** Validate with Path.resolve() + startswith check

### Future Enhancements

1. Tool 2: `obsidian_get_context_tool` (reading with context)
2. Tool 3: `obsidian_vault_manager_tool` (modifications)
3. Caching for frequently accessed notes
4. Semantic embeddings for better search

### Confidence Score: 9/10

**High confidence because:** Pydantic AI patterns researched, VSA structure clear, tool spec detailed, testing patterns established, all docs referenced

**Not 10/10 because:** First tool - edge cases may emerge, VaultManager performance unknown until tested with real vaults
