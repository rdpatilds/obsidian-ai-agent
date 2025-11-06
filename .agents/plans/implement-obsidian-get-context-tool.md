# Feature: Obsidian Get Context Tool

Validate documentation, codebase patterns, and task sanity before implementing. Import from correct files.

## Feature Description

Implement `obsidian_get_context_tool` - the third MVP tool for workflow-oriented reading with context. Retrieves full note content (~1500+ tokens) vs summaries (~50-200 tokens). Completes three-tool architecture: discover → **read** → modify.

## User Story

As an Obsidian vault user
I want to read full note content with surrounding context (related notes, backlinks, metadata)
So that I can synthesize information, understand relationships, and perform deep analysis

## Problem Statement

Users can discover (query tool) and modify (manager tool) but cannot read full content with context. Gap prevents synthesis workflows and daily note operations. MVP 33% incomplete.

## Solution Statement

Five context types: **read_note** (single), **read_multiple** (batch), **gather_related** (note + related), **daily_note** (today/date), **note_with_backlinks** (note + backlinks). Uses existing VaultManager methods. Backlinks via regex wikilink parsing.

## Feature Metadata

**Type**: New Capability | **Complexity**: Medium | **Systems**: `app/features/`, `app/core/agents/base.py`, `app/main.py`
**Dependencies**: `pydantic-ai`, `python-frontmatter` (existing), stdlib `re`

---

## CONTEXT REFERENCES

### Files to Read Before Implementing

**PRIMARY PATTERNS** (MIRROR EXACTLY):
- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool.py` (lines 1-195) - Tool structure, logging, error handling
- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_models.py` (lines 1-41) - Model structure with Field descriptions
- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_service.py` (lines 1-315) - Service layer pattern, `execute_find_related()` (lines 167-226)
- `app/features/obsidian_query_vault_tool/tests/test_obsidian_query_vault_tool.py` - Test structure with `@pytest.mark.asyncio`
- `app/features/obsidian_query_vault_tool/tests/conftest.py` - Fixtures to reuse

**VAULT OPERATIONS**:
- `app/shared/vault/vault_manager.py` (lines 119-156, 274-343, 455-496) - `read_note()`, `search_content()`, `get_recent_notes()`
- `app/shared/vault/vault_models.py` (lines 21-38) - `Note` model structure

**INTEGRATION**:
- `app/core/agents/base.py` (lines 25-108) - Agent instructions (UPDATE REQUIRED)
- `app/main.py` - Tool registration pattern

**DOCUMENTATION**:
- `.agents/reference/adding_tools_guide.md` (entire) - 7-element agent-optimized docstring pattern
- `.agents/reference/mvp-tool-designs.md` (lines 313-410) - Tool 3 specification
- [Obsidian Wikilinks](https://help.obsidian.md/Linking+notes+and+files/Internal+links) - `[[note]]` format

### New Files to Create

```
app/features/obsidian_get_context_tool/
├── __init__.py
├── obsidian_get_context_tool.py (tool registration)
├── obsidian_get_context_tool_models.py (Pydantic models)
├── obsidian_get_context_tool_service.py (business logic)
└── tests/
    ├── __init__.py
    ├── conftest.py (import from query tool)
    ├── test_obsidian_get_context_tool.py (integration tests)
    └── test_obsidian_get_context_tool_service.py (unit tests)
```

### Key Patterns

**Tool Registration** (from query tool):
```python
@vault_agent.tool
async def obsidian_get_context_tool(ctx: RunContext[AgentDeps], ...) -> Result:
    """7-element docstring from adding_tools_guide.md"""
    vault_manager = ctx.deps.vault_manager
    logger.info("agent.tool.execution_started", tool="obsidian_get_context_tool", ...)
    try:
        # Route to service
        result = await service.execute_<context_type>(...)
        logger.info("agent.tool.execution_completed", ...)
        return result
    except Exception as e:
        logger.error("agent.tool.execution_failed", error=str(e), exc_info=True)
        raise
```

**Naming**: snake_case files/functions, PascalCase models, `_tool` suffix

---

## STEP-BY-STEP TASKS

### 1. CREATE Package Init (`__init__.py`)
- **IMPLEMENT**: Empty file for Python package marker
- **VALIDATE**: `python -c "import app.features.obsidian_get_context_tool"`

### 2. CREATE Models (`obsidian_get_context_tool_models.py`)
- **IMPLEMENT**: Three Pydantic models with Field descriptions
```python
"""Pydantic models for Obsidian Get Context Tool."""
from pydantic import BaseModel, Field

class NoteContent(BaseModel):
    """Complete note representation for context results."""
    path: str = Field(..., description="Relative path from vault root")
    title: str = Field(..., description="Note title from frontmatter or filename")
    content: str = Field(..., description="Full markdown content without frontmatter")
    metadata: dict[str, str | list[str] | int | float | bool] | None = Field(
        default=None, description="Frontmatter metadata (detailed mode only)"
    )
    word_count: int = Field(..., description="Number of words in content")

class BacklinkInfo(BaseModel):
    """Information about a note linking to the target."""
    note_path: str = Field(..., description="Path to note containing the link")
    note_title: str = Field(..., description="Title of linking note")
    context: str = Field(..., description="Surrounding text where link appears (~100 chars)")

class ObsidianGetContextToolResult(BaseModel):
    """Result from obsidian_get_context_tool."""
    primary_note: NoteContent = Field(..., description="Main requested note")
    related_notes: list[NoteContent] | None = Field(
        default=None, description="Related notes (gather_related, note_with_backlinks)"
    )
    backlinks: list[BacklinkInfo] | None = Field(
        default=None, description="Notes linking to primary (note_with_backlinks only)"
    )
    token_estimate: int = Field(..., description="Approximate tokens in response content")
```
- **PATTERN**: Mirror `obsidian_query_vault_tool_models.py` structure
- **GOTCHA**: Use `dict[str, ...]` not `Dict` (Python 3.12+ built-in generics)
- **VALIDATE**: `uv run mypy app/features/obsidian_get_context_tool/`

### 3. CREATE Service Layer (`obsidian_get_context_tool_service.py`)
- **IMPLEMENT**: Helper functions + 5 execute functions
```python
"""Business logic for Obsidian Get Context Tool."""
import re
from datetime import datetime
from typing import Literal

from app.core.logging import get_logger
from app.features.obsidian_get_context_tool.obsidian_get_context_tool_models import (
    BacklinkInfo, NoteContent, ObsidianGetContextToolResult,
)
from app.shared.vault.vault_manager import VaultManager
from app.shared.vault.vault_models import Note

logger = get_logger(__name__)

def _estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token)."""
    return len(text) // 4

def _note_to_content(note: Note, response_format: str) -> NoteContent:
    """Convert Note to NoteContent based on format."""
    relative_path = str(note.path.relative_to(note.path.parent.parent))
    metadata = None
    if response_format == "detailed" and note.frontmatter:
        metadata = {
            "tags": note.frontmatter.tags,
            "title": note.frontmatter.title,
            "created": note.frontmatter.created.isoformat() if note.frontmatter.created else None,
            "modified": note.frontmatter.modified.isoformat() if note.frontmatter.modified else None,
            **note.frontmatter.custom
        }
    return NoteContent(
        path=relative_path,
        title=note.title,
        content=note.content,
        metadata=metadata,
        word_count=note.word_count
    )

def _find_backlinks(vault_manager: VaultManager, target_note_name: str) -> list[BacklinkInfo]:
    """Find all notes with wikilinks to target note."""
    backlinks: list[BacklinkInfo] = []
    wikilink_pattern = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]*)?\]\]')

    all_notes = vault_manager.list_notes(folder="", recursive=True)
    for vault_path in all_notes:
        try:
            note = vault_manager.read_note(str(vault_path.relative_path))
            matches = wikilink_pattern.finditer(note.content)
            for match in matches:
                linked_note = match.group(1).strip()
                if linked_note == target_note_name or f"{linked_note}.md" == target_note_name:
                    start = max(0, match.start() - 50)
                    end = min(len(note.content), match.end() + 50)
                    context = note.content[start:end].strip()
                    backlinks.append(BacklinkInfo(
                        note_path=str(vault_path.relative_path),
                        note_title=note.title,
                        context=context
                    ))
                    break
        except Exception as e:
            logger.warning("vault.backlink_search_failed", path=str(vault_path.relative_path), error=str(e))
    return backlinks

async def execute_read_note(
    vault_manager: VaultManager, target: str, response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Read single note with metadata."""
    logger.info("vault.read_note_started", target=target)
    note = vault_manager.read_note(target)
    note_content = _note_to_content(note, response_format)
    token_estimate = _estimate_tokens(note_content.content)
    logger.info("vault.read_note_completed", path=target, word_count=note.word_count)
    return ObsidianGetContextToolResult(primary_note=note_content, token_estimate=token_estimate)

async def execute_read_multiple(
    vault_manager: VaultManager, targets: list[str], response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Read multiple notes together."""
    logger.info("vault.read_multiple_started", count=len(targets))
    notes: list[NoteContent] = []
    total_tokens = 0
    primary_note = None

    for i, target in enumerate(targets):
        try:
            note = vault_manager.read_note(target)
            note_content = _note_to_content(note, response_format)
            if i == 0:
                primary_note = note_content
            else:
                notes.append(note_content)
            total_tokens += _estimate_tokens(note_content.content)
        except Exception as e:
            logger.warning("vault.read_multiple_failed", target=target, error=str(e))

    if not primary_note:
        raise ValueError("No notes could be read from targets list")

    logger.info("vault.read_multiple_completed", count=len(notes) + 1)
    return ObsidianGetContextToolResult(
        primary_note=primary_note, related_notes=notes if notes else None, token_estimate=total_tokens
    )

async def execute_gather_related(
    vault_manager: VaultManager, target: str, max_related: int, response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Read note and its related notes."""
    logger.info("vault.gather_related_started", target=target, max_related=max_related)

    primary = vault_manager.read_note(target)
    primary_content = _note_to_content(primary, response_format)

    # Find related notes (mirror execute_find_related pattern)
    words = primary.content.split()[:100]
    query = " ".join(words)
    related_notes_raw = vault_manager.search_content(query, limit=max_related + 1)
    related_notes_raw = [n for n in related_notes_raw if n.path != primary.path][:max_related]

    related_contents = [_note_to_content(n, response_format) for n in related_notes_raw]

    total_tokens = _estimate_tokens(primary_content.content)
    total_tokens += sum(_estimate_tokens(n.content) for n in related_contents)

    logger.info("vault.gather_related_completed", related_count=len(related_contents))
    return ObsidianGetContextToolResult(
        primary_note=primary_content,
        related_notes=related_contents if related_contents else None,
        token_estimate=total_tokens
    )

async def execute_daily_note(
    vault_manager: VaultManager, date: str | None, response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Get daily note for specific date or today."""
    logger.info("vault.daily_note_started", date=date)

    if date == "today" or date is None:
        target_date = datetime.now()
    else:
        target_date = datetime.fromisoformat(date)

    date_str = target_date.strftime("%Y-%m-%d")
    possible_paths = [
        f"Daily/{date_str}.md",
        f"daily/{date_str}.md",
        f"{date_str}.md",
        f"Journal/{date_str}.md",
    ]

    for path in possible_paths:
        try:
            note = vault_manager.read_note(path)
            note_content = _note_to_content(note, response_format)
            token_estimate = _estimate_tokens(note_content.content)
            logger.info("vault.daily_note_completed", path=path, date=date_str)
            return ObsidianGetContextToolResult(primary_note=note_content, token_estimate=token_estimate)
        except FileNotFoundError:
            continue

    raise FileNotFoundError(f"Daily note not found for {date_str}. Tried: {', '.join(possible_paths)}")

async def execute_note_with_backlinks(
    vault_manager: VaultManager, target: str, response_format: Literal["concise", "detailed"]
) -> ObsidianGetContextToolResult:
    """Read note with all backlinks."""
    logger.info("vault.note_with_backlinks_started", target=target)

    primary = vault_manager.read_note(target)
    primary_content = _note_to_content(primary, response_format)

    target_name = primary.path.stem
    backlinks = _find_backlinks(vault_manager, target_name)

    related_contents: list[NoteContent] = []
    for backlink in backlinks:
        try:
            note = vault_manager.read_note(backlink.note_path)
            related_contents.append(_note_to_content(note, response_format))
        except Exception as e:
            logger.warning("vault.backlink_read_failed", path=backlink.note_path, error=str(e))

    total_tokens = _estimate_tokens(primary_content.content)
    total_tokens += sum(_estimate_tokens(n.content) for n in related_contents)
    total_tokens += sum(_estimate_tokens(b.context) for b in backlinks)

    logger.info("vault.note_with_backlinks_completed", backlink_count=len(backlinks))
    return ObsidianGetContextToolResult(
        primary_note=primary_content,
        related_notes=related_contents if related_contents else None,
        backlinks=backlinks if backlinks else None,
        token_estimate=total_tokens
    )
```
- **PATTERN**: Mirror `obsidian_query_vault_tool_service.py` async functions
- **GOTCHA**: Use `note.path.stem` for filename without .md
- **GOTCHA**: Regex handles `[[Note]]` and `[[Note|Display]]` formats
- **VALIDATE**: `uv run mypy app/features/obsidian_get_context_tool/`

### 4. CREATE Tool Registration (`obsidian_get_context_tool.py`)
- **IMPLEMENT**: Tool with 7-element agent-optimized docstring
- **PATTERN**: **EXACTLY MIRROR** `obsidian_query_vault_tool.py:20-195`
- **DOCSTRING MUST INCLUDE**:
  1. One-line summary of tool purpose
  2. "Use this when" (5+ bullets for different scenarios)
  3. "Do NOT use this for" (3+ bullets pointing to other tools)
  4. Args section with WHY guidance for each parameter (not just WHAT)
  5. Returns section with format details
  6. Performance Notes with token estimates (~1500+ per note)
  7. Examples (6 examples covering all 5 context types)
- **KEY POINTS**:
  - Default `response_format="detailed"` (opposite of query tool)
  - Explain token costs clearly (query=~50-200, context=~1500+)
  - Show workflow: use query_tool first to find, then context_tool to read
  - Examples must use realistic paths like "Projects/ML.md" not "test.md"
- **PARAMETERS**:
  ```python
  context_type: Literal["read_note", "read_multiple", "gather_related", "daily_note", "note_with_backlinks"]
  target: str | None = None
  targets: list[str] | None = None
  date: str | None = None
  max_related: int = 3
  response_format: Literal["detailed", "concise"] = "detailed"
  ```
- **ROUTE TO SERVICE**: If/elif chain based on context_type, validate required params
- **VALIDATE**: `uv run mypy app/features/obsidian_get_context_tool/`

### 5. UPDATE Agent Instructions (`app/core/agents/base.py`)
- **LOCATION**: After line 47, before line 49 (Tool Selection section)
- **ADD**:
```python
### 3. obsidian_get_context_tool (READ FULL CONTENT)
Retrieve full note content with optional context for synthesis and analysis.
- Use for: Reading complete notes, gathering related notes, discovering backlinks, daily notes
- Context types: read_note, read_multiple, gather_related, daily_note, note_with_backlinks
- Default to response_format="detailed" for metadata
- Token-heavy (~1500+ per note) - use query_tool first to find, then this to read
```
- **UPDATE**: Line 50-53 - Change "TWO tools" to "THREE tools", add get_context_tool to list
- **VALIDATE**: `uv run mypy app/core/agents/`

### 6. REGISTER Tool (`app/main.py`)
- **LOCATION**: After `obsidian_note_manager_tool` import
- **ADD**: `import app.features.obsidian_get_context_tool.obsidian_get_context_tool  # noqa: F401`
- **GOTCHA**: `# noqa: F401` suppresses "unused import" (side effect for tool registration)
- **VALIDATE**: `uv run python -c "from app.main import app; print('OK')"`

### 7. CREATE Test Package Init (`tests/__init__.py`)
- **IMPLEMENT**: Empty file for test package marker
- **VALIDATE**: `python -c "import app.features.obsidian_get_context_tool.tests"`

### 8. CREATE Test Fixtures (`tests/conftest.py`)
- **IMPLEMENT**: Import shared fixtures from query tool
```python
"""Test fixtures for obsidian_get_context_tool - reuse from query tool."""
from app.features.obsidian_query_vault_tool.tests.conftest import (
    test_agent_deps, test_vault_manager, test_vault_path,
)
__all__ = ["test_vault_path", "test_vault_manager", "test_agent_deps"]
```
- **PATTERN**: Reuse existing test vault (3 notes: project_alpha.md, meeting_notes.md, daily_journal.md)
- **VALIDATE**: `uv run pytest app/features/obsidian_get_context_tool/tests/ --collect-only`

### 9. CREATE Service Tests (`tests/test_obsidian_get_context_tool_service.py`)
- **IMPLEMENT**: 8+ async test functions
```python
"""Tests for obsidian_get_context_tool service layer."""
import pytest
from app.features.obsidian_get_context_tool.obsidian_get_context_tool_service import (
    execute_read_note, execute_read_multiple, execute_gather_related,
    execute_daily_note, execute_note_with_backlinks,
)
from app.shared.vault.vault_manager import VaultManager

@pytest.mark.asyncio
async def test_read_note_basic(test_vault_manager: VaultManager) -> None:
    """Test basic note reading."""
    result = await execute_read_note(test_vault_manager, "project_alpha.md", "concise")
    assert result.primary_note.path == "project_alpha.md"
    assert result.primary_note.word_count > 0
    assert result.token_estimate > 0

@pytest.mark.asyncio
async def test_read_note_detailed_format(test_vault_manager: VaultManager) -> None:
    """Test detailed format includes metadata."""
    result = await execute_read_note(test_vault_manager, "project_alpha.md", "detailed")
    assert result.primary_note.metadata is not None
    assert "tags" in result.primary_note.metadata

@pytest.mark.asyncio
async def test_read_note_not_found(test_vault_manager: VaultManager) -> None:
    """Test reading non-existent note raises error."""
    with pytest.raises(FileNotFoundError):
        await execute_read_note(test_vault_manager, "nonexistent.md", "concise")

@pytest.mark.asyncio
async def test_read_multiple_notes(test_vault_manager: VaultManager) -> None:
    """Test reading multiple notes."""
    result = await execute_read_multiple(
        test_vault_manager, ["project_alpha.md", "meeting_notes.md"], "concise"
    )
    assert result.primary_note.path == "project_alpha.md"
    assert result.related_notes is not None
    assert len(result.related_notes) == 1

@pytest.mark.asyncio
async def test_gather_related_notes(test_vault_manager: VaultManager) -> None:
    """Test gathering related notes."""
    result = await execute_gather_related(test_vault_manager, "project_alpha.md", 2, "concise")
    assert result.primary_note.path == "project_alpha.md"
    assert isinstance(result.related_notes, (list, type(None)))

@pytest.mark.asyncio
async def test_note_with_backlinks_no_backlinks(test_vault_manager: VaultManager) -> None:
    """Test note with no backlinks."""
    result = await execute_note_with_backlinks(test_vault_manager, "project_alpha.md", "concise")
    assert result.primary_note.path == "project_alpha.md"
    assert result.backlinks is None or len(result.backlinks) == 0

@pytest.mark.asyncio
async def test_daily_note_not_found(test_vault_manager: VaultManager) -> None:
    """Test daily note missing raises error with helpful message."""
    with pytest.raises(FileNotFoundError, match="Tried:"):
        await execute_daily_note(test_vault_manager, "2099-12-31", "concise")

@pytest.mark.asyncio
async def test_concise_vs_detailed_metadata(test_vault_manager: VaultManager) -> None:
    """Test concise omits metadata, detailed includes it."""
    concise = await execute_read_note(test_vault_manager, "project_alpha.md", "concise")
    detailed = await execute_read_note(test_vault_manager, "project_alpha.md", "detailed")
    assert concise.primary_note.metadata is None
    assert detailed.primary_note.metadata is not None
```
- **PATTERN**: Mirror `test_obsidian_query_vault_tool.py` structure
- **VALIDATE**: `uv run pytest app/features/obsidian_get_context_tool/tests/test_obsidian_get_context_tool_service.py -v`

### 10. CREATE Integration Tests (`tests/test_obsidian_get_context_tool.py`)
- **IMPLEMENT**: 2 tests for tool registration
```python
"""Integration tests for obsidian_get_context_tool."""
import pytest
from pydantic_ai import RunContext
from app.core.agents import AgentDeps
from app.features.obsidian_get_context_tool.obsidian_get_context_tool import obsidian_get_context_tool

@pytest.mark.asyncio
async def test_tool_registered(test_agent_deps: AgentDeps) -> None:
    """Test that tool is registered and callable."""
    ctx = RunContext(deps=test_agent_deps, retry=0, messages=[])
    result = await obsidian_get_context_tool(ctx, context_type="read_note", target="project_alpha.md")
    assert result.primary_note.path == "project_alpha.md"

@pytest.mark.asyncio
async def test_tool_parameter_validation(test_agent_deps: AgentDeps) -> None:
    """Test tool validates required parameters."""
    ctx = RunContext(deps=test_agent_deps, retry=0, messages=[])
    with pytest.raises(ValueError, match="target parameter required"):
        await obsidian_get_context_tool(ctx, context_type="read_note", target=None)
```
- **VALIDATE**: `uv run pytest app/features/obsidian_get_context_tool/tests/test_obsidian_get_context_tool.py -v`

### 11. VALIDATE All Tests
- **RUN**: `uv run pytest app/features/obsidian_get_context_tool/tests/ -v` (all new tests pass)
- **RUN**: `uv run pytest -v` (all existing tests still pass - no regressions)

### 12. VALIDATE Type Checking
- **RUN**: `uv run mypy app/` (zero errors in strict mode)
- **RUN**: `uv run pyright app/` (zero errors in strict mode)

### 13. VALIDATE Linting
- **RUN**: `uv run ruff check .` (zero errors)
- **RUN**: `uv run ruff format .` (auto-format if needed)

### 14. MANUAL VALIDATION
- **START**: `uv run uvicorn app.main:app --reload --port 8123`
- **TEST 1**: Read full note
  ```json
  POST http://localhost:8123/v1/chat/completions
  {"model": "paddy", "messages": [{"role": "user", "content": "Read project_alpha.md in full"}]}
  ```
  **VERIFY**: Agent uses `obsidian_get_context_tool` with `context_type="read_note"` and returns full content
- **TEST 2**: Daily note
  ```json
  {"model": "paddy", "messages": [{"role": "user", "content": "Show me today's daily note"}]}
  ```
  **VERIFY**: Agent uses `context_type="daily_note"` with `date="today"`
- **TEST 3**: Backlinks
  ```json
  {"model": "paddy", "messages": [{"role": "user", "content": "What notes link to project_alpha.md?"}]}
  ```
  **VERIFY**: Agent uses `context_type="note_with_backlinks"`

---

## ACCEPTANCE CRITERIA

- [ ] All 5 context types implemented and working
- [ ] All validation commands pass (mypy, pyright, ruff, pytest)
- [ ] 8+ unit tests for service functions
- [ ] 2+ integration tests for tool registration
- [ ] Code mirrors query tool pattern exactly
- [ ] No test regressions (existing tests pass)
- [ ] Agent instructions updated (THREE tools, not TWO)
- [ ] Tool registered in main.py via side-effect import
- [ ] Tool docstring follows 7-element pattern from adding_tools_guide.md
- [ ] Backlinks handle `[[Note]]` and `[[Note|Text]]` formats
- [ ] Daily note tries 4 path patterns with clear error listing tried paths
- [ ] Token estimation implemented (~4 chars/token)
- [ ] Concise format omits metadata, detailed includes it
- [ ] Manual testing confirms all context types work via OpenAI API

---

## COMPLETION CHECKLIST

- [ ] All 14 tasks completed in order
- [ ] Each validation passed immediately after task
- [ ] Full test suite passes (34+ existing tests + 10+ new tests)
- [ ] No type/lint errors
- [ ] Manual testing via API confirms all 5 context types work
- [ ] Agent correctly selects all THREE tools for appropriate tasks
- [ ] Performance acceptable (<200ms single note, <1s multi-note operations)
- [ ] Token estimates reasonably accurate (±20%)

---

## DESIGN NOTES

**Why separate from query tool?**
Query returns summaries (~50-200 tokens) for discovery. Context returns full content (~1500+ tokens) for synthesis. Prevents token waste in two-step workflow: find → read.

**Why 5 context types vs separate tools?**
Follows "fewer, smarter tools" principle. All are reading operations with different context needs. Reduces agent confusion (1 read tool vs 5 separate tools).

**Why default "detailed"?**
Reading implies need for full information. Query tool defaults "concise" (discovery), context tool "detailed" (reading). User explicitly requested content.

**Backlink implementation:**
Regex wikilink parsing (simple, no dependencies). Matches with/without .md extension. Handles `[[Note]]` and `[[Note|Display Text]]` formats. Future: graph traversal for advanced relationships.

**Daily note paths:**
Tries 4 common patterns (Daily/, daily/, root, Journal/). YYYY-MM-DD format (ISO 8601). Fails with helpful error listing tried paths. Future: configurable via settings.

**Trade-offs:**
Chose completeness over token efficiency. This tool is for reading full content. Use query tool first to verify note exists (~50 tokens), then context tool to read (~1500+ tokens).

**Performance:**
Backlink discovery is O(n) vault scan. Acceptable for MVP (<1s for vaults <1000 notes). Future optimization: cache backlink index, update on writes.

**Related note algorithm:**
Simple content similarity (first 100 words). Mirrors `execute_find_related()` from query tool. Future: use tags, shared links, graph proximity.

**Future enhancements:**
- Backlink caching with incremental updates
- Graph traversal for sophisticated related discovery
- Daily note templates for creation
- Excerpt highlighting in backlink context
- Custom daily note paths via settings
- Tag-based relationship discovery
- Performance monitoring of token estimates vs actual
