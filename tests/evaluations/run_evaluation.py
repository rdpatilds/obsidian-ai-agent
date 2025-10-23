#!/usr/bin/env python3
"""Manual evaluation runner for consolidated Obsidian tools.

Run this script to execute the evaluation suite against the 4 consolidated tools.
Requires valid API keys set in environment or .env file.

Usage:
    # Run full evaluation (30 tasks)
    python tests/evaluations/run_evaluation.py --full

    # Run training set only (20 tasks)
    python tests/evaluations/run_evaluation.py --training

    # Run test set only (10 tasks)
    python tests/evaluations/run_evaluation.py --test

    # Specify custom output directory
    python tests/evaluations/run_evaluation.py --full --output ./eval_results
"""

import argparse
import asyncio
from datetime import datetime
from pathlib import Path

import frontmatter  # type: ignore

from src.agent.agent import create_agent
from src.agent.schemas import AgentDependencies
from src.shared.config import get_settings
from tests.evaluations.eval_runner import (
    print_report_summary,
    run_evaluation,
    save_report,
)
from tests.evaluations.workflow_tasks import TEST_TASKS, TRAINING_TASKS


def create_evaluation_vault(vault_dir: Path) -> Path:
    """Create a realistic vault for evaluation with diverse test data."""
    vault = vault_dir / "eval_vault"
    vault.mkdir(exist_ok=True)

    # Project notes
    projects_dir = vault / "projects"
    projects_dir.mkdir(exist_ok=True)

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
    research_dir.mkdir(exist_ok=True)

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
    drafts_dir.mkdir(exist_ok=True)

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
    review_queue_dir.mkdir(exist_ok=True)

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
    tasks_dir.mkdir(exist_ok=True)

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

    print(f"✅ Created evaluation vault at: {vault}")
    return vault


async def run_evaluation_main(mode: str, output_dir: Path) -> None:
    """Run evaluation suite.

    Args:
        mode: "full", "training", or "test"
        output_dir: Directory to save evaluation reports
    """
    # Get settings
    settings = get_settings()

    # Create evaluation vault
    temp_vault = create_evaluation_vault(output_dir)

    # Override vault path for evaluation
    settings.obsidian_vault_path = str(temp_vault)

    # Ensure all tools are enabled
    settings.enable_obsidian_note_manager = True
    settings.enable_obsidian_vault_query = True
    settings.enable_obsidian_graph_analyzer = True
    settings.enable_obsidian_vault_organizer = True

    # Create agent
    agent = create_agent(settings)

    # Create dependencies with required fields
    import httpx
    deps = AgentDependencies(
        http_client=httpx.AsyncClient(),
        openai_api_key=settings.openai_api_key or "",
        vault_path=str(temp_vault),
    )

    # Select tasks
    if mode == "full":
        tasks = TRAINING_TASKS + TEST_TASKS
        task_label = "Full Evaluation (30 tasks)"
    elif mode == "training":
        tasks = TRAINING_TASKS
        task_label = "Training Set (20 tasks)"
    else:  # test
        tasks = TEST_TASKS
        task_label = "Test Set (10 tasks)"

    # Print header
    print("\n" + "=" * 70)
    print(task_label.upper())
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: {settings.model_name}")
    print(f"Vault: {settings.obsidian_vault_path}")
    print(f"Output: {output_dir}")
    print("=" * 70 + "\n")

    # Run evaluation
    report = await run_evaluation(tasks, agent, deps)

    # Print summary
    print_report_summary(report)

    # Save report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"{mode}_evaluation_{timestamp}.json"
    report_path = output_dir / report_filename

    save_report(report, report_path)

    print(f"\n📊 Detailed report saved to: {report_path}")

    # Print analysis suggestions
    print(f"\n📈 Next Steps:")
    print(f"  1. Review report JSON: {report_path}")
    print(f"  2. Check failed tasks in report['task_results']")
    print(f"  3. Feed transcripts to Claude Code for analysis:")
    print(f"     'Analyze these evaluation results and suggest improvements'")
    print(f"  4. Implement suggested tool description improvements")
    print(f"  5. Re-run evaluation to measure impact")

    # Print target metrics
    print(f"\n🎯 Target Metrics (from PRD):")
    print(f"  Success Rate: >90% (actual: {report.success_rate:.1%})")
    print(f"  Avg Tool Calls: <3 (actual: {report.avg_tool_calls:.2f})")
    print(f"  Avg Tokens: <1500 (actual: {report.avg_tokens:.0f})")

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

    print("\n✅ Evaluation complete!")


def main() -> None:
    """Parse arguments and run evaluation."""
    parser = argparse.ArgumentParser(
        description="Run evaluation suite for consolidated Obsidian tools"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full evaluation (30 tasks)",
    )
    parser.add_argument(
        "--training",
        action="store_true",
        help="Run training set only (20 tasks)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run test set only (10 tasks)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./evaluation_results"),
        help="Output directory for reports (default: ./evaluation_results)",
    )

    args = parser.parse_args()

    # Determine mode
    if args.full:
        mode = "full"
    elif args.training:
        mode = "training"
    elif args.test:
        mode = "test"
    else:
        print("❌ Error: Specify --full, --training, or --test")
        parser.print_help()
        return

    # Create output directory
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    # Run evaluation
    asyncio.run(run_evaluation_main(mode, output_dir))


if __name__ == "__main__":
    main()
