"""Unit tests for message format conversion utilities."""

from typing import Any

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    SystemPromptPart,
    TextPart,
    UserPromptPart,
)

from app.openai_compat.converters import convert_to_pydantic_messages, normalize_content
from app.openai_compat.models import Message


def test_normalize_content_string() -> None:
    """Test normalizing string content returns unchanged."""
    content = "Hello, world!"
    result = normalize_content(content)

    assert result == "Hello, world!"
    assert isinstance(result, str)


def test_normalize_content_array_single_text() -> None:
    """Test normalizing array with single text object."""
    content = [{"type": "text", "text": "Hello"}]
    result = normalize_content(content)

    assert result == "Hello"


def test_normalize_content_array_multiple_text() -> None:
    """Test normalizing array with multiple text objects."""
    content: list[dict[str, Any]] = [
        {"type": "text", "text": "Hello"},
        {"type": "text", "text": "World"},
    ]
    result = normalize_content(content)

    assert result == "Hello World"


def test_normalize_content_array_with_image() -> None:
    """Test normalizing array with text and image (image ignored)."""
    content: list[dict[str, Any]] = [
        {"type": "text", "text": "Describe this:"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
    ]
    result = normalize_content(content)

    # Only text is extracted, image is ignored
    assert result == "Describe this:"


def test_normalize_content_empty_array() -> None:
    """Test normalizing empty array returns empty string."""
    content: list[dict[str, str]] = []
    result = normalize_content(content)

    assert result == ""


def test_convert_single_message() -> None:
    """Test converting single user message (no history)."""
    messages = [Message(role="user", content="Hello")]
    user_prompt, history = convert_to_pydantic_messages(messages)

    assert user_prompt == "Hello"
    assert history is None


def test_convert_with_history() -> None:
    """Test converting multiple messages creates history."""
    messages = [
        Message(role="user", content="First message"),
        Message(role="assistant", content="First response"),
        Message(role="user", content="Second message"),
    ]
    user_prompt, history = convert_to_pydantic_messages(messages)

    assert user_prompt == "Second message"
    assert history is not None
    assert len(history) == 2


def test_convert_with_system_message() -> None:
    """Test converting messages with system message."""
    messages = [
        Message(role="system", content="You are helpful"),
        Message(role="user", content="Hello"),
    ]
    user_prompt, history = convert_to_pydantic_messages(messages)

    assert user_prompt == "Hello"
    assert history is not None
    assert len(history) == 1

    # Verify system message uses SystemPromptPart
    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[0].parts[0], SystemPromptPart)
    assert history[0].parts[0].content == "You are helpful"


def test_convert_preserves_order() -> None:
    """Test that message order is preserved in history."""
    messages = [
        Message(role="user", content="Message 1"),
        Message(role="assistant", content="Response 1"),
        Message(role="user", content="Message 2"),
        Message(role="assistant", content="Response 2"),
        Message(role="user", content="Message 3"),
    ]
    user_prompt, history = convert_to_pydantic_messages(messages)

    assert user_prompt == "Message 3"
    assert history is not None
    assert len(history) == 4

    # Check order
    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[0].parts[0], UserPromptPart)
    assert history[0].parts[0].content == "Message 1"

    assert isinstance(history[1], ModelResponse)
    assert isinstance(history[1].parts[0], TextPart)
    assert history[1].parts[0].content == "Response 1"


def test_convert_user_message_type() -> None:
    """Test user messages create ModelRequest with UserPromptPart."""
    messages = [
        Message(role="user", content="First"),
        Message(role="user", content="Second"),
    ]
    user_prompt, history = convert_to_pydantic_messages(messages)

    assert user_prompt == "Second"
    assert history is not None
    assert len(history) == 1
    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[0].parts[0], UserPromptPart)


def test_convert_assistant_message_type() -> None:
    """Test assistant messages create ModelResponse."""
    messages = [
        Message(role="assistant", content="Response"),
        Message(role="user", content="Follow-up"),
    ]
    user_prompt, history = convert_to_pydantic_messages(messages)

    assert user_prompt == "Follow-up"
    assert history is not None
    assert len(history) == 1
    assert isinstance(history[0], ModelResponse)
    assert isinstance(history[0].parts[0], TextPart)
    assert history[0].parts[0].content == "Response"
    assert history[0].finish_reason == "stop"


def test_convert_normalizes_array_content() -> None:
    """Test that array content is normalized during conversion."""
    messages = [
        Message(
            role="user",
            content=[
                {"type": "text", "text": "Hello"},
                {"type": "text", "text": "World"},
            ],
        )
    ]
    user_prompt, history = convert_to_pydantic_messages(messages)

    assert user_prompt == "Hello World"
    assert history is None


def test_convert_complex_conversation() -> None:
    """Test converting complex conversation with multiple message types."""
    messages = [
        Message(role="system", content="You are a helpful assistant"),
        Message(role="user", content="What is Python?"),
        Message(role="assistant", content="Python is a programming language."),
        Message(role="user", content="What can I do with it?"),
        Message(role="assistant", content="You can build web apps, scripts, and more."),
        Message(role="user", content="How do I start?"),
    ]
    user_prompt, history = convert_to_pydantic_messages(messages)

    assert user_prompt == "How do I start?"
    assert history is not None
    assert len(history) == 5

    # Verify types
    assert isinstance(history[0], ModelRequest)  # system
    assert isinstance(history[0].parts[0], SystemPromptPart)
    assert isinstance(history[1], ModelRequest)  # user
    assert isinstance(history[1].parts[0], UserPromptPart)
    assert isinstance(history[2], ModelResponse)  # assistant
    assert isinstance(history[3], ModelRequest)  # user
    assert isinstance(history[4], ModelResponse)  # assistant
