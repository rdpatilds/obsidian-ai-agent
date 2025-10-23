"""OpenAI API-compatible request and response schemas.

This module defines Pydantic models that match the OpenAI API specification for:
- Chat completion requests and responses
- Streaming chunks
- Usage statistics
- Message formats
"""

from typing import Any, Literal

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """OpenAI chat message format.

    Attributes:
        role: Message role (system, user, assistant, tool).
        content: Message content (text or multimodal).
        name: Optional name for the message.
        tool_calls: Tool calls made by assistant.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]] | None = None
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ChatCompletionRequest(BaseModel):
    """Request to /v1/chat/completions endpoint.

    Attributes:
        model: Model identifier (e.g., "gpt-4o-mini").
        messages: List of conversation messages.
        temperature: Sampling temperature (0-2).
        max_tokens: Maximum tokens to generate.
        stream: Whether to stream the response.
        top_p: Nucleus sampling parameter.
        n: Number of completions to generate.
        stop: Stop sequences.
    """

    model: str = "gpt-4o-mini"
    messages: list[ChatMessage]
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool = False
    top_p: float | None = None
    n: int = 1
    stop: str | list[str] | None = None


class Usage(BaseModel):
    """Token usage statistics.

    Attributes:
        prompt_tokens: Tokens in the prompt.
        completion_tokens: Tokens in the completion.
        total_tokens: Sum of prompt and completion tokens.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Choice(BaseModel):
    """A single completion choice.

    Attributes:
        index: Choice index.
        message: The generated message.
        finish_reason: Why generation stopped.
    """

    index: int
    message: ChatMessage
    finish_reason: str | None = None


class ChatCompletionResponse(BaseModel):
    """Response from /v1/chat/completions endpoint.

    Attributes:
        id: Unique completion ID.
        object: Object type ("chat.completion").
        created: Unix timestamp.
        model: Model used.
        choices: List of completion choices.
        usage: Token usage statistics.
    """

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage


class DeltaMessage(BaseModel):
    """Delta message for streaming chunks.

    Attributes:
        role: Message role (only in first chunk).
        content: Content delta.
    """

    role: str | None = None
    content: str | None = None


class ChunkChoice(BaseModel):
    """Choice in streaming chunk.

    Attributes:
        index: Choice index.
        delta: Delta message.
        finish_reason: Why generation stopped.
    """

    index: int
    delta: DeltaMessage
    finish_reason: str | None = None


class ChatCompletionChunk(BaseModel):
    """Streaming chunk from /v1/chat/completions.

    Attributes:
        id: Unique completion ID.
        object: Object type ("chat.completion.chunk").
        created: Unix timestamp.
        model: Model used.
        choices: List of chunk choices.
    """

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChunkChoice]
