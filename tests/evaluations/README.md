# Evaluation Framework for Consolidated Obsidian Tools

This directory contains the evaluation framework for measuring and optimizing the performance of the 4 consolidated Obsidian tools.

## Overview

The evaluation suite consists of **30 tasks** divided into:
- **Training set**: 20 tasks for baseline measurement and optimization
- **Test set**: 10 tasks (held-out) for validation

### Task Categories
- **Simple operations** (6 tasks): Basic read/write/search
- **Search tasks** (6 tasks): Query vault with different modes
- **Graph analysis** (6 tasks): Knowledge graph navigation
- **Batch operations** (6 tasks): Organize multiple notes at once
- **Multi-tool workflows** (6 tasks): Complex tasks requiring tool composition

## Files

- `workflow_tasks.py` - Task definitions (30 tasks)
- `eval_runner.py` - Evaluation harness and metrics collection
- `analyze_transcripts.py` - Claude Code analysis helper
- `run_evaluation.py` - **Standalone evaluation runner (use this!)**
- `test_consolidated_tools_eval.py` - Pytest wrapper (optional)

---

## Quick Start

### Prerequisites

1. **Valid API Key**: Set in `.env` file or environment
   ```bash
   # For OpenAI
   OPENAI_API_KEY=sk-...

   # For OpenRouter
   OPENROUTER_API_KEY=...
   ```

2. **Model Configuration**: Check `src/shared/config.py`
   ```python
   model_name="openai:gpt-4o-mini"  # or your preferred model
   ```

### Run Evaluation

**Option 1: Full Evaluation (Recommended for initial baseline)**
```bash
python tests/evaluations/run_evaluation.py --full
```

**Option 2: Training Set Only**
```bash
python tests/evaluations/run_evaluation.py --training
```

**Option 3: Test Set Only (after optimization)**
```bash
python tests/evaluations/run_evaluation.py --test
```

**Custom output directory:**
```bash
python tests/evaluations/run_evaluation.py --full --output ./my_eval_results
```

---

## Evaluation Process

### 1. Run Baseline Evaluation

```bash
# Run full suite to establish baseline
python tests/evaluations/run_evaluation.py --full --output ./baseline_eval

# This creates:
# ./baseline_eval/
# ├── eval_vault/          # Test vault with sample data
# └── full_evaluation_TIMESTAMP.json  # Detailed results
```

### 2. Review Results

The JSON report contains:
- `success_rate`: Percentage of tasks that passed
- `avg_tool_calls`: Average number of tool invocations per task
- `avg_tokens`: Average tokens used per task
- `tool_usage_frequency`: Which tools were used how often
- `category_performance`: Metrics broken down by task category
- `task_results`: Individual task outcomes with transcripts

**Example report structure:**
```json
{
  "total_tasks": 30,
  "successful_tasks": 27,
  "failed_tasks": 3,
  "success_rate": 0.9,
  "avg_tool_calls": 2.5,
  "avg_tokens": 1200,
  "tool_usage_frequency": {
    "obsidian_vault_query": 15,
    "obsidian_note_manage": 10,
    "obsidian_vault_organize": 8,
    "obsidian_graph_analyze": 7
  },
  "category_performance": {
    "simple": {"total": 6, "success": 6, "avg_tokens": 800, "avg_tool_calls": 1.5},
    "search": {"total": 6, "success": 6, "avg_tokens": 900, "avg_tool_calls": 2.0},
    "graph": {"total": 6, "success": 5, "avg_tokens": 1500, "avg_tool_calls": 2.5},
    "batch": {"total": 6, "success": 5, "avg_tokens": 1100, "avg_tool_calls": 2.8},
    "multi": {"total": 6, "success": 5, "avg_tokens": 1800, "avg_tool_calls": 3.5}
  },
  "task_results": [
    {
      "task_prompt": "Read the project-alpha note and tell me the status",
      "category": "simple",
      "success": true,
      "tool_calls": [
        {"tool": "obsidian_note_manage", "args": {"path": "projects/project-alpha.md", ...}}
      ],
      "token_usage": {"prompt_tokens": 450, "completion_tokens": 150, "total_tokens": 600},
      "duration_ms": 1245.5,
      "agent_response": "The project-alpha note shows status: in-progress..."
    },
    // ... 29 more tasks
  ]
}
```

### 3. Analyze with Claude Code

Use the `analyze_transcripts.py` helper to get Claude's recommendations:

```bash
# Copy a sample task result to analyze
python tests/evaluations/analyze_transcripts.py ./baseline_eval/full_evaluation_*.json
```

Or manually feed to Claude Code:
```
I ran an evaluation of my 4 consolidated Obsidian tools. Here are the results:

[paste JSON report]

Please analyze:
1. Which tools are being misused or confused?
2. Where does token waste occur?
3. Which tool descriptions need clarification?
4. Opportunities for further consolidation?
5. Specific improvements to tool descriptions

Suggest specific edits to tool docstrings.
```

### 4. Implement Improvements

Based on Claude's analysis, update tool docstrings in:
- `src/tools/obsidian_note_manager/tool.py`
- `src/tools/obsidian_vault_query/tool.py`
- `src/tools/obsidian_graph_analyzer/tool.py`
- `src/tools/obsidian_vault_organizer/tool.py`

### 5. Re-Run Evaluation

```bash
# Run on held-out test set to validate improvements
python tests/evaluations/run_evaluation.py --test --output ./optimized_eval
```

### 6. Compare Results

```bash
# Compare baseline vs optimized
diff ./baseline_eval/full_evaluation_*.json ./optimized_eval/test_evaluation_*.json
```

Look for improvements in:
- ✅ Success rate increased
- ✅ Avg tool calls decreased
- ✅ Avg tokens decreased
- ✅ Specific category improvements

---

## Target Metrics (from PRD)

| Metric | Target | Baseline | Optimized | Status |
|--------|--------|----------|-----------|--------|
| **Success Rate** | >90% | _TBD_ | _TBD_ | ⏳ |
| **Avg Tool Calls** | <3 | _TBD_ | _TBD_ | ⏳ |
| **Avg Tokens** | <1500 | _TBD_ | _TBD_ | ⏳ |

---

## Using Pytest (Alternative Method)

If you prefer pytest:

```bash
# Check infrastructure
uv run pytest tests/evaluations/test_consolidated_tools_eval.py::test_evaluation_infrastructure -v

# Note: The actual evaluation tests are marked with @pytest.mark.skip
# because they require live API keys. To run them, remove the skip decorator
# and provide valid API keys.
```

---

## Troubleshooting

### "No API key found"
Make sure you have a valid API key in `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
# OR
OPENROUTER_API_KEY=sk-or-...
```

### "Tasks are failing unexpectedly"
1. Check that the evaluation vault was created correctly
2. Verify tools are enabled in settings
3. Check tool logs for errors
4. Try running a single simple task manually

### "Token count seems wrong"
Token counts are estimated (word count * 1.3). For accurate counts:
- Use actual API response metrics if available
- Modify `eval_runner.py` to extract real token usage from API

### "Evaluation is slow"
- Normal: ~30-60 seconds per task depending on model
- Full suite (30 tasks): 15-30 minutes
- Consider running training set only initially

---

## Advanced Usage

### Custom Task Sets

Create your own tasks in `workflow_tasks.py`:

```python
from tests.evaluations.workflow_tasks import EvalTask

CUSTOM_TASKS = [
    EvalTask(
        prompt="Your custom prompt here",
        expected_tools=["obsidian_note_manage"],
        max_tool_calls=2,
        max_tokens=1000,
        verifier=lambda result: "expected word" in result.lower(),
        category="custom",
    ),
]
```

Then modify `run_evaluation.py` to use `CUSTOM_TASKS`.

### Collect Detailed Transcripts

For deep analysis, capture full conversation history:

```python
# In eval_runner.py, add to TaskResult:
full_transcript: list[dict] = []  # All messages with timestamps

# During evaluation, save all messages
if hasattr(result, "all_messages"):
    for msg in result.all_messages():
        full_transcript.append({
            "role": msg.role,
            "content": str(msg.content),
            "timestamp": time.time()
        })
```

### A/B Testing Tool Versions

```bash
# Baseline with current tools
git checkout main
python tests/evaluations/run_evaluation.py --training --output ./baseline

# Test with modified tools
git checkout feature/improved-docstrings
python tests/evaluations/run_evaluation.py --training --output ./improved

# Compare
python tests/evaluations/compare_results.py ./baseline ./improved
```

---

## Continuous Improvement Cycle

1. **Baseline** → Run full eval, save results
2. **Analyze** → Feed to Claude Code, get suggestions
3. **Improve** → Update tool descriptions
4. **Validate** → Run on held-out test set
5. **Measure** → Compare metrics
6. **Iterate** → Repeat until targets met

**Goal**: Achieve >90% success rate with <3 avg tool calls and <1500 avg tokens.

---

## Questions?

See also:
- `PRPs/features/obsidian-consolidated-tools.md` - Full PRD with evaluation strategy
- `src/tools/*/tool.py` - Tool implementations and docstrings
- `tests/integration/test_consolidated_workflows.py` - Multi-tool integration tests

---

**Status**: Evaluation framework ready. Run baseline evaluation to start optimization cycle.
