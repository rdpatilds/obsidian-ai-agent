# Research Report: OpenAI-Compatible Streaming Implementation

**Date**: 2025-11-05
**Focus**: Implementing streaming with Pydantic AI `agent.iter()` and FastAPI SSE

---

## 1. Pydantic AI Streaming Pattern

### Core Usage

```python
from pydantic_ai.messages import PartDeltaEvent, TextPartDelta

async def stream_agent_text(
    agent: Agent,
    user_prompt: str,
    message_history: list[ModelMessage] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream text deltas from agent."""
    async with agent.iter(user_prompt, message_history=message_history) as run:
        async for node in run:
            if Agent.is_model_request_node(node):
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        if isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                if event.delta.content_delta:
                                    yield event.delta.content_delta

            elif Agent.is_end_node(node):
                # Access usage: run.usage()
                break
```

### Node Types
- `UserPromptNode` - Initial prompt
- `ModelRequestNode` - LLM streaming (extract text here)
- `CallToolsNode` - Tool execution
- `End` - Completion (access `run.usage()`)

---

## 2. Message Conversion

### OpenAI → Pydantic AI

```python
from pydantic_ai.messages import (
    ModelMessage, ModelRequest, ModelResponse,
    SystemPromptPart, UserPromptPart, TextPart, RequestUsage
)

def convert_to_pydantic_messages(
    openai_messages: list[dict],
) -> tuple[str, list[ModelMessage] | None]:
    """Convert OpenAI messages to Pydantic AI format.

    Returns:
        (user_prompt, message_history)
        Last message becomes prompt, rest become history.
    """
    # Last user message is the prompt
    user_prompt = normalize_content(openai_messages[-1]["content"])

    if len(openai_messages) == 1:
        return user_prompt, None

    # Convert history
    history: list[ModelMessage] = []
    for msg in openai_messages[:-1]:
        content = normalize_content(msg["content"])

        if msg["role"] == "system":
            history.append(ModelRequest(parts=[SystemPromptPart(content=content)]))
        elif msg["role"] == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif msg["role"] == "assistant":
            history.append(ModelResponse(
                parts=[TextPart(content=content)],
                model_name="unknown",
                usage=RequestUsage(input_tokens=0, output_tokens=0, total_tokens=0),
                finish_reason="stop"
            ))

    return user_prompt, history if history else None

def normalize_content(content: str | list[dict]) -> str:
    """Flatten array content to string."""
    if isinstance(content, str):
        return content

    parts = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
        elif isinstance(item, dict) and "text" in item:
            parts.append(item["text"])

    return " ".join(parts)
```

---

## 3. OpenAI Streaming Format

### Chunk Structure

**First chunk** (includes role):
```json
{
  "id": "chatcmpl-xxxxx",
  "object": "chat.completion.chunk",
  "created": 1736083200,
  "model": "claude-sonnet-4-0",
  "choices": [{
    "index": 0,
    "delta": {"role": "assistant", "content": ""},
    "finish_reason": null
  }]
}
```

**Content chunks**:
```json
{
  "choices": [{
    "delta": {"content": "Hello"},
    "finish_reason": null
  }]
}
```

**Final chunk** (with usage):
```json
{
  "choices": [{
    "delta": {},
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 100,
    "total_tokens": 115
  }
}
```

**Termination**: `data: [DONE]\n\n`

### Required Fields
- `id`, `object`, `created`, `model`, `choices` - Always required
- `choices[0].delta.role` - First chunk only
- `choices[0].delta.content` - Content chunks only
- `choices[0].finish_reason` - `null` until final chunk
- `usage` - Final chunk only

---

## 4. FastAPI Implementation

### StreamChunkBuilder Helper

```python
import json
import time
import uuid

class StreamChunkBuilder:
    """Build OpenAI streaming chunks."""

    def __init__(self, model: str):
        self.completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        self.created = int(time.time())
        self.model = model
        self.first_chunk_sent = False

    def build_content_chunk(self, content: str) -> dict:
        delta = {"content": content}
        if not self.first_chunk_sent:
            delta["role"] = "assistant"
            self.first_chunk_sent = True

        return {
            "id": self.completion_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "choices": [{
                "index": 0,
                "delta": delta,
                "finish_reason": None,
            }],
        }

    def build_final_chunk(self, prompt_tokens: int, completion_tokens: int) -> dict:
        return {
            "id": self.completion_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    @staticmethod
    def format_sse(chunk: dict) -> str:
        """Format as SSE: 'data: {...}\\n\\n'"""
        return f"data: {json.dumps(chunk)}\n\n"
```

### Streaming Endpoint

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    if request.stream:
        return StreamingResponse(
            stream_openai_response(request, vault_agent),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        # Non-streaming implementation
        pass

async def stream_openai_response(
    request: ChatCompletionRequest,
    agent: Agent,
) -> AsyncGenerator[str, None]:
    """Generate OpenAI-compatible SSE stream."""
    builder = StreamChunkBuilder(model=request.model)

    try:
        # Convert messages
        user_prompt, message_history = convert_to_pydantic_messages(request.messages)

        # Stream agent response
        async for text_delta in stream_agent_text(agent, user_prompt, message_history):
            chunk = builder.build_content_chunk(text_delta)
            yield builder.format_sse(chunk)

        # Send final chunk (TODO: get actual usage from run.usage())
        final_chunk = builder.build_final_chunk(
            prompt_tokens=0,
            completion_tokens=0,
        )
        yield builder.format_sse(final_chunk)
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error("agent.stream_failed", error=str(e), exc_info=True)
        error_chunk = {"error": {"message": str(e), "type": "server_error"}}
        yield builder.format_sse(error_chunk)
        yield "data: [DONE]\n\n"
```

---

## 5. Complete Flow

```
OpenAI Request
    ↓
convert_to_pydantic_messages() → (user_prompt, message_history)
    ↓
agent.iter(user_prompt, message_history)
    ↓
ModelRequestNode.stream() → PartDeltaEvent → TextPartDelta.content_delta
    ↓
StreamChunkBuilder.build_content_chunk(text_delta)
    ↓
format_sse(chunk) → "data: {...}\n\n"
    ↓
FastAPI StreamingResponse
```

---

## 6. Key Implementation Notes

### Usage Access
```python
# After End node in agent.iter()
usage = run.usage()
usage.input_tokens      # Prompt tokens
usage.output_tokens     # Completion tokens
usage.total_tokens      # Total
```

### SSE Format Rules
- Format: `data: <JSON>\n\n` (double newline required)
- JSON must be single line (no newlines in JSON)
- Terminate with: `data: [DONE]\n\n`

### Production Considerations
- Check client disconnection: `await request.is_disconnected()`
- Buffer small deltas to reduce overhead
- Use `UsageLimits` to prevent runaway costs
- Log comprehensively: `agent.stream_started`, `agent.stream_completed`, `agent.stream_failed`

---

## Next Steps

1. Implement `StreamChunkBuilder` in `app/shared/utils.py`
2. Add message conversion functions to `app/shared/utils.py`
3. Add streaming endpoint to `app/agent/routes.py`
4. Test with Obsidian Copilot
5. Add proper usage tracking from `run.usage()`

---

**Status**: ✅ Ready for Implementation
