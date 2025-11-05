"""Schemas for agent testing endpoint."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request for agent chat."""

    message: str = Field(..., min_length=1, description="User message")


class ChatResponse(BaseModel):
    """Response from agent chat."""

    response: str = Field(..., description="Agent response")
    usage: dict[str, int] = Field(..., description="Token usage")
