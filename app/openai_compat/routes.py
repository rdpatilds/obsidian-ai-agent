"""OpenAI-compatible chat completions endpoint for Obsidian Copilot integration.

This module provides the /v1/chat/completions endpoint that implements the OpenAI
Chat Completions API specification for streaming and non-streaming responses.

Key features:
- Streaming via Server-Sent Events (SSE)
- Non-streaming full response mode
- Message history support
- OpenAI format conversion to Pydantic AI format
- Proper error handling and logging
"""

import time
import uuid
from collections.abc import AsyncGenerator, Sequence

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    PartDeltaEvent,
    PartStartEvent,
    TextPart,
    TextPartDelta,
)

from app.core.agents import AgentDeps, vault_agent
from app.core.config import get_settings
from app.core.logging import get_logger
from app.openai_compat.converters import convert_to_pydantic_messages
from app.openai_compat.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    Usage,
)
from app.openai_compat.streaming import StreamChunkBuilder
from app.shared.vault.vault_manager import VaultManager

logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["openai-compat"])


async def stream_agent_text(
    agent: Agent[AgentDeps, str],
    user_prompt: str,
    message_history: Sequence[ModelMessage] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream text deltas from Pydantic AI agent.

    This function uses agent.iter() to stream text content from the LLM,
    extracting only text deltas from PartDeltaEvent objects.

    Args:
        agent: The Pydantic AI agent instance.
        user_prompt: The current user message prompt.
        message_history: Optional previous message history.

    Yields:
        Text content deltas as they arrive from the LLM.

    Example:
        >>> async for text_delta in stream_agent_text(vault_agent, "Hello"):
        ...     print(text_delta, end="")
        Hello! How can I help you?
    """
    settings = get_settings()
    vault_manager = VaultManager(settings.obsidian_vault_path)
    async with agent.iter(
        user_prompt,
        message_history=message_history,
        deps=AgentDeps(vault_manager=vault_manager, settings=settings),
    ) as run:
        async for node in run:
            # Extract text from model request nodes
            if Agent.is_model_request_node(node):
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        # Filter for text content deltas
                        if isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                if event.delta.content_delta:
                                    yield event.delta.content_delta

            # Stop at end node
            elif Agent.is_end_node(node):
                break


async def stream_openai_response(
    request: ChatCompletionRequest,
) -> AsyncGenerator[str, None]:
    """Generate OpenAI-compatible SSE streaming response.

    This function orchestrates the streaming workflow:
    1. Convert OpenAI messages to Pydantic AI format
    2. Stream text deltas from the agent
    3. Build and format OpenAI chunks
    4. Send final chunk with usage statistics
    5. Send termination signal

    Args:
        request: OpenAI-compatible chat completion request.

    Yields:
        SSE-formatted chunks as strings.

    Example SSE output:
        data: {"id":"chatcmpl-123","choices":[{"delta":{"role":"assistant","content":""}}]}\n\n
        data: {"id":"chatcmpl-123","choices":[{"delta":{"content":"Hello"}}]}\n\n
        data: {"id":"chatcmpl-123","choices":[{"delta":{}},"finish_reason":"stop"}],"usage":{...}}\n\n
        data: [DONE]\n\n
    """
    builder = StreamChunkBuilder(model=request.model)
    start_time = time.time()

    logger.info(
        "agent.stream_started",
        model=request.model,
        message_count=len(request.messages),
    )

    try:
        # Convert OpenAI messages to Pydantic AI format
        user_prompt, message_history = convert_to_pydantic_messages(request.messages)

        # Track token usage (we'll get this from run.usage() later)
        prompt_tokens = 0
        completion_tokens = 0

        # Stream text deltas from agent
        settings = get_settings()
        vault_manager = VaultManager(settings.obsidian_vault_path)
        async with vault_agent.iter(
            user_prompt,
            message_history=message_history,
            deps=AgentDeps(vault_manager=vault_manager, settings=settings),
        ) as run:
            # Send empty role chunk FIRST (OpenAI SSE spec requirement)
            # Must be sent before any content to properly initialize the response
            role_chunk = builder.build_role_chunk()
            logger.debug(
                "agent.stream.chunk_sending",
                chunk_type="role",
                delta=role_chunk["choices"][0]["delta"],
            )
            yield builder.format_sse(role_chunk)
            builder.role_chunk_sent = True

            async for node in run:
                if Agent.is_model_request_node(node):
                    async with node.stream(run.ctx) as request_stream:
                        async for event in request_stream:
                            # Handle initial text part (contains first chunk)
                            if isinstance(event, PartStartEvent):
                                if isinstance(event.part, TextPart) and event.part.content:
                                    chunk = builder.build_content_chunk(event.part.content)
                                    logger.debug(
                                        "agent.stream.chunk_sending",
                                        chunk_type="start",
                                        content=event.part.content,
                                    )
                                    yield builder.format_sse(chunk)

                            # Handle text deltas (subsequent chunks)
                            elif isinstance(event, PartDeltaEvent):
                                if isinstance(event.delta, TextPartDelta):
                                    if event.delta.content_delta:
                                        chunk = builder.build_content_chunk(
                                            event.delta.content_delta
                                        )
                                        logger.debug(
                                            "agent.stream.chunk_sending",
                                            chunk_type="delta",
                                            content=event.delta.content_delta,
                                        )
                                        yield builder.format_sse(chunk)

                elif Agent.is_call_tools_node(node):
                    # CallToolsNode emits tool call/result events, not text events
                    # We'll just insert newlines for visual separation after tool execution
                    # Text content comes from subsequent ModelRequestNode, not CallToolsNode
                    newline_chunk = builder.build_content_chunk("\n\n")
                    logger.debug(
                        "agent.stream.chunk_sending",
                        chunk_type="tool_separator",
                        content="\\n\\n",
                    )
                    yield builder.format_sse(newline_chunk)

                elif Agent.is_end_node(node):
                    # Get usage statistics after completion
                    usage = run.usage()
                    prompt_tokens = usage.input_tokens
                    completion_tokens = usage.output_tokens
                    break

        # Send final chunk with usage
        final_chunk = builder.build_final_chunk(prompt_tokens, completion_tokens)
        yield builder.format_sse(final_chunk)

        # Send termination signal
        yield "data: [DONE]\n\n"

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "agent.stream_completed",
            model=request.model,
            total_tokens=prompt_tokens + completion_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=round(duration_ms, 2),
        )

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "agent.stream_failed",
            model=request.model,
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=round(duration_ms, 2),
            exc_info=True,
        )

        # Send error chunk and termination
        error_chunk = {
            "error": {
                "message": str(e),
                "type": "server_error",
            }
        }
        yield builder.format_sse(error_chunk)
        yield "data: [DONE]\n\n"


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
) -> StreamingResponse | ChatCompletionResponse:
    """OpenAI-compatible chat completions endpoint.

    Implements the OpenAI Chat Completions API specification with support
    for both streaming and non-streaming modes.

    Args:
        request: Chat completion request with messages and parameters.

    Returns:
        StreamingResponse for streaming mode (stream=true).
        ChatCompletionResponse for non-streaming mode (stream=false).

    Raises:
        HTTPException: 400 if messages list is empty.
        HTTPException: 500 if agent execution fails.

    Examples:
        Streaming request:
        POST /v1/chat/completions
        {"model": "claude-sonnet-4-0", "messages": [...], "stream": true}

        Non-streaming request:
        POST /v1/chat/completions
        {"model": "claude-sonnet-4-0", "messages": [...], "stream": false}
    """
    # Validate messages
    if not request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="messages field is required and must not be empty",
        )

    logger.info(
        "request.http_received",
        endpoint="/v1/chat/completions",
        model=request.model,
        message_count=len(request.messages),
        stream=request.stream,
    )

    # Streaming mode
    if request.stream:
        return StreamingResponse(
            stream_openai_response(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Non-streaming mode
    start_time = time.time()
    try:
        # Convert messages and run agent
        user_prompt, message_history = convert_to_pydantic_messages(request.messages)
        settings = get_settings()
        vault_manager = VaultManager(settings.obsidian_vault_path)
        result = await vault_agent.run(
            user_prompt,
            message_history=message_history,
            deps=AgentDeps(vault_manager=vault_manager, settings=settings),
        )

        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "agent.chat.completed",
            model=request.model,
            total_tokens=result.usage().total_tokens,
            prompt_tokens=result.usage().input_tokens,
            completion_tokens=result.usage().output_tokens,
            duration_ms=round(duration_ms, 2),
        )

        # Build OpenAI response
        completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        response = ChatCompletionResponse(
            id=completion_id,
            created=int(time.time()),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    message=Message(
                        role="assistant",
                        content=result.output,
                    ),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=result.usage().input_tokens,
                completion_tokens=result.usage().output_tokens,
                total_tokens=result.usage().total_tokens,
            ),
        )

        logger.info(
            "request.http_completed",
            endpoint="/v1/chat/completions",
            status_code=200,
            duration_ms=round(duration_ms, 2),
        )

        return response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            "agent.chat.failed",
            model=request.model,
            error=str(e),
            error_type=type(e).__name__,
            duration_ms=round(duration_ms, 2),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {e!s}",
        ) from e
