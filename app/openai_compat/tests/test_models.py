"""Unit tests for OpenAI-compatible Pydantic models."""

from typing import Any

import pytest
from pydantic import ValidationError

from app.openai_compat.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    Usage,
)


def test_message_with_string_content() -> None:
    """Test message with simple string content."""
    msg = Message(role="user", content="Hello, world!")

    assert msg.role == "user"
    assert msg.content == "Hello, world!"
    assert msg.name is None
    assert msg.tool_calls is None


def test_message_with_array_content() -> None:
    """Test message with multimodal array content."""
    content: list[dict[str, Any]] = [
        {"type": "text", "text": "Describe this image:"},
        {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
    ]
    msg = Message(role="user", content=content)

    assert msg.role == "user"
    assert isinstance(msg.content, list)
    assert len(msg.content) == 2


def test_message_with_tool_call() -> None:
    """Test assistant message with tool call."""
    msg = Message(
        role="assistant",
        content="",
        tool_calls=[
            {
                "id": "call_123",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"city": "NYC"}'},
            }
        ],
    )

    assert msg.role == "assistant"
    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1


def test_chat_completion_request_minimal() -> None:
    """Test chat completion request with required fields only."""
    req = ChatCompletionRequest(
        model="claude-sonnet-4-0",
        messages=[Message(role="user", content="Hello")],
    )

    assert req.model == "claude-sonnet-4-0"
    assert len(req.messages) == 1
    assert req.stream is False
    assert req.temperature == 1.0
    assert req.n == 1


def test_chat_completion_request_full() -> None:
    """Test chat completion request with all optional fields."""
    req = ChatCompletionRequest(
        model="claude-sonnet-4-0",
        messages=[Message(role="user", content="Hello")],
        temperature=0.7,
        max_tokens=1000,
        stream=True,
        top_p=0.9,
        frequency_penalty=0.5,
        presence_penalty=0.3,
        stop=["END"],
        n=1,
    )

    assert req.temperature == 0.7
    assert req.max_tokens == 1000
    assert req.stream is True
    assert req.top_p == 0.9
    assert req.frequency_penalty == 0.5
    assert req.presence_penalty == 0.3
    assert req.stop == ["END"]


def test_chat_completion_request_validation_empty_messages() -> None:
    """Test that empty messages list raises validation error."""
    with pytest.raises(ValidationError) as exc_info:
        ChatCompletionRequest(
            model="claude-sonnet-4-0",
            messages=[],
        )

    errors = exc_info.value.errors()
    assert len(errors) > 0
    assert any("min_length" in str(err) for err in errors)


def test_chat_completion_request_validation_temperature() -> None:
    """Test temperature bounds validation."""
    # Valid temperature
    req = ChatCompletionRequest(
        model="test",
        messages=[Message(role="user", content="test")],
        temperature=0.5,
    )
    assert req.temperature == 0.5

    # Invalid temperature too high
    with pytest.raises(ValidationError):
        ChatCompletionRequest(
            model="test",
            messages=[Message(role="user", content="test")],
            temperature=3.0,
        )

    # Invalid temperature negative
    with pytest.raises(ValidationError):
        ChatCompletionRequest(
            model="test",
            messages=[Message(role="user", content="test")],
            temperature=-0.5,
        )


def test_chat_completion_response_structure() -> None:
    """Test chat completion response structure."""
    response = ChatCompletionResponse(
        id="chatcmpl-123",
        created=1234567890,
        model="claude-sonnet-4-0",
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content="Hello!"),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
    )

    assert response.id == "chatcmpl-123"
    assert response.object == "chat.completion"
    assert response.model == "claude-sonnet-4-0"
    assert len(response.choices) == 1
    assert response.choices[0].message.content == "Hello!"
    assert response.usage.total_tokens == 15


def test_usage_model() -> None:
    """Test usage statistics model."""
    usage = Usage(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
    )

    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150


def test_choice_model() -> None:
    """Test choice model."""
    choice = Choice(
        index=0,
        message=Message(role="assistant", content="Response text"),
        finish_reason="stop",
    )

    assert choice.index == 0
    assert choice.message.role == "assistant"
    assert choice.finish_reason == "stop"
