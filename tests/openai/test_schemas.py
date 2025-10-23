"""Unit tests for OpenAI API schemas."""

import pytest

from src.openai.schemas import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    ChunkChoice,
    DeltaMessage,
    Usage,
)


@pytest.mark.unit
def test_chat_message_validation():
    """Test ChatMessage validation with different roles."""
    # Valid user message
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

    # Valid assistant message
    msg = ChatMessage(role="assistant", content="Hi there")
    assert msg.role == "assistant"

    # Valid system message
    msg = ChatMessage(role="system", content="You are helpful")
    assert msg.role == "system"


@pytest.mark.unit
def test_chat_completion_request_required_fields():
    """Test ChatCompletionRequest with required fields only."""
    request = ChatCompletionRequest(
        messages=[ChatMessage(role="user", content="Hello")]
    )
    assert request.model == "gpt-4o-mini"
    assert len(request.messages) == 1
    assert request.temperature is None  # No default, let provider decide
    assert request.top_p is None  # No default, let provider decide
    assert request.stream is False


@pytest.mark.unit
def test_chat_completion_request_all_fields():
    """Test ChatCompletionRequest with all optional fields."""
    request = ChatCompletionRequest(
        model="gpt-4",
        messages=[ChatMessage(role="user", content="Hello")],
        temperature=0.7,
        max_tokens=100,
        stream=True,
        top_p=0.9,
        n=2,
        stop=["END"],
    )
    assert request.model == "gpt-4"
    assert request.temperature == 0.7
    assert request.max_tokens == 100
    assert request.stream is True
    assert request.top_p == 0.9
    assert request.n == 2
    assert request.stop == ["END"]


@pytest.mark.unit
def test_chat_completion_response_serialization():
    """Test ChatCompletionResponse serialization."""
    response = ChatCompletionResponse(
        id="chatcmpl-123",
        created=1234567890,
        model="gpt-4o-mini",
        choices=[
            Choice(
                index=0,
                message=ChatMessage(role="assistant", content="Hello!"),
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )

    assert response.id == "chatcmpl-123"
    assert response.object == "chat.completion"
    assert len(response.choices) == 1
    assert response.usage.total_tokens == 15

    # Test serialization
    data = response.model_dump()
    assert data["id"] == "chatcmpl-123"
    assert data["object"] == "chat.completion"


@pytest.mark.unit
def test_chat_completion_chunk_for_streaming():
    """Test ChatCompletionChunk for streaming."""
    chunk = ChatCompletionChunk(
        id="chatcmpl-123",
        created=1234567890,
        model="gpt-4o-mini",
        choices=[
            ChunkChoice(
                index=0, delta=DeltaMessage(content="Hello"), finish_reason=None
            )
        ],
    )

    assert chunk.object == "chat.completion.chunk"
    assert chunk.choices[0].delta.content == "Hello"
    assert chunk.choices[0].finish_reason is None


@pytest.mark.unit
def test_multimodal_content():
    """Test ChatMessage with multimodal content."""
    msg = ChatMessage(
        role="user",
        content=[
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}},
        ],
    )
    assert msg.role == "user"
    assert isinstance(msg.content, list)
    assert len(msg.content) == 2
