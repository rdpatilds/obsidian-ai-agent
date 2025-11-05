"""Message format conversion utilities between OpenAI and Pydantic AI formats.

This module handles bidirectional conversion between:
- OpenAI Chat Completions API message format
- Pydantic AI agent message format (ModelMessage types)

Key conversion patterns:
- Last user message becomes the user_prompt parameter
- All previous messages become message_history
- Array content is normalized to strings (Obsidian Copilot pattern)
- System messages use SystemPromptPart
- User messages use UserPromptPart
- Assistant messages use ModelResponse with TextPart
"""

from collections.abc import Sequence
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.usage import RequestUsage

from app.openai_compat.models import Message as OpenAIMessage


def normalize_content(content: str | list[dict[str, Any]]) -> str:
    """Normalize message content to string format.

    OpenAI messages support both string and array formats. The array format
    is used for multimodal content (text + images), but Obsidian Copilot
    normalizes arrays to strings before processing.

    Args:
        content: Message content in string or array format.

    Returns:
        Normalized string content.

    Example:
        >>> normalize_content("Hello")
        "Hello"
        >>> normalize_content([{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}])
        "Hello World"
    """
    if isinstance(content, str):
        return content

    # Extract text from array format
    text_parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            text_parts.append(item)
        elif "text" in item:
            text_parts.append(str(item["text"]))

    return " ".join(text_parts)


def convert_to_pydantic_messages(
    openai_messages: Sequence[OpenAIMessage],
) -> tuple[str, Sequence[ModelMessage] | None]:
    """Convert OpenAI messages to Pydantic AI format.

    The last message becomes the user_prompt parameter for agent.iter().
    All previous messages are converted to Pydantic AI ModelMessage format
    for the message_history parameter.

    Args:
        openai_messages: List of OpenAI-format messages.

    Returns:
        Tuple of (user_prompt, message_history).
        - user_prompt: The last message's content as a string
        - message_history: Previous messages in Pydantic AI format, or None if only one message

    Example:
        >>> messages = [
        ...     Message(role="system", content="You are helpful"),
        ...     Message(role="user", content="Hello"),
        ...     Message(role="assistant", content="Hi there!"),
        ...     Message(role="user", content="How are you?")
        ... ]
        >>> user_prompt, history = convert_to_pydantic_messages(messages)
        >>> user_prompt
        "How are you?"
        >>> len(history)
        3
    """
    # Last user message becomes the prompt
    user_prompt = normalize_content(openai_messages[-1].content)

    # Single message - no history
    if len(openai_messages) == 1:
        return user_prompt, None

    # Convert all previous messages to history
    history: list[ModelMessage] = []
    for msg in openai_messages[:-1]:
        content = normalize_content(msg.content)

        if msg.role == "system":
            # System messages use SystemPromptPart
            history.append(ModelRequest(parts=[SystemPromptPart(content=content)]))
        elif msg.role == "user":
            # User messages use UserPromptPart
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif msg.role == "assistant":
            # Assistant messages use ModelResponse with TextPart
            # We don't have actual usage stats, so use zeros
            history.append(
                ModelResponse(
                    parts=[TextPart(content=content)],
                    model_name="unknown",
                    usage=RequestUsage(
                        input_tokens=0,
                        output_tokens=0,
                    ),
                    finish_reason="stop",
                )
            )

    return user_prompt, history if history else None
