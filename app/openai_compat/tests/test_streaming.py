"""Unit tests for StreamChunkBuilder and SSE formatting."""

import json

from app.openai_compat.streaming import StreamChunkBuilder


def test_builder_initialization() -> None:
    """Test StreamChunkBuilder initializes with correct values."""
    builder = StreamChunkBuilder(model="claude-sonnet-4-0")

    assert builder.model == "claude-sonnet-4-0"
    assert builder.completion_id.startswith("chatcmpl-")
    assert len(builder.completion_id) == 38  # "chatcmpl-" (9) + 29 hex chars = 38
    assert builder.created > 0
    assert builder.role_chunk_sent is False


def test_role_chunk_structure() -> None:
    """Test role chunk has correct structure with empty content (OpenAI SSE spec)."""
    builder = StreamChunkBuilder(model="test-model")
    chunk = builder.build_role_chunk()

    assert chunk["id"] == builder.completion_id
    assert chunk["object"] == "chat.completion.chunk"
    assert chunk["model"] == "test-model"
    assert len(chunk["choices"]) == 1
    assert chunk["choices"][0]["delta"]["role"] == "assistant"
    assert chunk["choices"][0]["delta"]["content"] == ""
    assert chunk["choices"][0]["finish_reason"] is None


def test_content_chunks_never_have_role() -> None:
    """Test content chunks never include role (only in build_role_chunk)."""
    builder = StreamChunkBuilder(model="test-model")

    # Build multiple content chunks
    first_chunk = builder.build_content_chunk("Hello")
    second_chunk = builder.build_content_chunk(" World")

    # Neither should have role
    assert "role" not in first_chunk["choices"][0]["delta"]
    assert "role" not in second_chunk["choices"][0]["delta"]

    # Both should have content
    assert first_chunk["choices"][0]["delta"]["content"] == "Hello"
    assert second_chunk["choices"][0]["delta"]["content"] == " World"
    assert first_chunk["choices"][0]["finish_reason"] is None
    assert second_chunk["choices"][0]["finish_reason"] is None


def test_multiple_content_chunks() -> None:
    """Test building multiple content chunks in sequence."""
    builder = StreamChunkBuilder(model="test-model")

    chunks: list[dict[str, object]] = []
    for text in ["Hello", " ", "World", "!"]:
        chunk = builder.build_content_chunk(text)
        chunks.append(chunk)

    # None should have role (role is only in build_role_chunk)
    for chunk in chunks:
        assert "role" not in chunk["choices"][0]["delta"]  # type: ignore[index]

    # All have content
    contents: list[object] = [c["choices"][0]["delta"]["content"] for c in chunks]  # type: ignore[index]
    assert contents == ["Hello", " ", "World", "!"]


def test_final_chunk_structure() -> None:
    """Test final chunk has correct structure with usage."""
    builder = StreamChunkBuilder(model="test-model")
    final_chunk = builder.build_final_chunk(prompt_tokens=15, completion_tokens=100)

    assert final_chunk["id"] == builder.completion_id
    assert final_chunk["object"] == "chat.completion.chunk"
    assert final_chunk["model"] == "test-model"
    assert len(final_chunk["choices"]) == 1
    assert final_chunk["choices"][0]["delta"] == {}
    assert final_chunk["choices"][0]["finish_reason"] == "stop"
    assert "usage" in final_chunk
    assert final_chunk["usage"]["prompt_tokens"] == 15
    assert final_chunk["usage"]["completion_tokens"] == 100
    assert final_chunk["usage"]["total_tokens"] == 115


def test_format_sse() -> None:
    """Test SSE formatting with correct prefix and newlines."""
    chunk = {
        "id": "chatcmpl-123",
        "object": "chat.completion.chunk",
        "choices": [{"delta": {"content": "test"}}],
    }
    sse_text = StreamChunkBuilder.format_sse(chunk)

    # Should start with "data: "
    assert sse_text.startswith("data: ")

    # Should end with double newline
    assert sse_text.endswith("\n\n")

    # Should be valid JSON between prefix and suffix
    json_part = sse_text[6:-2]  # Remove "data: " and "\n\n"
    parsed = json.loads(json_part)
    assert parsed["id"] == "chatcmpl-123"
    assert parsed["choices"][0]["delta"]["content"] == "test"


def test_chunk_json_valid() -> None:
    """Test all chunks produce valid JSON."""
    builder = StreamChunkBuilder(model="test-model")

    # Content chunk
    content_chunk = builder.build_content_chunk("Hello")
    json.dumps(content_chunk)  # Should not raise

    # Final chunk
    final_chunk = builder.build_final_chunk(10, 20)
    json.dumps(final_chunk)  # Should not raise


def test_sse_format_preserves_json() -> None:
    """Test SSE formatting preserves JSON structure."""
    builder = StreamChunkBuilder(model="test-model")
    chunk = builder.build_content_chunk("Test content")
    sse_formatted = builder.format_sse(chunk)

    # Extract JSON from SSE format
    json_str = sse_formatted.replace("data: ", "").replace("\n\n", "")
    parsed = json.loads(json_str)

    # Verify structure preserved
    assert parsed["id"] == chunk["id"]
    assert parsed["model"] == chunk["model"]
    assert parsed["choices"][0]["delta"]["content"] == "Test content"


def test_completion_id_format() -> None:
    """Test completion ID format matches OpenAI pattern."""
    builder = StreamChunkBuilder(model="test-model")

    # Should match chatcmpl-{hex_string}
    assert builder.completion_id.startswith("chatcmpl-")

    # Extract hex part
    hex_part = builder.completion_id[9:]  # After "chatcmpl-"

    # Should be 29 hex characters
    assert len(hex_part) == 29
    assert all(c in "0123456789abcdef" for c in hex_part)


def test_completion_id_unique() -> None:
    """Test each builder gets unique completion ID."""
    builder1 = StreamChunkBuilder(model="test")
    builder2 = StreamChunkBuilder(model="test")

    assert builder1.completion_id != builder2.completion_id


def test_created_timestamp_reasonable() -> None:
    """Test created timestamp is reasonable Unix timestamp."""
    import time

    before = int(time.time())
    builder = StreamChunkBuilder(model="test")
    after = int(time.time())

    assert before <= builder.created <= after


def test_full_streaming_sequence() -> None:
    """Test complete streaming sequence produces valid chunks."""
    builder = StreamChunkBuilder(model="claude-sonnet-4-0")

    # Simulate streaming response
    chunks: list[str] = []

    # Role chunk first (OpenAI SSE spec)
    role_chunk = builder.build_role_chunk()
    chunks.append(builder.format_sse(role_chunk))

    # Content chunks
    for text in ["Hello", " there", "!"]:
        chunk = builder.build_content_chunk(text)
        chunks.append(builder.format_sse(chunk))

    # Final chunk
    final = builder.build_final_chunk(prompt_tokens=5, completion_tokens=3)
    chunks.append(builder.format_sse(final))

    # Verify all chunks
    assert len(chunks) == 5  # role + 3 content + final

    # First chunk has role with empty content
    first_data: dict[str, object] = json.loads(chunks[0].replace("data: ", "").strip())
    assert first_data["choices"][0]["delta"]["role"] == "assistant"  # type: ignore[index]
    assert first_data["choices"][0]["delta"]["content"] == ""  # type: ignore[index]

    # Content chunks have no role
    for i in range(1, 4):
        content_data: dict[str, object] = json.loads(chunks[i].replace("data: ", "").strip())
        assert "role" not in content_data["choices"][0]["delta"]  # type: ignore[index]

    # Last chunk has usage
    last_data: dict[str, object] = json.loads(chunks[-1].replace("data: ", "").strip())
    assert "usage" in last_data
    assert last_data["usage"]["total_tokens"] == 8  # type: ignore[index]
