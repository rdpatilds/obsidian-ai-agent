"""Agent service layer for executing agent requests.

This module provides service functions for:
- Non-streaming agent execution
- Streaming agent execution with proper event handling
- Error handling and structured logging
"""

from collections.abc import AsyncIterator

from pydantic_ai import Agent
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPartDelta
from pydantic_ai.settings import ModelSettings

from src.agent.agent import get_agent
from src.agent.schemas import AgentDependencies, AgentRequest, AgentResponse
from src.shared.logging import get_logger


logger = get_logger(__name__)


async def run_agent(
    request: AgentRequest,
    deps: AgentDependencies,
    model_settings: ModelSettings | None = None,
) -> AgentResponse:
    """Run agent with given request and dependencies.

    Args:
        request: Agent request with prompt and message history.
        deps: Dependencies for agent tools (HTTP client, API keys).
        model_settings: Optional model settings (temperature, max_tokens, etc.).

    Returns:
        Agent response with text, tool calls, and usage stats.

    Raises:
        ValueError: If request validation fails.
        RuntimeError: If agent execution fails.
    """
    logger.info(
        "agent_request_started",
        request_id=request.request_id,
        prompt_length=len(request.prompt),
        history_length=len(request.message_history),
    )

    try:
        agent = get_agent()

        # Run agent with message history and optional model settings
        result = await agent.run(
            request.prompt,
            deps=deps,
            message_history=request.message_history,
            model_settings=model_settings,
        )

        usage_stats = result.usage()
        usage_dict = {
            "prompt_tokens": usage_stats.input_tokens,
            "completion_tokens": usage_stats.output_tokens,
            "total_tokens": usage_stats.total_tokens,
        }

        logger.info(
            "agent_request_completed",
            request_id=request.request_id,
            response_length=len(str(result.output)),
            usage=usage_dict,
        )

        return AgentResponse(
            response_text=str(result.output),
            tool_calls=[],
            usage=usage_dict,
            finish_reason="stop",
        )
    except Exception as e:
        logger.exception(
            "agent_request_failed",
            request_id=request.request_id,
            error_type=type(e).__name__,
        )
        raise


async def stream_agent(
    request: AgentRequest,
    deps: AgentDependencies,
    model_settings: ModelSettings | None = None,
) -> AsyncIterator[str]:
    """Stream agent response as it's generated.

    Args:
        request: Agent request with prompt and message history.
        deps: Dependencies for agent tools.
        model_settings: Optional model settings (temperature, max_tokens, etc.).

    Yields:
        Text chunks as they're generated.

    Raises:
        ValueError: If request validation fails.
        RuntimeError: If agent execution fails.
    """
    logger.info(
        "agent_stream_started",
        request_id=request.request_id,
        prompt_length=len(request.prompt),
    )

    try:
        agent = get_agent()

        # Use agent.iter() for streaming (NOT run_stream)
        async with agent.iter(
            request.prompt,
            deps=deps,
            message_history=request.message_history,
            model_settings=model_settings,
        ) as run:
            async for node in run:
                # Check if this is a model request node (where streaming happens)
                if Agent.is_model_request_node(node):
                    # Stream from the node
                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            # Handle initial content (PartStartEvent)
                            if (
                                isinstance(event, PartStartEvent)
                                and event.part.part_kind == "text"
                            ):
                                yield event.part.content
                            # Handle incremental deltas (PartDeltaEvent)
                            elif isinstance(event, PartDeltaEvent) and isinstance(
                                event.delta, TextPartDelta
                            ):
                                yield event.delta.content_delta

        logger.info("agent_stream_completed", request_id=request.request_id)
    except Exception as e:
        logger.exception(
            "agent_stream_failed",
            request_id=request.request_id,
            error_type=type(e).__name__,
        )
        raise
