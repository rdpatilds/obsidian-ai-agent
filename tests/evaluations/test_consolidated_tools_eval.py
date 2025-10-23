"""Pytest wrapper for consolidated tools evaluation.

This test suite runs the 30 evaluation tasks against the 4 consolidated tools
to measure performance, validate tool design, and collect data for optimization.
"""

import asyncio
from pathlib import Path

import frontmatter  # type: ignore
import pytest

from src.agent.agent import create_agent
from src.agent.schemas import AgentDependencies
from src.shared.config import Settings
from tests.evaluations.eval_runner import (
    EvalReport,
    print_report_summary,
    run_evaluation,
    save_report,
)
from tests.evaluations.workflow_tasks import TEST_TASKS, TRAINING_TASKS


@pytest.fixture
def evaluation_vault(tmp_path: Path) -> Path:
    """Create a realistic vault for evaluation with diverse test data.

    This vault simulates a real user's knowledge base with:
    - Project notes with metadata
    - Meeting notes with dates
    - Research notes with tags
    - Draft notes to organize
    - Connected notes with wikilinks
    """
    vault = tmp_path / "eval_vault"
    vault.mkdir()

    # Project notes
    projects_dir = vault / "projects"
    projects_dir.mkdir()

    (projects_dir / "project-alpha.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Project Alpha

## Overview
Main project for Q1 2025. Focus on AI integration.

## Status
Currently in progress, 60% complete.

## Links
Related to [[projects/project-beta]] and [[research/ai-safety]].
""",
                tags=["project", "active"],
                status="in-progress",
                priority=8,
            )
        )
    )

    (projects_dir / "project-beta.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Project Beta

## Overview
Completed project from 2024.

## Status
All done, archived.
""",
                tags=["project", "completed"],
                status="done",
                priority=5,
            )
        )
    )

    # Research notes
    research_dir = vault / "research"
    research_dir.mkdir()

    (research_dir / "ai-safety.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# AI Safety Research

## Key Concepts
Safety measures for AI systems.

Connected to multiple projects.
""",
                tags=["research", "ai", "important"],
            )
        )
    )

    (research_dir / "deep-learning.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Deep Learning

## Notes
Neural networks and architectures.

Links to [[research/ai-safety]] and [[projects/project-alpha]].
""",
                tags=["research", "ai", "deep-learning"],
            )
        )
    )

    # Main concept note for graph tests
    (vault / "main-concept.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Main Concept

Central hub connecting to:
- [[research/deep-learning]]
- [[projects/project-alpha]]
- [[research/ai-safety]]
""",
                tags=["hub", "central"],
            )
        )
    )

    # Draft notes for batch operations
    drafts_dir = vault / "drafts"
    drafts_dir.mkdir()

    for i in range(3):
        (drafts_dir / f"draft-{i}.md").write_text(
            frontmatter.dumps(
                frontmatter.Post(
                    f"""# Draft Note {i}

Content that needs review.
""",
                    tags=["draft"],
                    status="draft",
                )
            )
        )

    # Old notes for archiving
    (vault / "old-note-1.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Old Note

Should be archived.
""",
                tags=["old", "archive"],
            )
        )
    )

    # Review queue
    review_queue_dir = vault / "review-queue"
    review_queue_dir.mkdir()

    (review_queue_dir / "needs-review.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Needs Review

Content awaiting review.
""",
                tags=["review-queue"],
            )
        )
    )

    # Notes tagged with #review
    (vault / "review-note.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Review Note

For review tag test.
""",
                tags=["review"],
            )
        )
    )

    # Completed tasks
    tasks_dir = vault / "tasks"
    tasks_dir.mkdir()

    (tasks_dir / "completed-task.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Completed Task

- [x] Done
""",
                tags=["task"],
                status="completed",
            )
        )
    )

    # Incomplete tasks
    (tasks_dir / "incomplete-task.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Incomplete Task

- [ ] TODO
""",
                tags=["task"],
                status="in-progress",
                priority=9,
            )
        )
    )

    # Published notes
    (vault / "published-note.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Published Note

Already published.
""",
                tags=["draft", "article"],
                status="published",
            )
        )
    )

    # Refactor notes for multi-tool workflow
    (vault / "refactor-1.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Refactor 1

Code to refactor. Links to [[refactor-2]].
""",
                tags=["refactor", "code"],
            )
        )
    )

    (vault / "refactor-2.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Refactor 2

Related refactoring. Links to [[refactor-1]].
""",
                tags=["refactor", "code"],
            )
        )
    )

    return vault


@pytest.fixture
async def eval_agent_and_deps(evaluation_vault: Path) -> tuple:
    """Create agent and dependencies for evaluation."""
    # Create settings with evaluation vault
    settings = Settings(
        obsidian_vault_path=str(evaluation_vault),
        enable_obsidian_note_manager=True,
        enable_obsidian_vault_query=True,
        enable_obsidian_graph_analyzer=True,
        enable_obsidian_vault_organizer=True,
        model_name="openai:gpt-4o-mini",
        openai_api_key="test-key",  # Will use mock in tests
    )

    # Create agent with 4 consolidated tools
    agent = create_agent(settings)

    # Create dependencies
    deps = AgentDependencies()

    return agent, deps, settings


@pytest.mark.evaluation
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires live API - run manually with real API keys")
async def test_training_set_evaluation(
    eval_agent_and_deps: tuple, tmp_path: Path
) -> None:
    """Run evaluation on training set (20 tasks).

    This test executes the 20 training tasks to establish a baseline
    and collect data for optimization.

    To run this test:
        uv run pytest tests/evaluations/test_consolidated_tools_eval.py::test_training_set_evaluation -v -s
    """
    agent, deps, settings = eval_agent_and_deps

    print("\n" + "=" * 70)
    print("TRAINING SET EVALUATION (20 tasks)")
    print("=" * 70)

    # Run evaluation
    report = await run_evaluation(TRAINING_TASKS, agent, deps)

    # Print summary
    print_report_summary(report)

    # Save detailed report
    report_path = tmp_path / "reports" / "training_set_report.json"
    save_report(report, report_path)

    print(f"\nDetailed report saved to: {report_path}")

    # Assert minimum success rate
    assert report.success_rate >= 0.7, (
        f"Training set success rate {report.success_rate:.1%} below 70% threshold. "
        f"Tool design may need improvement."
    )

    # Assert reasonable tool call efficiency
    assert report.avg_tool_calls <= 4.0, (
        f"Average {report.avg_tool_calls:.2f} tool calls exceeds target of 4. "
        f"Tools may not be consolidated enough."
    )


@pytest.mark.evaluation
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires live API - run manually with real API keys")
async def test_held_out_evaluation(
    eval_agent_and_deps: tuple, tmp_path: Path
) -> None:
    """Run evaluation on held-out test set (10 tasks).

    This test runs against tasks not used for optimization to
    validate that improvements generalize.

    To run this test:
        uv run pytest tests/evaluations/test_consolidated_tools_eval.py::test_held_out_evaluation -v -s
    """
    agent, deps, settings = eval_agent_and_deps

    print("\n" + "=" * 70)
    print("HELD-OUT TEST SET EVALUATION (10 tasks)")
    print("=" * 70)

    # Run evaluation
    report = await run_evaluation(TEST_TASKS, agent, deps)

    # Print summary
    print_report_summary(report)

    # Save detailed report
    report_path = tmp_path / "reports" / "test_set_report.json"
    save_report(report, report_path)

    print(f"\nDetailed report saved to: {report_path}")

    # Assert held-out performance
    assert report.success_rate >= 0.7, (
        f"Test set success rate {report.success_rate:.1%} below 70% threshold. "
        f"Tools may not generalize well."
    )


@pytest.mark.evaluation
@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires live API - run manually with real API keys")
async def test_full_evaluation_suite(
    eval_agent_and_deps: tuple, tmp_path: Path
) -> None:
    """Run complete evaluation on all 30 tasks.

    This is the comprehensive evaluation that measures:
    - Overall tool performance
    - Token efficiency across formats
    - Tool call efficiency
    - Success rates by category

    To run this test:
        uv run pytest tests/evaluations/test_consolidated_tools_eval.py::test_full_evaluation_suite -v -s
    """
    agent, deps, settings = eval_agent_and_deps

    all_tasks = TRAINING_TASKS + TEST_TASKS

    print("\n" + "=" * 70)
    print(f"FULL EVALUATION SUITE ({len(all_tasks)} tasks)")
    print("=" * 70)
    print(f"Training tasks: {len(TRAINING_TASKS)}")
    print(f"Test tasks: {len(TEST_TASKS)}")
    print(f"Vault: {settings.obsidian_vault_path}")
    print("=" * 70 + "\n")

    # Run evaluation
    report = await run_evaluation(all_tasks, agent, deps)

    # Print summary
    print_report_summary(report)

    # Save detailed report
    report_path = tmp_path / "reports" / "full_evaluation_report.json"
    save_report(report, report_path)

    print(f"\n📊 Detailed report saved to: {report_path}")
    print(f"\n📈 Analysis next steps:")
    print(f"  1. Review report JSON for failed tasks")
    print(f"  2. Feed transcripts to Claude Code for analysis")
    print(f"  3. Implement suggested tool description improvements")
    print(f"  4. Re-run evaluation to measure impact")

    # Target metrics from PRD
    print(f"\n🎯 Target Metrics (from PRD):")
    print(f"  Success Rate: >90% (actual: {report.success_rate:.1%})")
    print(f"  Avg Tool Calls: <3 (actual: {report.avg_tool_calls:.2f})")
    print(f"  Avg Tokens: <1500 (actual: {report.avg_tokens:.0f})")

    # Assertions
    assert report.success_rate >= 0.7, (
        f"Overall success rate {report.success_rate:.1%} below minimum 70%. "
        f"Significant tool design issues."
    )

    if report.success_rate < 0.9:
        print(
            f"\n⚠️  Success rate {report.success_rate:.1%} below target 90%. "
            f"Optimization recommended."
        )

    if report.avg_tool_calls >= 3.0:
        print(
            f"\n⚠️  Average tool calls {report.avg_tool_calls:.2f} at/above target. "
            f"Consider further consolidation."
        )


@pytest.mark.evaluation
@pytest.mark.asyncio
async def test_evaluation_infrastructure(evaluation_vault: Path) -> None:
    """Test that evaluation infrastructure is properly set up.

    This test validates:
    - Vault is created correctly
    - All test data exists
    - Task definitions are valid
    """
    # Check vault structure
    assert evaluation_vault.exists()
    assert (evaluation_vault / "projects").exists()
    assert (evaluation_vault / "research").exists()
    assert (evaluation_vault / "drafts").exists()

    # Check key files
    assert (evaluation_vault / "projects" / "project-alpha.md").exists()
    assert (evaluation_vault / "research" / "deep-learning.md").exists()
    assert (evaluation_vault / "main-concept.md").exists()

    # Verify task definitions
    assert len(TRAINING_TASKS) == 20
    assert len(TEST_TASKS) == 10

    # Check task structure
    for task in TRAINING_TASKS + TEST_TASKS:
        assert hasattr(task, "prompt")
        assert hasattr(task, "expected_tools")
        assert hasattr(task, "max_tool_calls")
        assert hasattr(task, "max_tokens")
        assert hasattr(task, "verifier")
        assert hasattr(task, "category")

    print("\n✅ Evaluation infrastructure validated")
    print(f"   Vault: {evaluation_vault}")
    print(f"   Training tasks: {len(TRAINING_TASKS)}")
    print(f"   Test tasks: {len(TEST_TASKS)}")
    print(f"   Total: {len(TRAINING_TASKS) + len(TEST_TASKS)} tasks")
