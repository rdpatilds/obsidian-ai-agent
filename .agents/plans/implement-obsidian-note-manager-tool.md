# Feature: Obsidian Note Manager Tool

Implement comprehensive note/folder management tool enabling create, update, delete, move operations plus bulk operations. Combined with existing query tool, enables workflows like "find notes tagged 'inbox', move to Archive."

## User Story

As an Obsidian user interacting with Paddy
I want to create, update, move, delete, and organize notes/folders using natural language
So that I can manage my vault efficiently without manual file operations

## Problem & Solution

**Problem:** Agent currently read-only (query tool only). Cannot modify vault content.

**Solution:** Single consolidated tool with 11 operations following established VSA pattern:
- Note ops: create, update, append, delete, move
- Folder ops: create, delete, move
- Bulk ops: bulk_tag, bulk_move, bulk_update_metadata

**Feature Type:** New Capability | **Complexity:** High | **Systems:** app/features/, app/shared/vault/, app/core/agents/

---

## CONTEXT REFERENCES

### Must Read Before Implementing

**Patterns to Mirror:**
- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool.py` - Tool decorator, RunContext, error handling, logging
- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_service.py` - Service layer operation routing
- `app/features/obsidian_query_vault_tool/obsidian_query_vault_tool_models.py` - Pydantic model structure

**Integration Points:**
- `app/core/agents/base.py` (lines 1-53) - Agent definition, system prompt to update
- `app/core/agents/tool_registry.py` (lines 1-24) - Side-effect import pattern
- `app/shared/vault/vault_manager.py` (lines 1-380) - Extend with write methods
- `app/shared/vault/vault_models.py` - Reuse Note, Frontmatter, VaultPath models

**Critical References:**
- `.agents/reference/adding_tools_guide.md` - 7-element agent tool docstring structure (CRITICAL)
- `.agents/reference/mvp-tool-designs.md` (lines 149-311) - Complete operation specs, parameters, error messages
- `.agents/reference/vsa-patterns.md` (lines 232-263, 424-536) - Feature slice structure, naming conventions

**External Docs:**
- https://ai.pydantic.dev/tools/ - @agent.tool decorator, RunContext[AgentDeps] pattern
- https://python-frontmatter.readthedocs.io/ - frontmatter.dumps() for writing YAML frontmatter

### Files to Create

```
app/features/obsidian_note_manager_tool/
├── __init__.py
├── obsidian_note_manager_tool.py          # Tool function with @vault_agent.tool
├── obsidian_note_manager_tool_models.py   # ObsidianNoteManagerToolResult
├── obsidian_note_manager_tool_service.py  # 11 execute_* functions
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_obsidian_note_manager_tool.py
    └── test_obsidian_note_manager_tool_service.py
```

### Files to Update

- `app/shared/vault/vault_manager.py` - Add write_note(), append_to_note(), delete_note(), move_note(), create_folder(), delete_folder(), move_folder()
- `app/core/agents/tool_registry.py` - Add import for new tool
- `app/core/agents/base.py` - Update system prompt with tool documentation and workflows

### Key Patterns

**Tool Function Structure:** Mirror `obsidian_query_vault_tool.py:20-194`
- @vault_agent.tool decorator
- async def with ctx: RunContext[AgentDeps]
- operation: Literal[...] for routing
- Access vault_manager via ctx.deps.vault_manager
- Structured logging: agent.tool.execution_{started|completed|failed}
- try/except with exc_info=True

**Service Function Structure:** Mirror `obsidian_query_vault_tool_service.py:76-111`
- async def execute_operation(vault_manager, params...)
- logger.info("vault.operation_started", ...)
- Business logic with error handling
- Return structured result model
- logger.info("vault.operation_completed", ...)

**VaultManager Write Pattern:** Follow read_note() pattern at `vault_manager.py:118-155`
- Validate path with self._validate_path()
- Use frontmatter.dumps(frontmatter.Post(content, **metadata))
- Create parent dirs: abs_path.parent.mkdir(parents=True, exist_ok=True)
- Structured logging with vault.* events

**Logging Events:** `{domain}.{component}.{action}_{state}`
- agent.tool.execution_started/completed/failed
- vault.write_note_started/completed/failed
- vault.operation_completed with affected_count

---

## IMPLEMENTATION PLAN

### Phase 1: Extend VaultManager (9 Methods)

Add atomic write operations to VaultManager following existing read patterns.

**write_note(relative_path, content, metadata, overwrite):**
- Validate path, check overwrite constraint
- Use frontmatter.dumps() if metadata provided
- Create parent dirs, write file
- Return absolute path

**append_to_note(relative_path, content):**
- Read existing note via read_note()
- Append content with newline handling
- Preserve existing frontmatter
- Write back via write_note()

**delete_note(relative_path):** Validate path, unlink file

**move_note(source, dest, create_folders):** Validate both paths, Path.rename()

**create_folder(relative_path, exist_ok):** Validate path, mkdir(parents=True)

**delete_folder(relative_path, recursive):** Validate path, use shutil.rmtree() if recursive

**move_folder(source, dest):** Validate both paths, Path.rename()

### Phase 2: Feature Slice Structure

Create directory: `app/features/obsidian_note_manager_tool/` with __init__, models, service, tool files.

### Phase 3: Pydantic Models

**ObsidianNoteManagerToolResult(BaseModel):**
- success: bool
- operation: str
- affected_count: int
- affected_paths: list[str]
- message: str
- warnings: list[str] | None
- partial_success: bool | None (bulk ops)
- failures: list[dict[str, str]] | None (bulk ops)

### Phase 4: Service Layer (11 Functions)

**Note Operations:**
- execute_create_note(vault_manager, target, content, metadata, create_folders)
- execute_update_note(vault_manager, target, content, metadata)
- execute_append_note(vault_manager, target, content)
- execute_delete_note(vault_manager, target, confirm_destructive)
- execute_move_note(vault_manager, target, destination, create_folders)

**Folder Operations:**
- execute_create_folder(vault_manager, target, create_folders)
- execute_delete_folder(vault_manager, target, confirm_destructive)
- execute_move_folder(vault_manager, target, destination)

**Bulk Operations:**
- execute_bulk_tag(vault_manager, targets, metadata) - Loop targets, read note, merge tags, write back
- execute_bulk_move(vault_manager, targets, destination, create_folders) - Create dest folder, move each
- execute_bulk_update_metadata(vault_manager, targets, metadata_changes) - Loop, read, merge metadata, write

**Error Handling:** Return ObsidianNoteManagerToolResult(success=False, message=...) on exceptions. Bulk ops track succeeded/failed lists.

### Phase 5: Tool Function

**Signature:**
```python
@vault_agent.tool
async def obsidian_note_manager_tool(
    ctx: RunContext[AgentDeps],
    operation: Literal[11 operations...],
    target: str | None = None,
    targets: list[str] | None = None,
    content: str | None = None,
    destination: str | None = None,
    metadata: dict[...] | None = None,
    metadata_changes: dict[...] | None = None,
    confirm_destructive: bool = False,
    create_folders: bool = True,
) -> ObsidianNoteManagerToolResult:
```

**Docstring:** Follow `.agents/reference/adding_tools_guide.md` 7-element structure:
1. One-line summary
2. Use this when (6 scenarios for discovery/modification/organization)
3. Do NOT use this for (searching, reading without modification)
4. Args (operation with 11 variants + use cases, all parameters with guidance)
5. Returns (ObsidianNoteManagerToolResult structure)
6. Performance Notes (~50ms single ops, ~20-50ms per item bulk ops)
7. Examples (10+ examples covering all operation types)

**Routing:** if/elif chain on operation parameter to call appropriate service function with parameter validation.

### Phase 6: Agent Integration

**tool_registry.py:** Add `from app.features.obsidian_note_manager_tool import obsidian_note_manager_tool  # noqa: F401`

**base.py system prompt:** Update instructions to:
- List both tools (query + manager)
- Document workflow patterns (search then modify, bulk organization)
- Explain safety (confirm_destructive required for deletes)
- Recommend tool selection (query=read-only, manager=write)

### Phase 7: Tests

**Fixtures (conftest.py):** temp_vault, vault_manager, sample_note

**Service Tests:** Test all 11 operations - success cases, FileNotFoundError, confirm_destructive validation, partial success in bulk ops

**Tool Tests:** Mock RunContext, test parameter validation, operation routing, error propagation

**Edge Cases:** Non-existent folders with create_folders=False, duplicate destinations, mixed valid/invalid bulk targets

---

## STEP-BY-STEP TASKS

Execute tasks in order. Each task is atomic and independently testable.

### Task 1: ADD write_note() to VaultManager

**FILE:** app/shared/vault/vault_manager.py

**IMPLEMENT:** Add method after read_note() (around line 156)
```python
def write_note(
    self, relative_path: str, content: str,
    metadata: dict[str, str | list[str] | int | float | bool] | None = None,
    overwrite: bool = False
) -> Path:
```

**PATTERN:** Mirror read_note() at lines 118-155
- Start: `abs_path = self._validate_path(relative_path)`
- Check: `if abs_path.exists() and not overwrite: raise ValueError(...)`
- Log: `self.logger.info("vault.write_note_started", path=relative_path)`
- Frontmatter: `if metadata: post = frontmatter.Post(content, **metadata); full_content = frontmatter.dumps(post)`
- Write: `abs_path.parent.mkdir(parents=True, exist_ok=True); abs_path.write_text(full_content, encoding="utf-8")`
- Log: `self.logger.info("vault.write_note_completed", path=relative_path)`
- Return: `return abs_path`

**IMPORTS:** frontmatter already imported at line 6

**GOTCHA:** frontmatter.dumps() requires frontmatter.Post object, not dict

**VALIDATE:** `uv run mypy app/shared/vault/vault_manager.py` (must pass strict mode)

### Task 2: ADD append_to_note() to VaultManager

**FILE:** app/shared/vault/vault_manager.py

**IMPLEMENT:** Add method after write_note()
```python
def append_to_note(self, relative_path: str, content: str) -> Path:
```

**LOGIC:**
1. Read existing: `note = self.read_note(relative_path)` (raises FileNotFoundError if missing)
2. Append content: `new_content = note.content; if not new_content.endswith("\n"): new_content += "\n"; new_content += content`
3. Preserve frontmatter: Build metadata dict from note.frontmatter if exists
4. Write back: `return self.write_note(relative_path, new_content, metadata, overwrite=True)`

**VALIDATE:** `uv run mypy app/shared/vault/vault_manager.py`

### Task 3: ADD delete_note(), move_note() to VaultManager

**FILE:** app/shared/vault/vault_manager.py

**delete_note(relative_path):**
- Validate path, check exists, `abs_path.unlink()`, log vault.delete_note_{started|completed|failed}

**move_note(source, dest, create_folders):**
- Validate both paths, check source exists, check dest doesn't exist
- Create parent if create_folders: `dest_abs.parent.mkdir(parents=True, exist_ok=True)`
- Move: `source_abs.rename(dest_abs)`

**VALIDATE:** `uv run mypy app/shared/vault/vault_manager.py`

### Task 4: ADD folder operations to VaultManager

**FILE:** app/shared/vault/vault_manager.py

**create_folder(relative_path, exist_ok):** `abs_path.mkdir(parents=True, exist_ok=exist_ok)`

**delete_folder(relative_path, recursive):**
- Import shutil at top: `import shutil`
- Check is_dir(), check empty if not recursive
- Delete: `shutil.rmtree(abs_path)` if recursive else `abs_path.rmdir()`

**move_folder(source, dest):** Similar to move_note but check is_dir()

**VALIDATE:** `uv run mypy app/shared/vault/vault_manager.py && uv run pyright app/shared/vault/vault_manager.py`

### Task 5: CREATE feature slice structure

**CREATE:** app/features/obsidian_note_manager_tool/__init__.py (empty)

**CREATE:** app/features/obsidian_note_manager_tool/tests/__init__.py (empty)

**VERIFY:** Directory structure matches Files to Create section

### Task 6: CREATE models file

**FILE:** app/features/obsidian_note_manager_tool/obsidian_note_manager_tool_models.py

**PATTERN:** Mirror obsidian_query_vault_tool_models.py structure

**IMPLEMENT:** ObsidianNoteManagerToolResult class per Phase 3 spec
- All fields with Field(..., description="...")
- Use Pydantic BaseModel
- Type hints: bool, str, int, list[str], list[str] | None, list[dict[str, str]] | None

**VALIDATE:** `uv run mypy app/features/obsidian_note_manager_tool/obsidian_note_manager_tool_models.py`

### Task 7: CREATE service file - Note operations

**FILE:** app/features/obsidian_note_manager_tool/obsidian_note_manager_tool_service.py

**IMPORTS:**
```python
from typing import Literal
from app.core.logging import get_logger
from app.features.obsidian_note_manager_tool.obsidian_note_manager_tool_models import ObsidianNoteManagerToolResult
from app.shared.vault.vault_manager import VaultManager

logger = get_logger(__name__)
```

**IMPLEMENT 5 NOTE FUNCTIONS:**
- execute_create_note(vault_manager, target, content, metadata, create_folders) → Result
- execute_update_note(vault_manager, target, content, metadata) → Result
- execute_append_note(vault_manager, target, content) → Result
- execute_delete_note(vault_manager, target, confirm_destructive) → Result
- execute_move_note(vault_manager, target, destination, create_folders) → Result

**PATTERN PER FUNCTION:**
```python
async def execute_operation(...) -> ObsidianNoteManagerToolResult:
    logger.info("vault.operation_started", ...)
    try:
        # Call VaultManager method
        vault_manager.operation_method(...)
        logger.info("vault.operation_completed", ...)
        return ObsidianNoteManagerToolResult(success=True, operation="...", affected_count=1, affected_paths=[...], message="...")
    except SpecificError as e:
        logger.warning("vault.operation_failed", error=str(e))
        return ObsidianNoteManagerToolResult(success=False, operation="...", affected_count=0, affected_paths=[], message=str(e))
```

**GOTCHA:** delete_note must check confirm_destructive FIRST, return failure if False

**VALIDATE:** `uv run mypy app/features/obsidian_note_manager_tool/obsidian_note_manager_tool_service.py`

### Task 8: ADD service file - Folder & Bulk operations

**FILE:** app/features/obsidian_note_manager_tool/obsidian_note_manager_tool_service.py (continue)

**IMPLEMENT 3 FOLDER FUNCTIONS:** execute_create_folder, execute_delete_folder, execute_move_folder (mirror note ops)

**IMPLEMENT 3 BULK FUNCTIONS:**

**execute_bulk_tag(vault_manager, targets, metadata):**
- Loop targets: succeeded = []; failed = []
- For each: read note, merge tags (list(set(existing + new))), write back
- Catch per-item exceptions, add to failed list
- Return with partial_success=True if mixed results

**execute_bulk_move(vault_manager, targets, destination, create_folders):**
- Create destination folder first if create_folders
- Loop targets: extract filename, move to destination/filename
- Track succeeded/failed

**execute_bulk_update_metadata(vault_manager, targets, metadata_changes):**
- Loop targets: read, merge metadata dict, write back
- Track succeeded/failed

**VALIDATE:** `uv run mypy app/features/obsidian_note_manager_tool/obsidian_note_manager_tool_service.py`

### Task 9: CREATE tool file with comprehensive docstring

**FILE:** app/features/obsidian_note_manager_tool/obsidian_note_manager_tool.py

**IMPORTS:**
```python
from typing import Literal
from pydantic_ai import RunContext
from app.core.agents import AgentDeps, vault_agent
from app.core.logging import get_logger
from app.features.obsidian_note_manager_tool import obsidian_note_manager_tool_service as service
from app.features.obsidian_note_manager_tool.obsidian_note_manager_tool_models import ObsidianNoteManagerToolResult

logger = get_logger(__name__)
```

**SIGNATURE:** Per Phase 5 - @vault_agent.tool decorator, async def, 9 parameters

**DOCSTRING (CRITICAL - 7 ELEMENTS):**
1. **Summary:** "Manage notes and folders in Obsidian vault - all modification operations."
2. **Use this when:** 6 bullet points (create/modify content, delete, move/reorganize, bulk ops, folder mgmt)
3. **Do NOT use:** 3 bullet points (searching, reading, checking existence)
4. **Args:** operation with 11 variants + specific use cases, all parameters with when to use
5. **Returns:** ObsidianNoteManagerToolResult structure description
6. **Performance Notes:** Single ops <50ms, bulk ops ~20-50ms per item, token usage ~100
7. **Examples:** 10+ examples covering all operation types with realistic paths

**REFERENCE:** `.agents/reference/adding_tools_guide.md` for exact docstring structure
**REFERENCE:** `.agents/reference/mvp-tool-designs.md` lines 209-251 for operation examples

**ROUTING LOGIC:**
```python
vault_manager = ctx.deps.vault_manager
logger.info("agent.tool.execution_started", tool="obsidian_note_manager_tool", operation=operation)
try:
    if operation == "create_note":
        if not target or not content: raise ValueError(...)
        result = await service.execute_create_note(...)
    elif operation == "update_note":
        ...
    # ... (11 total branches)
    logger.info("agent.tool.execution_completed", ...)
    return result
except Exception as e:
    logger.error("agent.tool.execution_failed", exc_info=True, ...)
    raise
```

**VALIDATE:** `uv run mypy app/features/obsidian_note_manager_tool/obsidian_note_manager_tool.py`

### Task 10: UPDATE tool_registry.py

**FILE:** app/core/agents/tool_registry.py

**ADD:** Import after line 17 (after query tool import)
```python
from app.features.obsidian_note_manager_tool import (  # noqa: F401
    obsidian_note_manager_tool,
)
```

**VALIDATE:** `uv run mypy app/core/agents/tool_registry.py`

### Task 11: UPDATE agent system prompt

**FILE:** app/core/agents/base.py

**REPLACE:** instructions string (lines 27-50) with new content documenting:
- Both tools (query + manager) with clear separation
- Workflow patterns: search→modify, bulk organization, content creation
- Safety guidelines: confirm_destructive, partial success explanation
- Tool selection: query=read-only, manager=write

**PATTERN:** Keep "You are Paddy" opening, add "## Available Tools" section with TWO tools, add "## Workflow Patterns" and "## Guidelines" sections

**VALIDATE:** `uv run mypy app/core/agents/base.py`

### Task 12: CREATE test fixtures

**FILE:** app/features/obsidian_note_manager_tool/tests/conftest.py

**IMPLEMENT:** 3 fixtures using @pytest.fixture decorator
- temp_vault(tmp_path) → Path: Create tmp_path / "test_vault", mkdir, return
- vault_manager(temp_vault) → VaultManager: Return VaultManager(temp_vault)
- sample_note(vault_manager) → str: Create note via vault_manager.write_note(), return path

**VALIDATE:** `uv run pytest app/features/obsidian_note_manager_tool/tests/conftest.py -v`

### Task 13: CREATE service tests

**FILE:** app/features/obsidian_note_manager_tool/tests/test_obsidian_note_manager_tool_service.py

**IMPLEMENT:** Test functions with @pytest.mark.asyncio, use fixtures

**TESTS (minimum 15):**
- test_execute_create_note_success
- test_execute_create_note_already_exists
- test_execute_update_note_success
- test_execute_update_note_not_found
- test_execute_append_note_success
- test_execute_delete_note_without_confirmation (assert success=False)
- test_execute_delete_note_with_confirmation
- test_execute_move_note_success
- test_execute_create_folder_success
- test_execute_bulk_tag_success
- test_execute_bulk_tag_partial_success (mix valid/invalid)
- test_execute_bulk_move_success
- test_execute_bulk_update_metadata_success
- test_folder_operations (create/delete/move)

**PATTERN:**
```python
@pytest.mark.asyncio
async def test_execute_create_note_success(vault_manager):
    result = await service.execute_create_note(vault_manager, "test.md", "content", {"tags": ["test"]}, True)
    assert result.success is True
    assert result.operation == "create_note"
    assert "test.md" in result.affected_paths
    # Verify file exists
    note = vault_manager.read_note("test.md")
    assert note.content == "content"
```

**VALIDATE:** `uv run pytest app/features/obsidian_note_manager_tool/tests/test_obsidian_note_manager_tool_service.py -v`

### Task 14: CREATE tool integration tests

**FILE:** app/features/obsidian_note_manager_tool/tests/test_obsidian_note_manager_tool.py

**IMPLEMENT:** Mock RunContext[AgentDeps] for integration testing

**TESTS (minimum 5):**
- test_tool_create_note (verify routing to service)
- test_tool_missing_required_param (expect ValueError)
- test_tool_invalid_operation (expect ValueError)
- test_tool_logging_events (verify logger calls)
- test_tool_error_propagation

**MOCK PATTERN:**
```python
from unittest.mock import Mock
from pydantic_ai import RunContext

@pytest.mark.asyncio
async def test_tool_create_note(vault_manager, monkeypatch):
    deps = AgentDeps(vault_manager=vault_manager, settings=Mock())
    ctx = Mock(spec=RunContext)
    ctx.deps = deps
    result = await obsidian_note_manager_tool(ctx=ctx, operation="create_note", target="test.md", content="content")
    assert result.success is True
```

**VALIDATE:** `uv run pytest app/features/obsidian_note_manager_tool/tests/test_obsidian_note_manager_tool.py -v`

---

## TESTING STRATEGY

**Unit Tests:** All 11 operations (success, error, edge cases), confirm_destructive validation, bulk partial success, frontmatter merging

**Integration Tests:** Tool function with mocked RunContext, parameter routing, logging output

**Edge Cases:** Missing folders with create_folders=False, duplicate destinations, destructive ops without confirmation, bulk mixed results

---

## VALIDATION COMMANDS

```bash
# Level 1: Linting & Formatting
uv run ruff check app/features/obsidian_note_manager_tool/ app/shared/vault/vault_manager.py app/core/agents/
uv run ruff format app/features/obsidian_note_manager_tool/ app/shared/vault/vault_manager.py app/core/agents/

# Level 2: Type Checking
uv run mypy app/features/obsidian_note_manager_tool/ app/shared/vault/vault_manager.py app/core/agents/
uv run pyright app/features/obsidian_note_manager_tool/ app/shared/vault/vault_manager.py app/core/agents/

# Level 3: Unit Tests
uv run pytest app/features/obsidian_note_manager_tool/tests/ -v

# Level 4: Full Suite
uv run pytest -v

# Level 5: Manual Validation
uv run uvicorn app.main:app --reload --port 8123
# Python REPL: from app.core.agents.base import vault_agent; print([tool.name for tool in vault_agent.tools])
# Should show: ['obsidian_query_vault_tool', 'obsidian_note_manager_tool']
```

---

## ACCEPTANCE CRITERIA

- [ ] VaultManager has 7 new write methods (write/append/delete/move notes, create/delete/move folders)
- [ ] Feature slice follows VSA structure (models, service, tool, tests)
- [ ] Tool function has 7-element agent-optimized docstring (per adding_tools_guide.md)
- [ ] Service layer implements all 11 operations with structured results
- [ ] Tool registered in tool_registry.py via side-effect import
- [ ] Agent system prompt documents both tools and workflows
- [ ] All validation commands pass (ruff, mypy, pyright, pytest)
- [ ] Tests cover all operations, errors, edge cases (80%+ coverage)
- [ ] Safety mechanisms work (confirm_destructive, partial success for bulk ops)
- [ ] Structured logging captures all operations with context
- [ ] No regressions in existing query tool functionality
- [ ] Manual testing confirms tool registration and end-to-end workflow

---

## NOTES

**Design Decisions:**
- Single tool pattern following Anthropic's "fewer, smarter tools" principle
- Operation parameter routing mirrors existing query tool pattern
- Destructive ops require explicit confirm_destructive=True
- Bulk ops use partial success (don't fail entire operation on single item failure)
- Frontmatter preserved when not explicitly updated (read→merge→write)
- Path validation prevents directory traversal via VaultManager._validate_path()

**Performance:** Single ops <50ms, bulk ops ~20-50ms per item (linear scaling)

**Future Enhancements:** Template support, find/replace, note merging, vault statistics, backup before destructive ops

**Confidence:** 9/10 for one-pass success. Friction points: frontmatter merging edge cases (minor), bulk error handling (clear pattern provided).
