---
description: Run all validation checks (linting, formatting, type checking, tests)
model: Haiku
---

# Validation Suite

Run comprehensive validation on the codebase including linting, formatting, type checking, and tests.

## Instructions: Run these commands in order and report back to the user

### 1. Ruff Linting Check

`uv run ruff check src/`

### 2. Ruff Formatting Check

`uv run ruff format --check src/`

### 3. Mypy Type Checking (Strict Mode)

`uv run mypy src/`

### 4. Unit Tests

`uv run pytest tests/ -m unit -v`

### 5. Integration Tests

start the server `uv run uvicorn src.main:app --host 0.0.0.0 --port 8030 --reload`
Then run `uv run pytest tests/ -m integration -v`

## Report Format

Provide a concise summary in this format:

```
🔍 Validation Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Ruff Linting: PASSED (0 issues)
✅ Ruff Formatting: PASSED
✅ Mypy Type Checking: PASSED
✅ Unit Tests: PASSED (X tests, Y.Ys)
✅ Integration Tests: PASSED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: ✅ ALL CHECKS PASSED
```

Or if issues found:

```
🔍 Validation Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ Ruff Linting: FAILED (12 issues)
✅ Ruff Formatting: PASSED
❌ Mypy Type Checking: FAILED (3 errors)
✅ Unit Tests: PASSED (X tests, Y.Ys)
X Integration Tests: FAILED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Issues Found: 15 total

Linting Issues (12):
- List of file name and line number amd issue description

Type Errors (3):
- List of file name and line number amd issue description

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: ❌ VALIDATION FAILED
```
