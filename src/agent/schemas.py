"""Agent schemas for request/response models and dependencies.

This module defines Pydantic models for agent execution, including:
- AgentDependencies: Dependency injection container for tools
- AgentRequest: Input to agent execution with prompt and message history
- AgentResponse: Output from agent execution with response text and metadata
"""

import uuid
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field


class AgentDependencies(BaseModel):
    """Dependencies injected into agent tools.

    Attributes:
        http_client: Async HTTP client for external API calls.
        openai_api_key: API key for OpenAI model access.
        vault_path: Path to the Obsidian vault directory.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    http_client: httpx.AsyncClient
    openai_api_key: str
    vault_path: str


class AgentRequest(BaseModel):
    """Input to agent execution.

    Attributes:
        prompt: User's query or instruction.
        message_history: Pydantic AI native message history (ModelRequest/ModelResponse).
        request_id: Unique identifier for request tracing.
    """

    prompt: str
    message_history: list[Any] = Field(default_factory=list)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AgentResponse(BaseModel):
    """Output from agent execution.

    Attributes:
        response_text: Agent's text response.
        tool_calls: List of tools invoked during execution.
        usage: Token usage statistics.
        finish_reason: Why the generation stopped.
    """

    response_text: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    usage: dict[str, int] = Field(default_factory=dict)
    finish_reason: str = "stop"


# Structured Output Examples
# These can be used with Pydantic AI's result_type parameter for validated responses


class StructuredNote(BaseModel):
    """Example structured output for note creation/editing.

    This demonstrates how to use Pydantic AI's result validation
    for structured outputs when not using OpenAI compatibility mode.

    Example usage:
        agent = Agent(
            model="openai:gpt-4o-mini",
            result_type=StructuredNote,
        )
        result = await agent.run("Create a note about Python")
        note: StructuredNote = result.data
    """

    title: str = Field(description="Title of the note")
    content: str = Field(description="Main content of the note")
    tags: list[str] = Field(default_factory=list, description="Tags for organization")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")


class StructuredSummary(BaseModel):
    """Example structured output for content summarization.

    Demonstrates Pydantic AI's ability to enforce structured responses
    with automatic validation and retries (via result_retries).
    """

    summary: str = Field(description="Concise summary of the content")
    key_points: list[str] = Field(description="Main points extracted")
    sentiment: str = Field(description="Overall sentiment (positive/neutral/negative)")
    word_count: int = Field(ge=0, description="Approximate word count of summary")
