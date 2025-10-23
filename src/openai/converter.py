"""Format conversion between OpenAI and Pydantic AI message formats.

This module provides bidirectional conversion functions:
- convert_openai_to_pydantic: OpenAI messages → Pydantic AI format
- convert_pydantic_to_openai: Pydantic AI response → OpenAI format
"""

import time
import uuid

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from src.agent.schemas import AgentResponse
from src.openai.schemas import (
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    Usage,
)
from src.shared.logging import get_logger


logger = get_logger(__name__)


def convert_openai_to_pydantic(  # noqa: PLR0912  # TODO: Refactor to reduce complexity - extract message processing into separate helper functions (extract_content_from_message, build_pydantic_message)
    messages: list[ChatMessage],
) -> tuple[str, list[ModelRequest | ModelResponse]]:
    """Convert OpenAI messages to Pydantic AI format.

    Args:
        messages: List of OpenAI ChatMessage objects.

    Returns:
        Tuple of (user_prompt, message_history).
        The last user message becomes the prompt,
        prior messages become history using Pydantic AI's native message types.

    Raises:
        ValueError: If messages list is empty or has no user message.
    """
    if not messages:
        raise ValueError("Messages list cannot be empty")  # noqa: EM101, TRY003

    logger.info(
        "format_conversion_started",
        direction="openai_to_pydantic",
        message_count=len(messages),
    )

    pydantic_messages: list[ModelRequest | ModelResponse] = []
    user_prompt = ""
    system_prompt: str | None = None

    for msg in messages:
        # Extract content (handle multimodal)
        content = ""
        if msg.content is None:
            continue

        if isinstance(msg.content, str):
            content = msg.content
        elif isinstance(msg.content, list):
            # Extract text from multimodal content
            for item in msg.content:
                if isinstance(item, dict) and item.get("type") == "text":
                    content += item.get("text", "")

        if msg.role == "system":
            system_prompt = content
        elif msg.role == "user":
            user_prompt = content  # Keep last user message as prompt
            # Create ModelRequest with UserPromptPart
            pydantic_messages.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif msg.role == "assistant":
            # Create ModelResponse with TextPart
            pydantic_messages.append(ModelResponse(parts=[TextPart(content=content)]))

    if not user_prompt:
        raise ValueError("No user message found in messages")  # noqa: EM101, TRY003

    # If we have a system prompt, prepend it to the message history
    if system_prompt:
        pydantic_messages.insert(
            0, ModelRequest(parts=[SystemPromptPart(content=system_prompt)])
        )

    # Remove the last user message from history since it's the current prompt
    if pydantic_messages and isinstance(pydantic_messages[-1], ModelRequest) and any(
        isinstance(part, UserPromptPart) for part in pydantic_messages[-1].parts
    ):
        pydantic_messages = pydantic_messages[:-1]

    logger.info(
        "format_conversion_completed",
        direction="openai_to_pydantic",
        prompt_length=len(user_prompt),
        history_length=len(pydantic_messages),
    )

    return user_prompt, pydantic_messages


def convert_pydantic_to_openai(
    response: AgentResponse, request_model: str
) -> ChatCompletionResponse:
    """Convert Pydantic AI response to OpenAI format.

    Args:
        response: Agent response from Pydantic AI.
        request_model: Model name from original request.

    Returns:
        OpenAI-compatible ChatCompletionResponse.
    """
    logger.info("format_conversion_started", direction="pydantic_to_openai")

    openai_response = ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
        object="chat.completion",
        created=int(time.time()),
        model=request_model,
        choices=[
            Choice(
                index=0,
                message=ChatMessage(role="assistant", content=response.response_text),
                finish_reason=response.finish_reason,
            )
        ],
        usage=Usage(
            prompt_tokens=response.usage.get("prompt_tokens", 0),
            completion_tokens=response.usage.get("completion_tokens", 0),
            total_tokens=response.usage.get("total_tokens", 0),
        ),
    )

    logger.info("format_conversion_completed", direction="pydantic_to_openai")
    return openai_response
