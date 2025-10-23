"""Evaluation runner for measuring agent tool performance.

This module executes evaluation tasks, collects transcripts,
and generates performance reports.
"""

import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TaskResult:
    """Result from executing a single evaluation task."""

    task_prompt: str
    category: str
    success: bool
    tool_calls: list[dict[str, Any]]
    token_usage: dict[str, int]
    duration_ms: float
    error_message: str | None = None
    agent_response: str = ""


@dataclass
class EvalReport:
    """Evaluation report with metrics and task results."""

    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    success_rate: float
    avg_tool_calls: float
    avg_tokens: float
    avg_duration_ms: float
    tool_usage_frequency: dict[str, int] = field(default_factory=dict)
    category_performance: dict[str, dict[str, Any]] = field(default_factory=dict)
    task_results: list[TaskResult] = field(default_factory=list)


async def run_evaluation(
    tasks: list[Any], agent: Any, deps: Any
) -> EvalReport:  # noqa: ANN401
    """Run evaluation on a list of tasks.

    Args:
        tasks: List of EvalTask instances to evaluate.
        agent: Pydantic AI agent instance to test.
        deps: Agent dependencies (AgentDependencies).

    Returns:
        EvalReport with comprehensive metrics and task results.

    Raises:
        None - errors are captured in task results.
    """
    logger.info("evaluation_started", task_count=len(tasks))

    task_results: list[TaskResult] = []
    tool_usage: dict[str, int] = defaultdict(int)
    category_stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"total": 0, "success": 0, "avg_tokens": 0, "avg_tool_calls": 0}
    )

    for task in tasks:
        logger.info(
            "task_started", prompt=task.prompt[:50], category=task.category
        )

        start_time = time.perf_counter()
        tool_calls: list[dict[str, Any]] = []
        success = False
        error_message = None
        agent_response = ""
        token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        try:
            # Execute agent run
            result = await agent.run(task.prompt, deps=deps)

            # Extract response
            agent_response = str(result.data) if hasattr(result, "data") else str(result)

            # Collect tool calls from result (if available)
            # Note: Filter out ToolReturnPart (empty args) and only capture ToolCallPart
            if hasattr(result, "all_messages"):
                for message in result.all_messages():
                    if hasattr(message, "parts"):
                        for part in message.parts:
                            if hasattr(part, "tool_name"):
                                # Only capture actual tool calls (with args), not returns (empty)
                                args = getattr(part, "args", {})
                                if args:  # Skip empty tool returns
                                    tool_call = {
                                        "tool": part.tool_name,
                                        "args": args,
                                    }
                                    tool_calls.append(tool_call)
                                    tool_usage[part.tool_name] += 1

            # Estimate token usage (rough approximation)
            # In production, this would come from actual API metrics
            prompt_tokens = len(task.prompt.split()) * 1.3  # Rough tokenization
            completion_tokens = len(agent_response.split()) * 1.3
            token_usage = {
                "prompt_tokens": int(prompt_tokens),
                "completion_tokens": int(completion_tokens),
                "total_tokens": int(prompt_tokens + completion_tokens),
            }

            # Verify result
            success = task.verifier(agent_response)

            # Check constraints
            if len(tool_calls) > task.max_tool_calls:
                logger.warning(
                    "task_exceeded_tool_calls",
                    prompt=task.prompt[:50],
                    tool_calls=len(tool_calls),
                    max_tool_calls=task.max_tool_calls,
                )
                # Still count as success if verifier passed

            if token_usage["total_tokens"] > task.max_tokens:
                logger.warning(
                    "task_exceeded_tokens",
                    prompt=task.prompt[:50],
                    tokens=token_usage["total_tokens"],
                    max_tokens=task.max_tokens,
                )

        except Exception as e:
            logger.exception(
                "task_failed", prompt=task.prompt[:50], error=str(e)
            )
            error_message = str(e)
            success = False

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Create task result
        task_result = TaskResult(
            task_prompt=task.prompt,
            category=task.category,
            success=success,
            tool_calls=tool_calls,
            token_usage=token_usage,
            duration_ms=duration_ms,
            error_message=error_message,
            agent_response=agent_response,
        )
        task_results.append(task_result)

        # Update category stats
        category_stats[task.category]["total"] += 1
        if success:
            category_stats[task.category]["success"] += 1

        logger.info(
            "task_completed",
            prompt=task.prompt[:50],
            success=success,
            tool_calls=len(tool_calls),
            duration_ms=duration_ms,
        )

    # Calculate aggregate metrics
    successful = sum(1 for r in task_results if r.success)
    failed = len(task_results) - successful
    success_rate = (successful / len(task_results)) if task_results else 0.0

    avg_tool_calls = (
        sum(len(r.tool_calls) for r in task_results) / len(task_results)
        if task_results
        else 0.0
    )

    avg_tokens = (
        sum(r.token_usage["total_tokens"] for r in task_results) / len(task_results)
        if task_results
        else 0.0
    )

    avg_duration = (
        sum(r.duration_ms for r in task_results) / len(task_results)
        if task_results
        else 0.0
    )

    # Calculate category performance
    for category, stats in category_stats.items():
        category_results = [r for r in task_results if r.category == category]
        stats["avg_tokens"] = (
            sum(r.token_usage["total_tokens"] for r in category_results)
            / len(category_results)
            if category_results
            else 0.0
        )
        stats["avg_tool_calls"] = (
            sum(len(r.tool_calls) for r in category_results) / len(category_results)
            if category_results
            else 0.0
        )

    report = EvalReport(
        total_tasks=len(task_results),
        successful_tasks=successful,
        failed_tasks=failed,
        success_rate=success_rate,
        avg_tool_calls=avg_tool_calls,
        avg_tokens=avg_tokens,
        avg_duration_ms=avg_duration,
        tool_usage_frequency=dict(tool_usage),
        category_performance=dict(category_stats),
        task_results=task_results,
    )

    logger.info(
        "evaluation_completed",
        success_rate=success_rate,
        avg_tool_calls=avg_tool_calls,
        avg_tokens=avg_tokens,
    )

    return report


def save_report(report: EvalReport, output_path: str | Path) -> None:
    """Save evaluation report to JSON file.

    Args:
        report: EvalReport to save.
        output_path: Path to output JSON file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict for JSON serialization
    report_dict = asdict(report)

    with open(output_path, "w") as f:
        json.dump(report_dict, f, indent=2)

    logger.info("report_saved", path=str(output_path))


def print_report_summary(report: EvalReport) -> None:
    """Print human-readable report summary to console.

    Args:
        report: EvalReport to print.
    """
    print("\n" + "=" * 60)
    print("EVALUATION REPORT SUMMARY")
    print("=" * 60)
    print(f"Total Tasks: {report.total_tasks}")
    print(f"Successful: {report.successful_tasks}")
    print(f"Failed: {report.failed_tasks}")
    print(f"Success Rate: {report.success_rate:.1%}")
    print(f"\nAvg Tool Calls: {report.avg_tool_calls:.2f}")
    print(f"Avg Tokens: {report.avg_tokens:.0f}")
    print(f"Avg Duration: {report.avg_duration_ms:.0f}ms")
    print("\nTool Usage Frequency:")
    for tool, count in sorted(
        report.tool_usage_frequency.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {tool}: {count}")
    print("\nCategory Performance:")
    for category, stats in report.category_performance.items():
        success_rate = (
            stats["success"] / stats["total"] if stats["total"] > 0 else 0.0
        )
        print(f"  {category}:")
        print(f"    Success Rate: {success_rate:.1%}")
        print(f"    Avg Tool Calls: {stats['avg_tool_calls']:.2f}")
        print(f"    Avg Tokens: {stats['avg_tokens']:.0f}")
    print("=" * 60 + "\n")
