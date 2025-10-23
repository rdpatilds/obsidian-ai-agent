---
description: Auto-fix linting and formatting issues
model: Haiku
---

# Auto-Fix Code Issues

Automatically fix linting and formatting issues in the codebase.

## Execution

### 1. Current Status

!`uv run ruff check src/ | head -20`

### 2. Auto-Fix Linting Issues

!`uv run ruff check --fix src/`

### 3. Auto-Format Code

!`uv run ruff format src/`

### 4. Verify Fixes

!`uv run ruff check src/`

### 5. Type Check After Fixes

!`uv run mypy src/`

## Your Task

1. **Summarize what was fixed**:
   - Number of files modified
   - Types of issues resolved
   - Remaining issues (if any)

2. **Report remaining issues**:
   - Issues that require manual intervention
   - Type errors that need code changes
   - Suggestions for fixes

3. **Next steps**:
   - If all issues are resolved: suggest running `/validate` to confirm
   - If issues remain: provide specific guidance on how to fix them
   - Recommend reviewing the changes before committing

## Note

This command modifies your files. The fixes are safe (formatting and auto-fixable linting issues), but you should review the changes before committing.
