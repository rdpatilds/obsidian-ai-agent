"""Type definitions for agent interactions."""

from pydantic import BaseModel, Field


class AgentUsage(BaseModel):
    """Token usage statistics."""

    request_tokens: int = Field(..., description="Tokens in request")
    response_tokens: int = Field(..., description="Tokens in response")
    total_tokens: int = Field(..., description="Total tokens used")


class AgentResponse(BaseModel):
    """Agent response with output and metadata."""

    output: str = Field(..., description="Agent response text")
    usage: AgentUsage = Field(..., description="Token usage")
