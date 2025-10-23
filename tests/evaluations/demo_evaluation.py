#!/usr/bin/env python3
"""Quick demo evaluation - runs 3 sample tasks to demonstrate the framework."""

import asyncio
from pathlib import Path
from datetime import datetime

import frontmatter  # type: ignore

from src.agent.agent import create_agent
from src.agent.schemas import AgentDependencies
from src.shared.config import get_settings
from tests.evaluations.eval_runner import print_report_summary, run_evaluation
from tests.evaluations.workflow_tasks import SIMPLE_TASKS, SEARCH_TASKS, BATCH_TASKS


def create_demo_vault(vault_dir: Path) -> Path:
    """Create a small demo vault for quick testing."""
    vault = vault_dir / "demo_vault"
    vault.mkdir(exist_ok=True, parents=True)

    # Project note
    projects_dir = vault / "projects"
    projects_dir.mkdir(exist_ok=True)

    (projects_dir / "project-alpha.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# Project Alpha

Currently in progress, 60% complete.

Links to [[research/ai-safety]].
""",
                tags=["project", "active"],
                status="in-progress",
            )
        )
    )

    # Research note
    research_dir = vault / "research"
    research_dir.mkdir(exist_ok=True)

    (research_dir / "ai-safety.md").write_text(
        frontmatter.dumps(
            frontmatter.Post(
                """# AI Safety

Key concepts for safe AI systems.
""",
                tags=["research", "review"],
            )
        )
    )

    # Draft notes
    drafts_dir = vault / "drafts"
    drafts_dir.mkdir(exist_ok=True)

    (drafts_dir / "draft-1.md").write_text(
        frontmatter.dumps(
            frontmatter.Post("# Draft 1\nContent.", tags=["draft"])
        )
    )

    (drafts_dir / "draft-2.md").write_text(
        frontmatter.dumps(
            frontmatter.Post("# Draft 2\nContent.", tags=["draft"])
        )
    )

    print(f"✅ Created demo vault at: {vault}")
    return vault


async def main() -> None:
    """Run quick demo evaluation."""
    # Get settings
    settings = get_settings()

    # Create demo vault
    output_dir = Path("./demo_evaluation_results")
    output_dir.mkdir(exist_ok=True)
    demo_vault = create_demo_vault(output_dir)

    # Configure for demo
    settings.obsidian_vault_path = str(demo_vault)
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
        vault_path=str(demo_vault),
    )

    # Select 3 demo tasks (one from each category)
    demo_tasks = [
        SIMPLE_TASKS[0],  # Read project-alpha
        SEARCH_TASKS[0],  # Find notes tagged #review
        BATCH_TASKS[0],   # Move drafts to archive
    ]

    print("\n" + "=" * 70)
    print("QUICK DEMO EVALUATION (3 tasks)")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Model: {settings.model_name}")
    print(f"Vault: {settings.obsidian_vault_path}")
    print("=" * 70 + "\n")

    print("Running tasks:")
    for i, task in enumerate(demo_tasks, 1):
        print(f"  {i}. {task.prompt}")

    print("\n⏳ Executing evaluation...\n")

    # Run evaluation
    report = await run_evaluation(demo_tasks, agent, deps)

    # Print results
    print_report_summary(report)

    print("\n✅ Demo complete!")
    print(f"\n📊 This was a quick demo with 3 tasks.")
    print(f"📈 Full evaluation suite has 30 tasks across all categories.")
    print(f"\n🚀 To run full evaluation:")
    print(f"   python tests/evaluations/run_evaluation.py --full")


if __name__ == "__main__":
    asyncio.run(main())
