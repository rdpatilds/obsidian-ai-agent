# Fix Issue #$ISSUE_NUMBER: $ISSUE_TITLE

## Issue Description

$ISSUE_BODY

## Your Task

You are Codex, an AI coding assistant. Your job is to **plan and implement the fix for this issue**.

**STEP 1: Create Implementation Plan**

Create a plan document at `.agents/plans/<descriptive-name>.md` that includes:
- Brief analysis of what needs to be changed
- List of specific files to modify
- Key changes to make in each file
- Expected outcome

Keep the plan focused and actionable (not a novel - aim for 20-50 lines).

**STEP 2: Implement the Changes**

Based on your plan:
1. **Read the relevant files** that need to be changed
2. **Make the actual changes** to those files
3. **Keep changes focused** - only change what's needed
4. **Follow project conventions** documented in CLAUDE.md

## For This Specific Issue

The issue is about making the README more concise. You should:

1. Create `.agents/plans/make-readme-concise.md` with your plan
2. Read the current `README.md` file
3. Make it more concise and scannable while keeping essential information
4. Actually edit and save the `README.md` file with your changes

**IMPORTANT:**
- Actually modify files (don't just describe changes)
- Save all your changes
- Create BOTH the plan and the actual README changes

## Expected Output

You should create/modify these files:
- `.agents/plans/<name>.md` - Your implementation plan
- `README.md` - The actual changes
