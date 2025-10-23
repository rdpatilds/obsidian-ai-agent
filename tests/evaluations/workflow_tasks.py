"""Evaluation workflow tasks for Obsidian agent tools.

This module defines realistic workflow scenarios for evaluating agent performance
with consolidated tools. Tasks are split into training and test sets.
"""

from typing import Any, Callable


class EvalTask:
    """Represents a single evaluation task."""

    def __init__(
        self,
        prompt: str,
        expected_tools: list[str],
        max_tool_calls: int,
        max_tokens: int,
        verifier: Callable[[str], bool],
        category: str,
    ) -> None:
        """Initialize evaluation task.

        Args:
            prompt: User prompt to execute.
            expected_tools: List of tool names that should be used.
            max_tool_calls: Maximum number of tool calls for efficiency.
            max_tokens: Maximum tokens for efficiency.
            verifier: Function to verify the result is correct.
            category: Task category (simple, search, graph, batch, multi).
        """
        self.prompt = prompt
        self.expected_tools = expected_tools
        self.max_tool_calls = max_tool_calls
        self.max_tokens = max_tokens
        self.verifier = verifier
        self.category = category


# Simple Operations (6 tasks)
SIMPLE_TASKS = [
    EvalTask(
        prompt="Read the project-alpha note and tell me the status",
        expected_tools=["obsidian_note_manage"],
        max_tool_calls=1,
        max_tokens=300,
        verifier=lambda result: "status" in result.lower(),
        category="simple",
    ),
    EvalTask(
        prompt="Update the status in project-alpha to completed",
        expected_tools=["obsidian_note_manage"],
        max_tool_calls=2,
        max_tokens=500,
        verifier=lambda result: "completed" in result.lower()
        or "updated" in result.lower(),
        category="simple",
    ),
    EvalTask(
        prompt="Replace all occurrences of 'TODO' with 'DONE' in meeting-notes",
        expected_tools=["obsidian_note_manage"],
        max_tool_calls=2,
        max_tokens=400,
        verifier=lambda result: "replace" in result.lower() or "done" in result.lower(),
        category="simple",
    ),
    EvalTask(
        prompt="Append today's progress to the daily-log note",
        expected_tools=["obsidian_note_manage"],
        max_tool_calls=1,
        max_tokens=300,
        verifier=lambda result: "append" in result.lower()
        or "added" in result.lower(),
        category="simple",
    ),
    EvalTask(
        prompt="Check if the research-paper note exists and show me just the title and tags",
        expected_tools=["obsidian_note_manage"],
        max_tool_calls=1,
        max_tokens=200,
        verifier=lambda result: "title" in result.lower() or "tag" in result.lower(),
        category="simple",
    ),
    EvalTask(
        prompt="Delete the old-draft note (confirm: old-draft.md)",
        expected_tools=["obsidian_note_manage"],
        max_tool_calls=1,
        max_tokens=200,
        verifier=lambda result: "delete" in result.lower()
        or "removed" in result.lower(),
        category="simple",
    ),
]

# Complex Searches (6 tasks)
SEARCH_TASKS = [
    EvalTask(
        prompt="Find all notes tagged #review",
        expected_tools=["obsidian_vault_query"],
        max_tool_calls=1,
        max_tokens=800,
        verifier=lambda result: "review" in result.lower(),
        category="search",
    ),
    EvalTask(
        prompt="Find all high-priority tasks that are not completed",
        expected_tools=["obsidian_vault_query"],
        max_tool_calls=1,
        max_tokens=1000,
        verifier=lambda result: "priority" in result.lower(),
        category="search",
    ),
    EvalTask(
        prompt="Show me notes created this week that mention 'machine learning'",
        expected_tools=["obsidian_vault_query"],
        max_tool_calls=1,
        max_tokens=1000,
        verifier=lambda result: "machine learning" in result.lower()
        or "notes" in result.lower(),
        category="search",
    ),
    EvalTask(
        prompt="Search for all notes with status=active in their frontmatter",
        expected_tools=["obsidian_vault_query"],
        max_tool_calls=1,
        max_tokens=800,
        verifier=lambda result: "active" in result.lower()
        or "status" in result.lower(),
        category="search",
    ),
    EvalTask(
        prompt="Find notes containing 'API design' but only show titles",
        expected_tools=["obsidian_vault_query"],
        max_tool_calls=1,
        max_tokens=500,
        verifier=lambda result: "api" in result.lower() or "design" in result.lower(),
        category="search",
    ),
    EvalTask(
        prompt="List all notes tagged with both #project and #2025",
        expected_tools=["obsidian_vault_query"],
        max_tool_calls=1,
        max_tokens=800,
        verifier=lambda result: "project" in result.lower()
        or "2025" in result.lower(),
        category="search",
    ),
]

# Graph Analysis (6 tasks)
GRAPH_TASKS = [
    EvalTask(
        prompt="What notes are linked from the main-concept note?",
        expected_tools=["obsidian_graph_analyze"],
        max_tool_calls=1,
        max_tokens=800,
        verifier=lambda result: "link" in result.lower() or "note" in result.lower(),
        category="graph",
    ),
    EvalTask(
        prompt="Show me all notes within 2 hops of the project-overview note",
        expected_tools=["obsidian_graph_analyze"],
        max_tool_calls=1,
        max_tokens=1500,
        verifier=lambda result: "note" in result.lower() or "link" in result.lower(),
        category="graph",
    ),
    EvalTask(
        prompt="Find all notes that link TO the central-thesis note (backlinks)",
        expected_tools=["obsidian_graph_analyze"],
        max_tool_calls=1,
        max_tokens=800,
        verifier=lambda result: "link" in result.lower()
        or "central" in result.lower(),
        category="graph",
    ),
    EvalTask(
        prompt="Analyze the knowledge graph around 'AI research' note with minimal details",
        expected_tools=["obsidian_graph_analyze"],
        max_tool_calls=1,
        max_tokens=600,
        verifier=lambda result: "ai" in result.lower() or "research" in result.lower(),
        category="graph",
    ),
    EvalTask(
        prompt="Show me the immediate neighbors of the system-architecture note",
        expected_tools=["obsidian_graph_analyze"],
        max_tool_calls=1,
        max_tokens=700,
        verifier=lambda result: "neighbor" in result.lower()
        or "note" in result.lower(),
        category="graph",
    ),
    EvalTask(
        prompt="What's the connection between note-a and note-b in the graph?",
        expected_tools=["obsidian_graph_analyze"],
        max_tool_calls=2,
        max_tokens=1000,
        verifier=lambda result: "link" in result.lower()
        or "connection" in result.lower(),
        category="graph",
    ),
]

# Batch Operations (6 tasks)
BATCH_TASKS = [
    EvalTask(
        prompt="Move all notes in the drafts folder to archive",
        expected_tools=["obsidian_vault_query", "obsidian_vault_organize"],
        max_tool_calls=2,
        max_tokens=1000,
        verifier=lambda result: "move" in result.lower()
        or "archive" in result.lower(),
        category="batch",
    ),
    EvalTask(
        prompt="Tag all project notes with #project-2025",
        expected_tools=["obsidian_vault_query", "obsidian_vault_organize"],
        max_tool_calls=2,
        max_tokens=1000,
        verifier=lambda result: "tag" in result.lower()
        or "project-2025" in result.lower(),
        category="batch",
    ),
    EvalTask(
        prompt="Archive all notes tagged #old to the archive folder",
        expected_tools=["obsidian_vault_query", "obsidian_vault_organize"],
        max_tool_calls=2,
        max_tokens=1000,
        verifier=lambda result: "archive" in result.lower() or "old" in result.lower(),
        category="batch",
    ),
    EvalTask(
        prompt="Add tag #reviewed to all notes in the review-queue folder",
        expected_tools=["obsidian_vault_query", "obsidian_vault_organize"],
        max_tool_calls=2,
        max_tokens=1000,
        verifier=lambda result: "reviewed" in result.lower()
        or "tag" in result.lower(),
        category="batch",
    ),
    EvalTask(
        prompt="Show me a preview of moving all completed tasks to the done folder (dry run)",
        expected_tools=["obsidian_vault_query", "obsidian_vault_organize"],
        max_tool_calls=2,
        max_tokens=1200,
        verifier=lambda result: "preview" in result.lower()
        or "dry" in result.lower()
        or "done" in result.lower(),
        category="batch",
    ),
    EvalTask(
        prompt="Remove the #draft tag from all notes with status=published",
        expected_tools=["obsidian_vault_query", "obsidian_vault_organize"],
        max_tool_calls=2,
        max_tokens=1000,
        verifier=lambda result: "draft" in result.lower()
        or "remove" in result.lower(),
        category="batch",
    ),
]

# Multi-Tool Workflows (6 tasks)
MULTI_TOOL_TASKS = [
    EvalTask(
        prompt="Create a summary of all project-alpha notes and save it to summaries/project-alpha.md",
        expected_tools=[
            "obsidian_vault_query",
            "obsidian_note_manage",
        ],
        max_tool_calls=3,
        max_tokens=2000,
        verifier=lambda result: "summary" in result.lower()
        or "project-alpha" in result.lower(),
        category="multi",
    ),
    EvalTask(
        prompt="Find all incomplete tasks, organize them by priority, and create a daily plan",
        expected_tools=["obsidian_vault_query", "obsidian_note_manage"],
        max_tool_calls=3,
        max_tokens=2000,
        verifier=lambda result: "task" in result.lower()
        or "priority" in result.lower(),
        category="multi",
    ),
    EvalTask(
        prompt="Analyze the knowledge graph around 'deep learning' and create a mind map note",
        expected_tools=["obsidian_graph_analyze", "obsidian_note_manage"],
        max_tool_calls=2,
        max_tokens=2000,
        verifier=lambda result: "deep learning" in result.lower()
        or "mind map" in result.lower(),
        category="multi",
    ),
    EvalTask(
        prompt="Find all notes tagged #refactor, analyze their connections, then tag them with #priority",
        expected_tools=[
            "obsidian_vault_query",
            "obsidian_graph_analyze",
            "obsidian_vault_organize",
        ],
        max_tool_calls=3,
        max_tokens=2000,
        verifier=lambda result: "refactor" in result.lower()
        or "priority" in result.lower(),
        category="multi",
    ),
    EvalTask(
        prompt="Create a new meeting note from the meeting template with today's date",
        expected_tools=["obsidian_template_create"],
        max_tool_calls=1,
        max_tokens=800,
        verifier=lambda result: "meeting" in result.lower()
        or "template" in result.lower(),
        category="multi",
    ),
    EvalTask(
        prompt="Execute a Dataview query to list all tasks due this week",
        expected_tools=["obsidian_dataview_execute"],
        max_tool_calls=1,
        max_tokens=1000,
        verifier=lambda result: "task" in result.lower() or "due" in result.lower(),
        category="multi",
    ),
]

# Combine all tasks
ALL_TASKS = SIMPLE_TASKS + SEARCH_TASKS + GRAPH_TASKS + BATCH_TASKS + MULTI_TOOL_TASKS

# Split into training and test sets (80/20 split)
# Training: 24 tasks (4 from each category)
TRAINING_TASKS = (
    SIMPLE_TASKS[:4]
    + SEARCH_TASKS[:4]
    + GRAPH_TASKS[:4]
    + BATCH_TASKS[:4]
    + MULTI_TOOL_TASKS[:4]
)

# Test: 6 tasks (remaining from each category)
TEST_TASKS = (
    SIMPLE_TASKS[4:]
    + SEARCH_TASKS[4:]
    + GRAPH_TASKS[4:]
    + BATCH_TASKS[4:]
    + MULTI_TOOL_TASKS[4:]
)
