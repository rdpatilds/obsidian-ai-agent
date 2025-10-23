"""Transcript analysis helper for evaluation-driven tool optimization.

This module formats evaluation transcripts for Claude analysis
and helps extract optimization suggestions.
"""

from typing import Any

from src.shared.logging import get_logger

logger = get_logger(__name__)


def format_transcript_for_analysis(task_results: list[Any]) -> str:
    """Format task results into a transcript for Claude analysis.

    Args:
        task_results: List of TaskResult instances from evaluation.

    Returns:
        Formatted transcript string for Claude to analyze.
    """
    transcript = "# Evaluation Transcripts for Tool Optimization\n\n"
    transcript += "Analyze these agent interactions to identify:\n"
    transcript += "1. Tool confusion - agent choosing wrong tools\n"
    transcript += "2. Token waste - using detailed format when minimal would work\n"
    transcript += "3. Redundant calls - multiple calls that could be consolidated\n"
    transcript += "4. Efficiency opportunities - ways to reduce tool calls or tokens\n\n"
    transcript += "## Task Transcripts\n\n"

    for idx, result in enumerate(task_results, 1):
        transcript += f"### Task {idx}: {result.category.upper()}\n\n"
        transcript += f"**Prompt:** {result.task_prompt}\n\n"
        transcript += f"**Success:** {'✓' if result.success else '✗'}\n"
        transcript += f"**Tool Calls:** {len(result.tool_calls)}\n"
        transcript += f"**Tokens Used:** {result.token_usage['total_tokens']}\n"
        transcript += f"**Duration:** {result.duration_ms:.0f}ms\n\n"

        if result.tool_calls:
            transcript += "**Tool Call Sequence:**\n\n"
            for call_idx, call in enumerate(result.tool_calls, 1):
                transcript += f"{call_idx}. `{call['tool']}(`\n"
                # Show key args only (truncate long values)
                for arg, value in call.get("args", {}).items():
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:97] + "..."
                    transcript += f"   - {arg}: {value_str}\n"
                transcript += ")\n\n"

        if result.error_message:
            transcript += f"**Error:** {result.error_message}\n\n"

        transcript += f"**Agent Response:** {result.agent_response[:200]}...\n\n"
        transcript += "---\n\n"

    return transcript


def generate_analysis_prompt(transcript: str, focus_areas: list[str] | None = None) -> str:
    """Generate a prompt for Claude to analyze transcripts.

    Args:
        transcript: Formatted transcript from format_transcript_for_analysis().
        focus_areas: Optional specific areas to focus analysis on.

    Returns:
        Prompt string for Claude analysis.
    """
    if focus_areas is None:
        focus_areas = [
            "tool selection patterns",
            "token efficiency",
            "redundant operations",
            "response format usage",
        ]

    prompt = transcript + "\n\n"
    prompt += "## Analysis Request\n\n"
    prompt += "Please analyze the above transcripts and provide:\n\n"
    prompt += "1. **Patterns**: Common patterns in tool usage (good and bad)\n"
    prompt += "2. **Issues**: Specific problems identified (tool confusion, waste)\n"
    prompt += "3. **Recommendations**: Actionable suggestions to improve:\n"

    for area in focus_areas:
        prompt += f"   - {area}\n"

    prompt += "\n4. **Tool Description Updates**: Specific changes to tool docstrings "
    prompt += "that would help the agent make better choices\n\n"
    prompt += "Focus on concrete, measurable improvements that reduce tool calls "
    prompt += "and token usage while maintaining task success.\n"

    return prompt


def extract_suggestions_from_analysis(analysis_text: str) -> dict[str, list[str]]:
    """Extract structured suggestions from Claude's analysis.

    Args:
        analysis_text: Claude's analysis response text.

    Returns:
        Dictionary with categorized suggestions.
    """
    suggestions: dict[str, list[str]] = {
        "patterns": [],
        "issues": [],
        "recommendations": [],
        "tool_updates": [],
    }

    # Simple section-based parsing
    current_section = None
    lines = analysis_text.split("\n")

    for line in lines:
        line_lower = line.lower().strip()

        # Detect section headers
        if "pattern" in line_lower and line.startswith("#"):
            current_section = "patterns"
            continue
        elif "issue" in line_lower and line.startswith("#"):
            current_section = "issues"
            continue
        elif "recommendation" in line_lower and line.startswith("#"):
            current_section = "recommendations"
            continue
        elif "tool" in line_lower and "update" in line_lower and line.startswith("#"):
            current_section = "tool_updates"
            continue

        # Extract bullet points
        if current_section and line.strip().startswith(("- ", "* ", "1.", "2.", "3.")):
            suggestion = line.strip().lstrip("- *123456789.")
            if suggestion:
                suggestions[current_section].append(suggestion)

    logger.info(
        "suggestions_extracted",
        patterns=len(suggestions["patterns"]),
        issues=len(suggestions["issues"]),
        recommendations=len(suggestions["recommendations"]),
        tool_updates=len(suggestions["tool_updates"]),
    )

    return suggestions


def create_improvement_report(
    original_metrics: dict[str, float],
    improved_metrics: dict[str, float],
    suggestions_applied: list[str],
) -> str:
    """Create a report showing improvements after applying suggestions.

    Args:
        original_metrics: Original evaluation metrics (success_rate, avg_tool_calls, etc.).
        improved_metrics: Metrics after applying suggestions.
        suggestions_applied: List of suggestions that were implemented.

    Returns:
        Formatted improvement report string.
    """
    report = "# Tool Optimization Improvement Report\n\n"
    report += "## Suggestions Applied\n\n"

    for idx, suggestion in enumerate(suggestions_applied, 1):
        report += f"{idx}. {suggestion}\n"

    report += "\n## Metrics Comparison\n\n"
    report += "| Metric | Original | Improved | Change |\n"
    report += "|--------|----------|----------|--------|\n"

    for metric in ["success_rate", "avg_tool_calls", "avg_tokens", "avg_duration_ms"]:
        if metric in original_metrics and metric in improved_metrics:
            original = original_metrics[metric]
            improved = improved_metrics[metric]
            change = improved - original
            change_pct = (change / original * 100) if original != 0 else 0

            # Format based on metric type
            if metric == "success_rate":
                orig_str = f"{original:.1%}"
                imp_str = f"{improved:.1%}"
                change_str = f"{change_pct:+.1f}%"
            elif metric == "avg_duration_ms":
                orig_str = f"{original:.0f}ms"
                imp_str = f"{improved:.0f}ms"
                change_str = f"{change:+.0f}ms ({change_pct:+.1f}%)"
            else:
                orig_str = f"{original:.2f}"
                imp_str = f"{improved:.2f}"
                change_str = f"{change:+.2f} ({change_pct:+.1f}%)"

            report += f"| {metric} | {orig_str} | {imp_str} | {change_str} |\n"

    report += "\n## Summary\n\n"
    report += "This report documents the iterative improvement process "
    report += "following Anthropic's evaluation-driven development approach.\n"

    return report
