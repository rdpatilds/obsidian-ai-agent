"""Pydantic models for OpenAI-compatible API request/response schemas.

This module provides data models that conform to the OpenAI Chat Completions API
specification, enabling compatibility with Obsidian Copilot and other OpenAI-compatible clients.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Single message in chat history.

    Supports both string content (text-only) and array content (multimodal format).
    The array format is normalized to strings for downstream processing.
    """

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[dict[str, Any]]
    name: str | None = None
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request.

    Mirrors the OpenAI Chat Completions API request format.
    See: https://platform.openai.com/docs/api-reference/chat/create
    """

    model: str
    messages: list[Message] = Field(..., min_length=1)
    temperature: float | None = Field(default=1.0, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool = False
    top_p: float | None = Field(default=1.0, ge=0, le=1)
    frequency_penalty: float | None = Field(default=0, ge=-2, le=2)
    presence_penalty: float | None = Field(default=0, ge=-2, le=2)
    stop: str | list[str] | None = None
    n: int = Field(default=1, ge=1)


class Choice(BaseModel):
    """Single completion choice in non-streaming response."""

    index: int
    message: Message
    finish_reason: Literal["stop", "length", "tool_calls"] | None


class Usage(BaseModel):
    """Token usage statistics."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response (non-streaming).

    Mirrors the OpenAI Chat Completions API response format.
    """

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage


class ChoiceDelta(BaseModel):
    """Delta content for streaming chunks."""

    index: int
    delta: dict[str, Any]
    finish_reason: Literal["stop", "length"] | None = None


class ChatCompletionChunk(BaseModel):
    """Streaming chunk in SSE format.

    Used for streaming responses. The first chunk includes role: "assistant",
    subsequent chunks contain content deltas, and the final chunk includes
    finish_reason and usage.
    """

    id: str
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int
    model: str
    choices: list[ChoiceDelta]
    usage: Usage | None = None
