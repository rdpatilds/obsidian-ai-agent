# Implementation Plan: Obsidian Folder Manager Tool

## Feature Description

Add folder management capabilities to the Obsidian AI agent, enabling it to create, rename, move, delete, and list folders within the vault. This feature solves the problem that the agent can currently only manipulate individual notes but cannot organize the vault's folder structure itself.

**Problem Statement:**
Users need to organize their Obsidian vault's folder structure as their knowledge base grows. Currently, the agent can only work with notes (files) but cannot:
- Create project folders or nested folder structures
- Rename folders when project names change
- Move folders to reorganize vault structure
- Delete old/empty folders during cleanup
- List folder contents with statistics

This limitation forces users to manually manage folder structure, breaking the flow of AI-assisted knowledge management.

## User Story

**As an** Obsidian user managing a growing knowledge base
**I want** the AI agent to organize my vault's folder structure
**So that** I can maintain a clean, organized vault without manually moving folders and files

**Acceptance Scenarios:**

1. **Creating Project Structure**
   - User: "Create a folder structure for my new project: projects/2025/website-redesign"
   - Agent: Creates nested folders, confirms creation

2. **Renaming Folders (with wikilink updates)**
   - User: "Rename the 'alpha' project folder to 'website-redesign'"
   - Agent: Renames folder AND updates all wikilinks in vault that reference files in that folder

3. **Moving Folders to Archive**
   - User: "Move the completed-project folder to archive/2024"
   - Agent: Moves folder, updates wikilinks, confirms new location

4. **Cleaning Up Empty Folders**
   - User: "Delete empty folders in the drafts directory"
   - Agent: Lists empty folders, deletes with confirmation

5. **Browsing Folder Contents**
   - User: "Show me what's in the projects folder with note counts"
   - Agent: Returns paginated list with statistics (note count, size, modified date)

## Solution and Approach

### Selected Approach: **Option 1 - Standalone `obsidian_folder_manager` Tool**

**Why this approach:**

1. **Follows Existing Architecture Pattern**
   - Matches the vertical slice architecture used by all existing tools
   - Clean separation: `src/tools/obsidian_folder_manager/` with schemas, service, tool
   - Consistent with KISS/YAGNI principles in `CLAUDE.md`

2. **Clear Agent Mental Model**
   - Single-folder operations → `obsidian_folder_manager`
   - Batch-folder operations → `obsidian_vault_organizer` (extend existing)
   - No confusion about which tool to use

3. **Future-Proof and Maintainable**
   - Easy to add folder-specific features (templates, metadata)
   - Independent testing and evolution
   - Doesn't bloat existing tools with unrelated functionality

4. **Security by Design**
   - Reuses proven `validate_vault_path()` security infrastructure
   - Same `is_path_allowed()` blocking mechanism
   - Vault-scoped operations only (from `OBSIDIAN_VAULT_PATH` env var)

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Backlink Updates** | Forward wikilinks only | Simple - Obsidian handles backlinks automatically |
| **Atomic Rollback** | Best-effort, no rollback | Avoid overengineering - log errors, don't fail entire operation |
| **Copy Operation** | Not implemented | MOVE is sufficient - COPY is expensive and rarely needed |
| **LIST Pagination** | Yes, max 200/page | Prevent token explosion on large vaults |
| **Wikilink Updates** | Best-effort async | Don't block operation if wikilink scan fails |
| **Non-blocking I/O** | Use `aioshutil` | Prevent blocking event loop on large folder operations |
| **Symlink Support** | Follow symlinks | `.resolve()` canonicalizes paths, handles symlinks safely |

## Relevant Codebase Files

**The coding agent MUST read these files to understand patterns:**

### Core Architecture & Patterns
- `CLAUDE.md` - **CRITICAL**: Development standards, type safety, logging rules, agent tool docstring format
- `README.md` - Project overview, tool design philosophy, quick start
- `src/shared/config.py` - Settings management, env var loading, vault path configuration
- `src/shared/logging.py` - Structured logging setup (AI-optimized)
- `src/shared/vault_security.py` - **CRITICAL**: Path validation, directory traversal protection, blocked patterns

### Existing Tool Implementations (Follow These Patterns)
- `src/tools/obsidian_note_manager/schemas.py` - Pydantic schema patterns (operations enum, request/response)
- `src/tools/obsidian_note_manager/service.py` - Service layer patterns (async operations, error handling, security)
- `src/tools/obsidian_note_manager/tool.py` - **CRITICAL**: Agent tool docstring format, parameter handling
- `src/tools/obsidian_vault_organizer/service.py` - Batch operations, rollback pattern, `shutil.move()` usage
- `src/tools/obsidian_vault_organizer/schemas.py` - Batch operation schemas, validation

### Shared Utilities
- `src/shared/obsidian_parsers.py` - **CRITICAL**: Wikilink extraction, frontmatter parsing
- `src/shared/response_formatter.py` - Token-efficient response formatting (minimal/concise/detailed)
- `src/shared/middleware.py` - Request logging, correlation IDs
- `src/agent/schemas.py` - AgentDependencies (vault_path injection)
- `src/agent/agent.py` - Tool registration pattern

### Test Patterns
- `tests/tools/obsidian_note_manager/test_service.py` - Unit test patterns
- `tests/integration/test_consolidated_tools.py` - Integration test patterns
- `tests/shared/test_vault_security.py` - **CRITICAL**: Security test patterns
- `tests/conftest.py` - Test fixtures (tmp_vault, mock_settings)

## Implementation Plan

### Foundational Work

1. **Add `aioshutil` Dependency**
   - Add to `pyproject.toml` dependencies
   - Provides non-blocking `move()`, `rmtree()`, `copytree()` operations
   - Prevents event loop blocking on large folder operations

2. **Security Enhancements**
   - Add `validate_folder_name()` to `src/shared/vault_security.py`
   - Block Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
   - Block invalid characters (`<>:"|?*`, path separators `/\`)
   - Prevent operations on vault root and critical folders (`.obsidian`, `.git`)

3. **Wikilink Update Helper**
   - Implement `_update_wikilinks_for_folder_rename()` in service
   - Scan all `.md` files in vault for wikilinks
   - Replace `[[old-path/file]]` → `[[new-path/file]]` patterns
   - Use `extract_wikilinks()` from `obsidian_parsers.py`
   - Best-effort: log errors but don't fail operation

4. **Incoming Wikilink Check Helper**
   - Implement `_check_incoming_wikilinks()` in service
   - Find notes that link TO files in folder being deleted
   - Return list of affected note paths
   - Used for DELETE operation warnings

### Core Implementation

1. **Schemas (`src/tools/obsidian_folder_manager/schemas.py`)**
   ```python
   class FolderOperation(str, Enum):
       CREATE = "create"
       RENAME = "rename"
       MOVE = "move"
       DELETE = "delete"
       LIST = "list"

   class ManageFolderRequest(BaseModel):
       path: str
       operation: FolderOperation
       # CREATE
       create_parents: bool = True
       # RENAME
       new_name: str | None = None
       # MOVE
       destination: str | None = None
       # DELETE
       force: bool = False
       confirm_path: str | None = None
       check_wikilinks: bool = True
       # RENAME/MOVE
       update_wikilinks: bool = True
       # LIST
       recursive: bool = False
       include_stats: bool = True
       max_results: int = Field(default=50, ge=1, le=200)
       offset: int = Field(default=0, ge=0)
       # Common
       dry_run: bool = False
       response_format: ResponseFormat = ResponseFormat.CONCISE

   class FolderOperationResult(BaseModel):
       success: bool
       path: str
       operation: FolderOperation
       message: str
       new_path: str | None = None
       metadata: dict[str, Any] = Field(default_factory=dict)
       token_estimate: int = 50
   ```

2. **Service Layer (`src/tools/obsidian_folder_manager/service.py`)**
   - `manage_folder_service()` - Main entry point
   - `_create_folder()` - Create with optional parent creation
   - `_rename_folder()` - Rename + wikilink updates (best-effort)
   - `_move_folder()` - Move + wikilink updates, circular move detection
   - `_delete_folder()` - Delete with force flag, wikilink warnings
   - `_list_folder()` - List with pagination, stats, depth limit (5)
   - All operations use `validate_vault_path()` for security
   - All operations use `aioshutil` for non-blocking I/O
   - Comprehensive structured logging throughout

3. **Tool Registration (`src/tools/obsidian_folder_manager/tool.py`)**
   - `@agent.tool` decorator
   - `obsidian_folder_manage()` function
   - **CRITICAL**: Follow agent tool docstring format from `CLAUDE.md`
   - Include: "Use this when", "Do NOT use this for", Performance Notes, Examples
   - Parameter descriptions with token efficiency guidance
   - Error handling and validation

### Integration Work

1. **Configuration Updates (`src/shared/config.py`)**
   ```python
   # Add to Settings class
   enable_obsidian_folder_manager: bool = True
   max_folder_depth: int = 10  # For LIST recursive operation
   max_wikilink_scan_notes: int = 1000  # Safety limit for wikilink updates
   ```

2. **Agent Registration (`src/agent/agent.py`)**
   ```python
   if settings.enable_obsidian_folder_manager:
       from src.tools.obsidian_folder_manager.tool import register_obsidian_folder_manager_tool
       register_obsidian_folder_manager_tool(agent)
   ```

3. **System Prompt Update (`src/shared/config.py`)**
   - Add `obsidian_folder_manage` section to `agent_system_prompt`
   - Describe when to use vs other tools
   - Emphasize wikilink auto-update feature
   - Token efficiency guidance

4. **Environment Variables (`.env.example`)**
   ```bash
   ENABLE_OBSIDIAN_FOLDER_MANAGER=true
   MAX_FOLDER_DEPTH=10
   MAX_WIKILINK_SCAN_NOTES=1000
   ```

5. **Dependencies (`pyproject.toml`)**
   ```toml
   dependencies = [
       # ... existing ...
       "aioshutil>=1.3",
   ]
   ```

## Step-by-Step Task List

### Phase 1: Foundational Setup

- [ ] Add `aioshutil>=1.3` to `pyproject.toml` dependencies
- [ ] Run `uv sync` to install new dependency
- [ ] Add `validate_folder_name()` function to `src/shared/vault_security.py`
  - Block Windows reserved names (CON, PRN, AUX, NUL, COM1-9, LPT1-9)
  - Block invalid characters (`<>:"|?*`, `/`, `\`)
  - Block empty/whitespace-only names
  - Add comprehensive docstring
- [ ] Add unit tests for `validate_folder_name()` in `tests/shared/test_vault_security.py`

### Phase 2: Core Schema Definition

- [ ] Create `src/tools/obsidian_folder_manager/__init__.py` (empty file)
- [ ] Create `src/tools/obsidian_folder_manager/schemas.py`
  - Define `FolderOperation` enum with 5 operations
  - Define `ManageFolderRequest` with all parameters and validators
  - Define `FolderOperationResult` response model
  - Add comprehensive docstrings following Google style
  - Add `@model_validator` for operation-specific requirements
- [ ] Create `tests/tools/obsidian_folder_manager/__init__.py` (empty)
- [ ] Create `tests/tools/obsidian_folder_manager/test_schemas.py`
  - Test operation validation
  - Test required fields per operation
  - Test invalid operation combinations

### Phase 3: Service Layer Implementation

- [ ] Create `src/tools/obsidian_folder_manager/service.py`
- [ ] Implement `manage_folder_service()` - main entry point with security validation
- [ ] Implement `_create_folder()` operation
  - Use `aioshutil` for async directory creation
  - Handle `create_parents` flag
  - Check if folder exists (return success if directory)
  - Structured logging with duration, path info
- [ ] Implement `_rename_folder()` operation
  - Validate new_name with `validate_folder_name()`
  - Check destination doesn't exist
  - Handle case-only renames (temp rename strategy)
  - Call `_update_wikilinks_for_folder_rename()` (best-effort)
  - Use `aioshutil.move()` for async operation
  - Return metadata with `links_updated` count
- [ ] Implement `_move_folder()` operation
  - Validate destination with `validate_vault_path()`
  - Detect circular moves (moving folder into itself)
  - Create destination parent dirs if needed
  - Call `_update_wikilinks_for_folder_rename()` (best-effort)
  - Use `aioshutil.move()` for async operation
- [ ] Implement `_delete_folder()` operation
  - Require `confirm_path` matches `path` (safety)
  - Check if folder is empty (if `force=False`)
  - Call `_check_incoming_wikilinks()` if `check_wikilinks=True`
  - Return warning metadata if notes would have broken links
  - Use `aioshutil.rmtree()` for async recursive deletion
  - Comprehensive logging with deletion count, affected notes
- [ ] Implement `_list_folder()` operation
  - Collect folders (recursive or immediate children)
  - Limit recursive depth to 5 levels
  - Filter with `is_path_allowed()` to exclude blocked dirs
  - Calculate stats if `include_stats=True` (note count, size, modified date)
  - Apply pagination (offset, max_results)
  - Return metadata with `has_more`, `total_folders`, `returned`
  - Token estimate based on response_format
- [ ] Implement `_update_wikilinks_for_folder_rename()` helper
  - Scan all `.md` files in vault with `vault_root.rglob("*.md")`
  - Use `extract_wikilinks()` from `obsidian_parsers.py`
  - Replace `[[old-folder-path/...]]` → `[[new-folder-path/...]]` patterns
  - Use `aiofiles` for async file I/O
  - Limit to `max_wikilink_scan_notes` from settings (default: 1000)
  - Best-effort: catch and log errors, don't raise
  - Return count of notes updated
- [ ] Implement `_check_incoming_wikilinks()` helper
  - Scan all `.md` files NOT in folder being deleted
  - Find wikilinks that reference files in target folder
  - Return list of note paths with links
  - Used for DELETE operation warnings
- [ ] Add comprehensive structured logging to all functions
  - Use `get_logger(__name__)` pattern
  - Log operation start/completion with duration_ms
  - Log warnings for wikilink failures
  - Log security violations with path details

### Phase 4: Tool Registration

- [ ] Create `src/tools/obsidian_folder_manager/tool.py`
- [ ] Implement `register_obsidian_folder_manager_tool(agent)`
- [ ] Define `@agent.tool async def obsidian_folder_manage()` with all parameters
- [ ] **CRITICAL**: Write comprehensive tool docstring following `CLAUDE.md` format
  - One-line summary
  - "Use this when you need to:" (5+ specific scenarios)
  - "Do NOT use this for:" (3+ redirect scenarios to other tools)
  - Args section with parameter guidance (WHY to use different values)
  - Returns section with format details
  - Performance Notes section (token estimates, execution time, limits)
  - Examples section (5+ realistic examples with actual paths)
- [ ] Implement parameter parsing and validation
  - Parse operation string to FolderOperation enum
  - Validate operation-specific requirements
  - Create ManageFolderRequest with all parameters
- [ ] Call `manage_folder_service()` with vault_path from `ctx.deps.vault_path`
- [ ] Format response output for agent consumption
  - Include success/failure status
  - Show operation details
  - Display metadata (links updated, affected notes, pagination info)
  - Add token estimate to output
- [ ] Add error handling with helpful messages
  - FileNotFoundError → "Folder not found: {path}"
  - SecurityError → "Path not allowed: {path}"
  - ValueError → "Invalid operation: {details}"
- [ ] Add structured logging for tool execution

### Phase 5: Configuration & Integration

- [ ] Update `src/shared/config.py`
  - Add `enable_obsidian_folder_manager: bool = True`
  - Add `max_folder_depth: int = 10`
  - Add `max_wikilink_scan_notes: int = 1000`
  - Add docstrings for new settings
- [ ] Update `src/agent/agent.py`
  - Import `register_obsidian_folder_manager_tool`
  - Add conditional registration based on `enable_obsidian_folder_manager`
  - Add structured logging for tool registration
- [ ] Update `src/shared/config.py` agent_system_prompt
  - Add "## 4. obsidian_folder_manage" section
  - Describe when to use (folder operations)
  - Describe when NOT to use (note operations, batch operations)
  - Emphasize wikilink auto-update on RENAME/MOVE
  - Add token efficiency guidance
- [ ] Update `.env.example`
  - Add `ENABLE_OBSIDIAN_FOLDER_MANAGER=true`
  - Add `MAX_FOLDER_DEPTH=10`
  - Add `MAX_WIKILINK_SCAN_NOTES=1000`
  - Add comments explaining each setting

### Phase 6: Comprehensive Testing

#### Unit Tests

- [ ] Create `tests/tools/obsidian_folder_manager/test_service.py`
  - Test `_create_folder()` operation
    - Success: create simple folder
    - Success: create nested folder with `create_parents=True`
    - Error: parent doesn't exist with `create_parents=False`
    - Success: folder already exists (idempotent)
    - Error: path exists as file
    - Edge: empty folder name rejected
    - Edge: Windows reserved names rejected
  - Test `_rename_folder()` operation
    - Success: simple rename
    - Success: case-only rename (Projects → projects)
    - Success: rename with wikilink updates
    - Error: folder doesn't exist
    - Error: destination already exists
    - Error: invalid new_name (reserved, invalid chars)
    - Verify wikilinks updated in notes
  - Test `_move_folder()` operation
    - Success: move to existing destination
    - Success: move with destination creation
    - Success: move with wikilink updates
    - Error: circular move (projects → projects/subfolder)
    - Error: destination folder with same name exists
    - Verify wikilinks updated in notes
  - Test `_delete_folder()` operation
    - Success: delete empty folder
    - Success: delete non-empty folder with `force=True`
    - Error: delete non-empty folder with `force=False`
    - Error: missing confirmation
    - Error: folder doesn't exist
    - Verify wikilink check warnings
  - Test `_list_folder()` operation
    - Success: list immediate children
    - Success: list recursive with depth limit
    - Success: list with stats (note count, size, modified)
    - Success: pagination (offset, max_results)
    - Success: empty folder returns empty list
    - Verify blocked folders excluded (.obsidian, .git)
    - Verify pagination metadata correct (has_more, total_folders)
  - Test wikilink helpers
    - `_update_wikilinks_for_folder_rename()` updates all references
    - `_check_incoming_wikilinks()` finds all linking notes
  - Test security validation
    - Path traversal blocked (../..)
    - Absolute paths blocked (/etc/passwd)
    - Blocked directories rejected (.obsidian, .git)
  - Test dry_run mode for all operations

- [ ] Create `tests/tools/obsidian_folder_manager/test_tool.py`
  - Test parameter validation
  - Test operation enum parsing
  - Test response formatting
  - Test error messages

#### Integration Tests

- [ ] Create `tests/integration/test_folder_operations.py`
  - Test complete workflow: create → rename → move → delete
  - Test wikilink updates end-to-end
    - Create folder with notes
    - Create notes that link to folder contents
    - Rename folder
    - Verify all wikilinks updated correctly
  - Test pagination with large folder structures
  - Test cross-tool workflow (vault_query → folder_manage)

#### Security Tests

- [ ] Add to `tests/shared/test_vault_security.py`
  - Test `validate_folder_name()` with all edge cases
  - Test Windows reserved names on all platforms
  - Test invalid characters rejected
  - Test symlink resolution security

#### Platform-Specific Tests

- [ ] Test Windows-specific concerns
  - Reserved folder names (CON, PRN, etc.)
  - Path length limits (260 chars)
  - Case-insensitive filesystem behavior
- [ ] Test Unix-specific concerns
  - Case-sensitive filesystem behavior
  - Symlink following

### Phase 7: Documentation

- [ ] Update `README.md`
  - Add `obsidian_folder_manage` to Core Tools section
  - Add usage examples with realistic paths
  - Update token efficiency table with folder operations
  - Add to Quick Start examples
- [ ] Update `CLAUDE.md` if needed
  - Verify folder tool follows all guidelines
  - Add any folder-specific patterns to guidelines
- [ ] Add inline code documentation
  - Comprehensive docstrings for all functions
  - Type hints for all parameters and returns
  - Usage examples in docstrings

### Phase 8: Validation & Quality Checks

- [ ] Run linting: `uv run ruff check src/`
- [ ] Fix linting issues: `uv run ruff check --fix src/`
- [ ] Run type checking: `uv run mypy src/`
- [ ] Fix type errors
- [ ] Run all tests: `uv run pytest tests/ -v`
- [ ] Run unit tests only: `uv run pytest tests/ -m unit -v`
- [ ] Run integration tests: `uv run pytest tests/ -m integration -v`
- [ ] Verify test coverage for new module
- [ ] Test E2E with curl (see Validation section)

## Testing Strategy

### Unit Tests (`tests/tools/obsidian_folder_manager/`)

**Scope:** Test individual service functions in isolation with mock vault

**Coverage Requirements:**
- All 5 operations (CREATE, RENAME, MOVE, DELETE, LIST)
- All parameters and edge cases
- Security validation
- Error handling
- Wikilink helpers

**Test Fixtures:**
```python
@pytest.fixture
def tmp_vault(tmp_path):
    """Create temporary vault for testing."""
    vault = tmp_path / "vault"
    vault.mkdir()
    return vault

@pytest.fixture
def vault_with_structure(tmp_vault):
    """Create vault with folder structure and notes."""
    (tmp_vault / "projects/alpha").mkdir(parents=True)
    (tmp_vault / "projects/alpha/spec.md").write_text("# Spec")
    (tmp_vault / "index.md").write_text("See [[projects/alpha/spec]]")
    return tmp_vault
```

**Test Categories:**
1. **Happy Path Tests** - Normal operations succeed
2. **Error Path Tests** - Invalid inputs rejected with clear errors
3. **Edge Case Tests** - Boundary conditions (empty folders, max depth, pagination)
4. **Security Tests** - Malicious inputs blocked
5. **Idempotency Tests** - Repeated operations safe

### Integration Tests (`tests/integration/`)

**Scope:** Test multiple components working together

**Key Scenarios:**
1. **Folder Lifecycle Workflow**
   - Create folder → Add notes → Rename folder → Verify wikilinks updated → Move folder → Delete folder

2. **Wikilink Update Chain**
   - Create folder structure with cross-references
   - Rename root folder
   - Verify ALL nested wikilinks updated

3. **Cross-Tool Integration**
   - Use `obsidian_vault_query` to find folders
   - Use `obsidian_folder_manage` to organize results
   - Verify consistency

4. **Pagination with Large Structures**
   - Create 200+ subfolders
   - Test pagination (offset, max_results)
   - Verify has_more flag accuracy

### End-to-End Tests (Manual Validation)

**Scope:** Test through OpenAI-compatible API with curl

**Test Scenarios:**
1. **Agent-Driven Folder Creation**
   ```bash
   curl -X POST http://localhost:8030/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-4o-mini",
       "messages": [{
         "role": "user",
         "content": "Create a folder structure for a new project: projects/2025/ai-research"
       }]
     }'
   ```

2. **Agent-Driven Rename with Wikilink Update**
   ```bash
   curl -X POST http://localhost:8030/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-4o-mini",
       "messages": [{
         "role": "user",
         "content": "Rename the alpha project folder to website-redesign"
       }]
     }'
   ```

3. **Agent-Driven Folder Listing**
   ```bash
   curl -X POST http://localhost:8030/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-4o-mini",
       "messages": [{
         "role": "user",
         "content": "Show me all folders in projects with note counts"
       }]
     }'
   ```

## Edge Cases for Testing

### Security Edge Cases
- [ ] **Directory Traversal**: `../../../etc` - Should be blocked by `validate_vault_path()`
- [ ] **Absolute Paths**: `/etc/passwd` - Should be blocked
- [ ] **Symlink Escape**: Symlink pointing outside vault - Resolved then blocked
- [ ] **Vault Root Operation**: Operating on vault root itself - Should be blocked
- [ ] **Critical Folder Operations**: Renaming/deleting `.obsidian`, `.git` - Should be blocked
- [ ] **Empty Vault Path**: `OBSIDIAN_VAULT_PATH` not set - Should return error

### Filesystem Edge Cases
- [ ] **Windows Reserved Names**: CON, PRN, AUX, NUL, COM1-9, LPT1-9 - Should be rejected
- [ ] **Invalid Characters**: `<>:"|?*` in folder names - Should be rejected
- [ ] **Path Separators**: `/` or `\` in folder names - Should be rejected
- [ ] **Empty Folder Name**: "" or "   " - Should be rejected
- [ ] **Case-Only Rename**: `Projects` → `projects` - Should use temp rename strategy
- [ ] **Very Long Paths**: > 260 chars on Windows - Should warn (if detectable)
- [ ] **Unicode Names**: Folders with emoji/unicode - Should work correctly
- [ ] **Whitespace Names**: Leading/trailing spaces - Should be trimmed or rejected

### Operation Edge Cases
- [ ] **CREATE**: Folder already exists - Should return success (idempotent)
- [ ] **CREATE**: Path is file not folder - Should return error
- [ ] **CREATE**: Missing parents with `create_parents=False` - Should return error
- [ ] **RENAME**: Folder doesn't exist - Should return error
- [ ] **RENAME**: Destination already exists - Should return error
- [ ] **RENAME**: Folder contains 1000+ notes - Should limit wikilink scan, log warning
- [ ] **MOVE**: Circular move (projects → projects/archive) - Should detect and reject
- [ ] **MOVE**: Destination same as source - Should return error or no-op
- [ ] **DELETE**: Non-empty folder with `force=False` - Should return error with count
- [ ] **DELETE**: Missing confirmation - Should return error with instruction
- [ ] **DELETE**: Folder has incoming wikilinks - Should warn with affected note list
- [ ] **LIST**: Empty folder - Should return empty list with message
- [ ] **LIST**: Recursive depth > 10 - Should limit to 5 levels (safety)
- [ ] **LIST**: Pagination beyond results - Should return empty with `has_more=false`

### Wikilink Edge Cases
- [ ] **No Wikilinks**: Rename folder with no references - Should complete quickly
- [ ] **Nested Wikilinks**: `[[folder/subfolder/file]]` - Should update all levels
- [ ] **Wikilink with Heading**: `[[folder/file#heading]]` - Should preserve heading
- [ ] **Wikilink with Alias**: `[[folder/file|Alias]]` - Should preserve alias
- [ ] **Embed Links**: `![[folder/file]]` - Should update embeds too
- [ ] **Partial Match**: Folder `alpha` and `alpha-2` exist - Should only update exact matches
- [ ] **Large Vault**: 10,000+ notes - Should respect `max_wikilink_scan_notes` limit

### Concurrency Edge Cases
- [ ] **Simultaneous Operations**: Two agents rename same folder - Second should error
- [ ] **File Locks**: Obsidian has folder open (Windows) - Should catch PermissionError
- [ ] **Async I/O**: Large folder move doesn't block other requests - aioshutil handles this

## Acceptance Criteria

### Functional Requirements
- [ ] ✅ **CREATE operation works**
  - Can create single folder
  - Can create nested folders with `create_parents=True`
  - Returns success if folder already exists (idempotent)
  - Rejects invalid folder names (reserved, invalid chars)

- [ ] ✅ **RENAME operation works**
  - Can rename folders with valid names
  - Updates ALL wikilinks in vault that reference folder contents
  - Handles case-only renames correctly
  - Returns count of notes with updated wikilinks
  - Fails gracefully if destination exists

- [ ] ✅ **MOVE operation works**
  - Can move folders to new locations
  - Creates destination parent folders if needed
  - Updates wikilinks from old path to new path
  - Detects and rejects circular moves
  - Uses `aioshutil` for non-blocking I/O

- [ ] ✅ **DELETE operation works**
  - Can delete empty folders
  - Can delete non-empty folders with `force=True`
  - Requires `confirm_path` matching `path` for safety
  - Warns about broken wikilinks if `check_wikilinks=True`
  - Returns list of notes that would have broken links

- [ ] ✅ **LIST operation works**
  - Lists immediate children or recursive (depth limit 5)
  - Includes statistics (note count, size, modified date) when requested
  - Supports pagination (offset, max_results up to 200)
  - Returns metadata with `has_more`, `total_folders`, `returned`
  - Excludes blocked directories (.obsidian, .git, .trash)

### Non-Functional Requirements
- [ ] ✅ **Security enforced**
  - All operations use `validate_vault_path()` to prevent directory traversal
  - Operations restricted to `OBSIDIAN_VAULT_PATH` from env var
  - Blocked directories cannot be accessed (.obsidian, .git, .trash, node_modules)
  - Symlinks are resolved and boundary-checked
  - Critical folders (vault root, .obsidian, .git) cannot be renamed/deleted

- [ ] ✅ **Type safety maintained**
  - All functions have complete type annotations
  - Mypy passes with strict configuration
  - No `Any` types without justification
  - Pydantic models validate all inputs

- [ ] ✅ **Logging comprehensive**
  - Structured logging for all operations (start, completion, errors)
  - Duration tracking (duration_ms) for performance monitoring
  - Wikilink update results logged (count, errors)
  - Security violations logged with path details
  - Follows AI-optimized logging patterns from `CLAUDE.md`

- [ ] ✅ **Token efficiency**
  - LIST operation respects response_format (minimal/concise/detailed)
  - Pagination prevents token explosion on large folders
  - Token estimates included in responses
  - Wikilink scans limited to `max_wikilink_scan_notes` setting

- [ ] ✅ **Agent usability**
  - Tool docstring follows `CLAUDE.md` format exactly
  - "Use this when" guidance clear and specific
  - "Do NOT use this for" redirects to appropriate tools
  - Performance notes document token costs
  - Examples use realistic paths and scenarios
  - Error messages actionable and clear

### Quality Requirements
- [ ] ✅ **Tests pass**
  - All unit tests pass (60+ tests expected)
  - All integration tests pass
  - Security tests pass
  - Platform-specific tests pass (where applicable)
  - Test coverage > 90% for new module

- [ ] ✅ **Linting passes**
  - `ruff check src/` passes with no errors
  - `mypy src/` passes with no errors
  - Code follows CLAUDE.md style guidelines

- [ ] ✅ **Documentation complete**
  - README.md updated with folder manager examples
  - .env.example updated with new settings
  - All functions have Google-style docstrings
  - Inline comments explain complex logic
  - System prompt updated with tool guidance

## Validation

### Pre-Deployment Validation Commands

**1. Dependency Installation**
```bash
# Install new dependencies
uv sync

# Verify aioshutil installed
uv pip list | grep aioshutil
```

**2. Linting & Type Checking**
```bash
# Check code style
uv run ruff check src/

# Auto-fix style issues
uv run ruff check --fix src/

# Type checking (strict mode)
uv run mypy src/

# Verify no errors in new module specifically
uv run mypy src/tools/obsidian_folder_manager/
```

**3. Unit Tests**
```bash
# Run all unit tests
uv run pytest tests/ -m unit -v

# Run folder manager tests specifically
uv run pytest tests/tools/obsidian_folder_manager/ -v

# Run with coverage
uv run pytest tests/tools/obsidian_folder_manager/ --cov=src/tools/obsidian_folder_manager --cov-report=term-missing
```

**4. Integration Tests**
```bash
# Run all integration tests
uv run pytest tests/ -m integration -v

# Run folder operations integration tests
uv run pytest tests/integration/test_folder_operations.py -v
```

**5. Security Tests**
```bash
# Run security-specific tests
uv run pytest tests/shared/test_vault_security.py -v -k folder

# Run all tests with security edge cases
uv run pytest tests/ -v -k "security or traversal or blocked"
```

**6. Full Test Suite**
```bash
# Run ALL tests (unit + integration)
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ --cov=src --cov-report=html
```

### End-to-End Validation (Server Running)

**Start Server:**
```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8030 --reload
```

**Health Check:**
```bash
# Verify server running
curl http://localhost:8030/health

# Expected output:
# {"status":"healthy","environment":"development"}
```

**E2E Test 1: Create Folder**
```bash
curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": "Create a folder called test-projects/2025/new-feature"
    }]
  }' | jq .

# Expected: Agent uses obsidian_folder_manage tool to create nested folder
# Verify: Check vault for folder creation
```

**E2E Test 2: List Folders**
```bash
curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": "List all folders in the vault with note counts"
    }]
  }' | jq .

# Expected: Agent uses obsidian_folder_manage with LIST operation
# Verify: Response includes folder list with statistics
```

**E2E Test 3: Rename with Wikilink Update**
```bash
# Setup: Create test folder and notes first
# Then rename:
curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": "Rename test-projects to archive-projects"
    }]
  }' | jq .

# Expected: Agent renames folder and reports wikilink updates
# Verify: Check vault for renamed folder and updated wikilinks in notes
```

**E2E Test 4: Security - Directory Traversal**
```bash
curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": "Create a folder at ../../../etc/malicious"
    }]
  }' | jq .

# Expected: Agent attempts operation, tool returns security error
# Verify: Folder NOT created outside vault, error logged
```

**E2E Test 5: Delete with Wikilink Check**
```bash
curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": "Delete the old-projects folder"
    }]
  }' | jq .

# Expected: Agent shows confirmation required, warns about broken links if any
# Verify: Folder still exists (confirmation not provided), warnings shown
```

### Regression Testing

**Verify Existing Tools Still Work:**
```bash
# Test obsidian_note_manage still works
curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": "Create a note at test.md with content Hello World"
    }]
  }' | jq .

# Test obsidian_vault_query still works
curl -X POST http://localhost:8030/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-key-change-in-production" \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [{
      "role": "user",
      "content": "Find all notes tagged project"
    }]
  }' | jq .

# Expected: All existing tools continue to work without issues
```

### Success Criteria Checklist

Run this checklist before considering the feature complete:

```bash
# 1. Dependencies installed
✓ uv pip list | grep aioshutil

# 2. Linting passes
✓ uv run ruff check src/
✓ uv run mypy src/

# 3. All tests pass
✓ uv run pytest tests/ -v --tb=short

# 4. New module has tests
✓ test -f tests/tools/obsidian_folder_manager/test_service.py
✓ test -f tests/tools/obsidian_folder_manager/test_tool.py
✓ test -f tests/integration/test_folder_operations.py

# 5. Configuration updated
✓ grep -q "enable_obsidian_folder_manager" src/shared/config.py
✓ grep -q "ENABLE_OBSIDIAN_FOLDER_MANAGER" .env.example

# 6. Agent registration present
✓ grep -q "register_obsidian_folder_manager_tool" src/agent/agent.py

# 7. Documentation updated
✓ grep -q "obsidian_folder_manage" README.md

# 8. Server starts without errors
✓ uv run uvicorn src.main:app --host 0.0.0.0 --port 8030 &
✓ sleep 5 && curl http://localhost:8030/health

# 9. E2E tests pass (manual verification)
✓ Test folder creation via API
✓ Test folder listing via API
✓ Test security blocks traversal

# 10. No regressions (existing tools work)
✓ Test note_manage via API
✓ Test vault_query via API
```

**If all checkmarks pass, feature is complete and ready for deployment.**
