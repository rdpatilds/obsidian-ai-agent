---
description: Verify code is ready for commit (validate + git status)
model: Haiku
---

# Commit Readiness Check

Comprehensive pre-commit validation to ensure code quality before committing.

## Current Git Status

### Staged Changes

!`git diff --cached --stat`

### Unstaged Changes

!`git diff --stat`

### Untracked Files

!`git status --short | grep '^??'`

## Validation Checks

### 1. Linting

!`uv run ruff check src/`

### 2. Formatting

!`uv run ruff format --check src/`

### 3. Type Checking

!`uv run mypy src/`

### 4. Unit Tests

!`uv run pytest tests/ -m unit -v --tb=short`

## Your Task

1. **Commit Readiness Assessment**:

   ```
   ✅ READY TO COMMIT
   - All validation checks passed
   - Changes are staged
   - No unintended files included

   OR

   ❌ NOT READY
   - [List of blocking issues]
   - [Required actions]
   ```

2. **Review Staged Changes**:
   - Summarize what's being committed
   - Check for accidental inclusions (.env, secrets, temp files)
   - Verify all related changes are staged

3. **Pre-Commit Actions** (if needed):
   - Run `/fix` to auto-fix linting/formatting
   - Stage additional files if needed
   - Remove unwanted files from staging

4. **Suggest Commit Message**:
   - Based on the changes, suggest a descriptive commit message
   - Follow conventional commit format if applicable
   - Include scope and breaking changes if relevant

## Example Output

```
🔍 Commit Readiness: ❌ NOT READY

Issues:
- 3 linting errors in src/tools/folder_manager/service.py
- 1 type error in src/shared/vault_security.py
- Untracked file: .env (should not be committed)

Actions Required:
1. Run: /fix (to auto-fix linting)
2. Fix type error at vault_security.py:330
3. Add .env to .gitignore or remove it

Estimated time: 5 minutes
```

## Note

This command does NOT create a commit - it only validates readiness. Use git commands to commit after validation passes.
