"""Unit tests for OpenAI format converter."""

import pytest

from src.agent.schemas import AgentResponse
from src.openai.converter import convert_openai_to_pydantic, convert_pydantic_to_openai
from src.openai.schemas import ChatMessage


@pytest.mark.unit
def test_convert_openai_to_pydantic_single_user_message():
    """Test conversion with single user message."""
    messages = [ChatMessage(role="user", content="Hello")]

    prompt, history = convert_openai_to_pydantic(messages)

    assert prompt == "Hello"
    assert len(history) == 0


@pytest.mark.unit
def test_convert_openai_to_pydantic_with_conversation():
    """Test conversion with system + user + assistant messages."""
    messages = [
        ChatMessage(role="system", content="You are helpful"),
        ChatMessage(role="user", content="What is 2+2?"),
        ChatMessage(role="assistant", content="4"),
        ChatMessage(role="user", content="Thanks"),
    ]

    prompt, history = convert_openai_to_pydantic(messages)

    assert prompt == "Thanks"
    assert len(history) == 3  # system + first user + assistant


@pytest.mark.unit
def test_convert_openai_to_pydantic_multimodal():
    """Test conversion with multimodal content."""
    messages = [
        ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "Hello"},
                {"type": "image_url", "image_url": {"url": "https://example.com/img.jpg"}},
            ],
        )
    ]

    prompt, history = convert_openai_to_pydantic(messages)

    assert prompt == "Hello"
    assert len(history) == 0


@pytest.mark.unit
def test_convert_openai_to_pydantic_empty_messages():
    """Test conversion with empty messages raises ValueError."""
    with pytest.raises(ValueError, match="Messages list cannot be empty"):
        convert_openai_to_pydantic([])


@pytest.mark.unit
def test_convert_openai_to_pydantic_no_user_message():
    """Test conversion with no user message raises ValueError."""
    messages = [ChatMessage(role="system", content="You are helpful")]

    with pytest.raises(ValueError, match="No user message found"):
        convert_openai_to_pydantic(messages)


@pytest.mark.unit
def test_convert_pydantic_to_openai():
    """Test conversion from Pydantic AI response to OpenAI format."""
    response = AgentResponse(
        response_text="Hello!",
        usage={
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
        finish_reason="stop",
    )

    openai_response = convert_pydantic_to_openai(response, "gpt-4o-mini")

    assert openai_response.model == "gpt-4o-mini"
    assert openai_response.object == "chat.completion"
    assert len(openai_response.choices) == 1
    assert openai_response.choices[0].message.content == "Hello!"
    assert openai_response.choices[0].finish_reason == "stop"
    assert openai_response.usage.total_tokens == 15


@pytest.mark.unit
def test_bidirectional_conversion():
    """Test bidirectional conversion (OpenAI → Pydantic → OpenAI)."""
    original_messages = [ChatMessage(role="user", content="Hello")]

    # Convert to Pydantic format
    prompt, history = convert_openai_to_pydantic(original_messages)

    # Create agent response
    agent_response = AgentResponse(
        response_text="Hi there!",
        usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        finish_reason="stop",
    )

    # Convert back to OpenAI format
    openai_response = convert_pydantic_to_openai(agent_response, "gpt-4o-mini")

    assert openai_response.choices[0].message.content == "Hi there!"
    assert openai_response.usage.total_tokens == 8
