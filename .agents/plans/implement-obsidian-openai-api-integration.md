# Feature: OpenAI-Compatible API Integration for Obsidian Copilot

The following plan should be complete, but it's important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Implement a complete OpenAI-compatible chat completions API endpoint (`/v1/chat/completions`) that enables Obsidian Copilot plugin integration with the Paddy agent. This feature provides streaming and non-streaming responses, full message history support, proper CORS configuration, and maintains compatibility with the OpenAI Chat Completions API specification while using Pydantic AI's `agent.iter()` for execution.

The implementation follows Vertical Slice Architecture (VSA) patterns, uses the existing vault_agent system prompt from `app/core/agents/base.py`, implements structured logging, maintains strict type safety, and provides comprehensive testing coverage.

## User Story

As an **Obsidian user**
I want to **use the Paddy AI agent through the Obsidian Copilot plugin**
So that **I can interact with my vault using natural language queries directly within Obsidian**

## Problem Statement

The Obsidian Copilot plugin requires an OpenAI-compatible API endpoint to communicate with custom AI agents. Currently, the Paddy agent only has a basic test endpoint (`/agent/chat`) that doesn't conform to OpenAI's API specification. Users cannot integrate Paddy with Obsidian Copilot because:

1. No OpenAI-compatible `/v1/chat/completions` endpoint exists
2. Message history handling is not implemented
3. Streaming responses are not supported
4. CORS is not configured for Obsidian app origins
5. Request/response formats don't match OpenAI specification

## Solution Statement

Implement a production-ready OpenAI-compatible API integration by:

1. Creating `/v1/chat/completions` endpoint with streaming and non-streaming support
2. Converting OpenAI message format to Pydantic AI message format for history handling
3. Using `agent.iter()` for streaming text deltas and formatting as Server-Sent Events (SSE)
4. Configuring CORS for Obsidian app origins (`app://obsidian.md`, `capacitor://localhost`)
5. Implementing proper error handling, logging, and validation
6. Providing user documentation for Obsidian Copilot setup

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: High
**Primary Systems Affected**: Agent routing, message handling, streaming infrastructure, CORS middleware
**Dependencies**:
- `pydantic-ai` (already installed) - For agent.iter() streaming
- `fastapi` (already installed) - For StreamingResponse and SSE
- Research findings in `.agents/report/research-report-obsidian-copilot-openai-api.md`
- Research findings in `.agents/report/research-report-streaming-implementation.md`

---

## CONTEXT REFERENCES

### Relevant Codebase Files IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `app/core/agents/base.py` (lines 23-38) - Why: Contains vault_agent with system prompt we MUST use
- `app/core/config.py` (lines 45-46) - Why: CORS allowed_origins configuration to update
- `app/core/middleware.py` - Why: CORS setup pattern to verify/update
- `app/agent/routes.py` - Why: Existing agent endpoint pattern to follow
- `app/agent/models.py` - Why: Current schema structure (will be replaced with OpenAI format)
- `app/shared/utils.py` - Why: Location for new utility functions (message conversion, content normalization)
- `app/shared/schemas.py` - Why: Shared schema patterns for pagination (reference only)
- `app/core/logging.py` - Why: Structured logging pattern to follow
- `docs/logging-standard.md` - Why: Event naming taxonomy for agent streaming events
- `.agents/reference/vsa-patterns.md` - Why: Vertical slice architecture principles

### New Files to Create

- `app/openai_compat/models.py` - Pydantic models for OpenAI request/response schemas
- `app/openai_compat/routes.py` - `/v1/chat/completions` endpoint implementation
- `app/openai_compat/streaming.py` - StreamChunkBuilder and SSE utilities
- `app/openai_compat/converters.py` - OpenAI ↔ Pydantic AI message conversion
- `app/openai_compat/tests/test_models.py` - Model validation tests
- `app/openai_compat/tests/test_routes.py` - Endpoint integration tests
- `app/openai_compat/tests/test_streaming.py` - Streaming functionality tests
- `app/openai_compat/tests/test_converters.py` - Message conversion tests
- `.agents/reference/obsidian-copilot-setup.md` - User setup guide

### Relevant Documentation YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [.agents/report/research-report-obsidian-copilot-openai-api.md](.agents/report/research-report-obsidian-copilot-openai-api.md)
  - Specific sections: Message Content Format, Endpoint Path Construction, Implementation Requirements
  - Why: Contains exact OpenAI format specifications and content normalization logic
- [.agents/report/research-report-streaming-implementation.md](.agents/report/research-report-streaming-implementation.md)
  - Specific sections: Pydantic AI Streaming Pattern, OpenAI Streaming Format, FastAPI Implementation
  - Why: Complete agent.iter() usage patterns and SSE chunk formatting
- [docs/logging-standard.md](docs/logging-standard.md)
  - Specific section: Agent Domain (lines 160-230)
  - Why: Event naming for agent.stream_started, agent.stream_completed, agent.llm.*
- [.agents/reference/vsa-patterns.md](.agents/reference/vsa-patterns.md)
  - Specific sections: Feature Slices, Core vs Shared Decision Framework
  - Why: Understand where code belongs in VSA structure

### Patterns to Follow

**Naming Conventions:**
```python
# Feature slice structure (from vsa-patterns.md)
app/openai_compat/
├── routes.py              # FastAPI endpoints
├── models.py              # Request/response schemas
├── streaming.py           # Streaming utilities
├── converters.py          # Message format conversion
└── tests/                 # Colocated tests

# Use existing utilities from app.shared.utils
from app.shared.utils import function_name
```

**Error Handling:**
```python
# Pattern from app/agent/routes.py:46-56
try:
    result = await vault_agent.run(request.message, deps=AgentDeps())
    logger.info("agent.chat.completed", ...)
    return response
except Exception as e:
    logger.error(
        "agent.chat.failed",
        error=str(e),
        error_type=type(e).__name__,
        exc_info=True,
    )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"...: {e!s}",
    ) from e
```

**Logging Pattern:**
```python
# Pattern from docs/logging-standard.md
from app.core.logging import get_logger

logger = get_logger(__name__)

# Lifecycle events
logger.info("agent.stream_started", model=model, message_count=len(messages))
logger.info("agent.stream_completed", total_tokens=usage.total_tokens)
logger.error("agent.stream_failed", error=str(e), exc_info=True)

# LLM events
logger.info("agent.llm.call_completed",
           model="claude-sonnet-4-0",
           tokens_prompt=usage.input_tokens,
           tokens_completion=usage.output_tokens,
           duration_ms=duration)
```

**Type Safety Pattern:**
```python
# From docs/mypy-standard.md - all functions must have complete annotations
from typing import AsyncGenerator
from collections.abc import Sequence

async def stream_agent_text(
    agent: Agent,
    user_prompt: str,
    message_history: Sequence[ModelMessage] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream text deltas from agent."""
    # Implementation
```

**Async Streaming Pattern (from research reports):**
```python
# From research-report-streaming-implementation.md
from pydantic_ai.messages import PartDeltaEvent, TextPartDelta

async with agent.iter(user_prompt, message_history=message_history) as run:
    async for node in run:
        if Agent.is_model_request_node(node):
            async with node.stream(run.ctx) as request_stream:
                async for event in request_stream:
                    if isinstance(event, PartDeltaEvent):
                        if isinstance(event.delta, TextPartDelta):
                            if event.delta.content_delta:
                                yield event.delta.content_delta
```

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation - Data Models & Utilities

Create the foundational data structures and utility functions for OpenAI format handling and message conversion.

**Tasks:**
- Create Pydantic models for OpenAI request/response schemas
- Implement content normalization (string vs array format)
- Implement OpenAI → Pydantic AI message conversion
- Create StreamChunkBuilder utility for SSE formatting
- Write unit tests for models and converters

### Phase 2: Core Implementation - Streaming & Endpoints

Implement the core agent streaming logic and FastAPI endpoint with OpenAI compatibility.

**Tasks:**
- Implement agent.iter() text streaming wrapper
- Create StreamingResponse generator for SSE
- Implement `/v1/chat/completions` endpoint (streaming + non-streaming)
- Add proper error handling and logging
- Integration tests for streaming and non-streaming modes

### Phase 3: Integration - CORS & Router Registration

Integrate the new OpenAI-compatible endpoint with the existing application infrastructure.

**Tasks:**
- Update CORS configuration for Obsidian origins
- Register router in main.py
- Verify middleware applies correctly
- Integration tests for CORS headers
- End-to-end testing with actual requests

### Phase 4: Testing & Validation - Comprehensive Coverage

Ensure all components work correctly through comprehensive testing.

**Tasks:**
- Unit tests for all components (models, converters, streaming)
- Integration tests for endpoint workflows
- CORS validation tests
- Error handling tests (validation, agent failures, etc.)
- Manual validation with curl and test client

### Phase 5: Documentation - User Setup Guide

Create clear documentation for end users to configure Obsidian Copilot.

**Tasks:**
- Write Obsidian Copilot setup guide
- Document baseURL configuration
- Provide troubleshooting tips
- Include example requests/responses

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### CREATE app/openai_compat/models.py

- **IMPLEMENT**: OpenAI request/response Pydantic models
- **PATTERN**: Model structure from research-report-obsidian-copilot-openai-api.md (Section 3.1)
- **IMPORTS**:
  ```python
  from pydantic import BaseModel, Field
  from typing import Literal, Any
  from collections.abc import Sequence
  ```
- **MODELS TO CREATE**:
  - `Message` - role, content (str | list[dict]), name, tool_calls, tool_call_id
  - `ChatCompletionRequest` - model, messages, temperature, max_tokens, stream, top_p, etc.
  - `Choice` - index, message, finish_reason
  - `Usage` - prompt_tokens, completion_tokens, total_tokens
  - `ChatCompletionResponse` - id, object, created, model, choices, usage
  - `ChoiceDelta` - role, content (for streaming)
  - `ChatCompletionChunk` - id, object, created, model, choices (for streaming)
- **GOTCHA**: Use `Literal` types for role and finish_reason values
- **GOTCHA**: content field must support both `str` and `list[dict[str, Any]]` formats
- **VALIDATE**: `uv run mypy app/openai_compat/models.py`

### CREATE app/openai_compat/converters.py

- **IMPLEMENT**: Message format conversion utilities
- **PATTERN**: Conversion logic from research-report-obsidian-copilot-openai-api.md (Section 4.2)
- **IMPORTS**:
  ```python
  from pydantic_ai.messages import (
      ModelMessage, ModelRequest, ModelResponse,
      SystemPromptPart, UserPromptPart, TextPart, RequestUsage
  )
  from app.openai_compat.models import Message as OpenAIMessage
  from collections.abc import Sequence
  ```
- **FUNCTIONS TO CREATE**:
  - `normalize_content(content: str | list[dict[str, Any]]) -> str` - Flatten array to string
  - `convert_to_pydantic_messages(openai_messages: Sequence[OpenAIMessage]) -> tuple[str, Sequence[ModelMessage] | None]` - Returns (user_prompt, message_history)
- **GOTCHA**: Last message becomes user_prompt, not part of history
- **GOTCHA**: System messages in history must use SystemPromptPart, not UserPromptPart
- **GOTCHA**: Assistant messages need RequestUsage even if we don't have actual token counts (use 0)
- **VALIDATE**: `uv run mypy app/openai_compat/converters.py`

### CREATE app/openai_compat/streaming.py

- **IMPLEMENT**: StreamChunkBuilder and SSE formatting
- **PATTERN**: Chunk builder from research-report-streaming-implementation.md (Section 4.1)
- **IMPORTS**:
  ```python
  import json
  import time
  import uuid
  from collections.abc import AsyncGenerator
  ```
- **CLASS TO CREATE**: `StreamChunkBuilder`
  - `__init__(self, model: str)` - Generate completion_id, created timestamp
  - `build_content_chunk(self, content: str) -> dict[str, Any]` - Build delta chunk with role on first call
  - `build_final_chunk(self, prompt_tokens: int, completion_tokens: int) -> dict[str, Any]` - Build termination chunk with usage
  - `@staticmethod format_sse(chunk: dict[str, Any]) -> str` - Format as SSE: `data: {...}\n\n`
- **GOTCHA**: First chunk must include `delta: {"role": "assistant", "content": ""}`
- **GOTCHA**: Final chunk has empty delta `{}` and `finish_reason: "stop"`
- **GOTCHA**: SSE format requires double newline `\n\n` after each chunk
- **VALIDATE**: `uv run mypy app/openai_compat/streaming.py`

### CREATE app/openai_compat/routes.py (Part 1: Streaming Helper)

- **IMPLEMENT**: Agent streaming text extraction helper
- **PATTERN**: agent.iter() usage from research-report-streaming-implementation.md (Section 1.1)
- **IMPORTS**:
  ```python
  from pydantic_ai import Agent
  from pydantic_ai.messages import PartDeltaEvent, TextPartDelta, ModelMessage
  from collections.abc import AsyncGenerator, Sequence
  from app.core.logging import get_logger
  ```
- **FUNCTION TO CREATE**:
  ```python
  async def stream_agent_text(
      agent: Agent,
      user_prompt: str,
      message_history: Sequence[ModelMessage] | None = None,
  ) -> AsyncGenerator[str, None]:
  ```
- **IMPLEMENTATION**:
  - Use `async with agent.iter(user_prompt, message_history=message_history) as run:`
  - Iterate nodes with `async for node in run:`
  - Check `if Agent.is_model_request_node(node):`
  - Stream with `async with node.stream(run.ctx) as request_stream:`
  - Filter for `PartDeltaEvent` with `TextPartDelta`
  - Yield `event.delta.content_delta`
  - Break on `Agent.is_end_node(node)`
- **GOTCHA**: Must check `if event.delta.content_delta:` before yielding (can be None)
- **VALIDATE**: `uv run mypy app/openai_compat/routes.py`

### CREATE app/openai_compat/routes.py (Part 2: SSE Generator)

- **IMPLEMENT**: OpenAI-compatible SSE streaming generator
- **PATTERN**: SSE streaming from research-report-streaming-implementation.md (Section 4.3)
- **IMPORTS**:
  ```python
  from app.openai_compat.models import ChatCompletionRequest
  from app.openai_compat.streaming import StreamChunkBuilder
  from app.openai_compat.converters import convert_to_pydantic_messages
  from app.core.agents import vault_agent
  ```
- **FUNCTION TO CREATE**:
  ```python
  async def stream_openai_response(
      request: ChatCompletionRequest,
  ) -> AsyncGenerator[str, None]:
  ```
- **IMPLEMENTATION**:
  - Create `StreamChunkBuilder(model=request.model)`
  - Log `agent.stream_started`
  - Convert messages: `user_prompt, message_history = convert_to_pydantic_messages(request.messages)`
  - Stream text: `async for text_delta in stream_agent_text(vault_agent, user_prompt, message_history):`
  - Build and yield chunks: `chunk = builder.build_content_chunk(text_delta)` then `yield builder.format_sse(chunk)`
  - After streaming, build and yield final chunk with usage
  - Yield `"data: [DONE]\n\n"` termination signal
  - Wrap in try/except, log errors with `agent.stream_failed`
- **GOTCHA**: Must access `run.usage()` AFTER End node to get token counts
- **GOTCHA**: Must handle exceptions and still send valid SSE (error chunk + [DONE])
- **VALIDATE**: `uv run mypy app/openai_compat/routes.py`

### CREATE app/openai_compat/routes.py (Part 3: Main Endpoint)

- **IMPLEMENT**: `/v1/chat/completions` POST endpoint
- **PATTERN**: Route structure from app/agent/routes.py, streaming from research
- **IMPORTS**:
  ```python
  from fastapi import APIRouter, HTTPException, status
  from fastapi.responses import StreamingResponse
  from app.openai_compat.models import ChatCompletionRequest, ChatCompletionResponse
  ```
- **ROUTER**: `router = APIRouter(prefix="/v1", tags=["openai-compat"])`
- **ENDPOINT**:
  ```python
  @router.post("/chat/completions")
  async def chat_completions(request: ChatCompletionRequest) -> StreamingResponse | ChatCompletionResponse:
  ```
- **IMPLEMENTATION**:
  - Validate: `if not request.messages: raise HTTPException(400, "messages required")`
  - Log `request.http_received`
  - If `request.stream == True`: return `StreamingResponse(stream_openai_response(request), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"})`
  - Else: implement non-streaming (call agent.run(), build ChatCompletionResponse)
  - Log `request.http_completed` or `request.http_failed`
- **GOTCHA**: Non-streaming must return full response with usage, not stream
- **GOTCHA**: Must set proper SSE headers for streaming response
- **VALIDATE**: `uv run mypy app/openai_compat/routes.py`

### UPDATE app/main.py

- **ADD**: Import and register openai_compat router
- **PATTERN**: Router registration from app/main.py:78-79
- **IMPORTS**: `from app.openai_compat.routes import router as openai_compat_router`
- **IMPLEMENTATION**: Add `app.include_router(openai_compat_router)` after existing agent_router
- **GOTCHA**: Register BEFORE app.get("/") root endpoint so it doesn't interfere
- **VALIDATE**: `uv run python -c "from app.main import app; print([r.path for r in app.routes])"`

### UPDATE app/core/config.py

- **UPDATE**: CORS allowed_origins to include Obsidian app origins
- **PATTERN**: Settings structure from app/core/config.py:45-46
- **IMPLEMENTATION**: Change line 46 from:
  ```python
  allowed_origins: list[str] = ["http://localhost:3000", "http://localhost:8123"]
  ```
  To:
  ```python
  allowed_origins: list[str] = [
      "http://localhost:3000",
      "http://localhost:8123",
      "app://obsidian.md",
      "capacitor://localhost",
  ]
  ```
- **GOTCHA**: Obsidian uses custom protocol schemes (app://, capacitor://)
- **VALIDATE**: `uv run python -c "from app.core.config import get_settings; print(get_settings().allowed_origins)"`

### CREATE app/openai_compat/tests/test_models.py

- **IMPLEMENT**: Unit tests for Pydantic model validation
- **PATTERN**: Test structure from app/shared/tests/test_models.py
- **IMPORTS**:
  ```python
  import pytest
  from app.openai_compat.models import Message, ChatCompletionRequest, ChatCompletionResponse
  ```
- **TESTS TO CREATE**:
  - `test_message_with_string_content()` - Validate string content
  - `test_message_with_array_content()` - Validate multimodal array content
  - `test_chat_completion_request_minimal()` - Required fields only
  - `test_chat_completion_request_full()` - All optional fields
  - `test_chat_completion_request_validation()` - Invalid data raises ValidationError
  - `test_chat_completion_response_structure()` - Response format validation
- **GOTCHA**: Test both content formats (string and array)
- **VALIDATE**: `uv run pytest app/openai_compat/tests/test_models.py -v`

### CREATE app/openai_compat/tests/test_converters.py

- **IMPLEMENT**: Unit tests for message conversion
- **PATTERN**: Test structure from existing test files
- **IMPORTS**:
  ```python
  from app.openai_compat.converters import normalize_content, convert_to_pydantic_messages
  from app.openai_compat.models import Message
  from pydantic_ai.messages import ModelRequest, ModelResponse
  ```
- **TESTS TO CREATE**:
  - `test_normalize_content_string()` - String input returns string
  - `test_normalize_content_array()` - Array with text objects flattened
  - `test_convert_single_message()` - Single user message (no history)
  - `test_convert_with_history()` - Multiple messages create history
  - `test_convert_with_system_message()` - System message in history
  - `test_convert_preserves_order()` - Message order maintained
- **GOTCHA**: Verify last message becomes prompt, not history
- **VALIDATE**: `uv run pytest app/openai_compat/tests/test_converters.py -v`

### CREATE app/openai_compat/tests/test_streaming.py

- **IMPLEMENT**: Unit tests for StreamChunkBuilder
- **PATTERN**: Test structure from existing test files
- **IMPORTS**:
  ```python
  import json
  from app.openai_compat.streaming import StreamChunkBuilder
  ```
- **TESTS TO CREATE**:
  - `test_builder_initialization()` - IDs and timestamps created
  - `test_first_chunk_has_role()` - First chunk includes role
  - `test_subsequent_chunks_no_role()` - Following chunks have no role
  - `test_final_chunk_structure()` - Final chunk has usage and finish_reason
  - `test_format_sse()` - SSE format with double newline
  - `test_chunk_json_valid()` - All chunks are valid JSON
- **GOTCHA**: Verify completion_id format matches `chatcmpl-{29 hex chars}`
- **VALIDATE**: `uv run pytest app/openai_compat/tests/test_streaming.py -v`

### CREATE app/openai_compat/tests/test_routes.py

- **IMPLEMENT**: Integration tests for /v1/chat/completions endpoint
- **PATTERN**: Integration test from app/agent/tests/test_routes.py
- **IMPORTS**:
  ```python
  import pytest
  from httpx import AsyncClient, ASGITransport
  from app.main import app
  ```
- **TESTS TO CREATE**:
  - `test_chat_completions_non_streaming()` - Full response mode
  - `test_chat_completions_streaming()` - SSE streaming mode
  - `test_chat_completions_with_history()` - Message history handling
  - `test_chat_completions_validation_error()` - Empty messages rejected
  - `test_chat_completions_content_normalization()` - Array content handled
  - `test_cors_headers_present()` - CORS headers in response
- **GOTCHA**: Streaming test must parse SSE format and verify chunks
- **GOTCHA**: Use `AsyncClient` with `ASGITransport` for async endpoint testing
- **VALIDATE**: `uv run pytest app/openai_compat/tests/test_routes.py -v`

### CREATE .agents/reference/obsidian-copilot-setup.md

- **IMPLEMENT**: User guide for Obsidian Copilot configuration
- **PATTERN**: Clear step-by-step instructions with screenshots descriptions
- **SECTIONS TO CREATE**:
  1. **Prerequisites** - Paddy running on localhost:8123, Obsidian Copilot installed
  2. **Configuration Steps**:
     - Open Obsidian Settings → Copilot
     - Add Custom Model
     - Set Provider: OpenAI
     - Set Base URL: `http://localhost:8123/v1`
     - Set API Key: Any non-empty string (not validated currently)
     - Set Model Name: `claude-sonnet-4-0` (can be any string)
  3. **Verification** - How to test the connection
  4. **Troubleshooting**:
     - CORS errors (check allowed_origins)
     - Connection refused (is Paddy running?)
     - Invalid response format (check logs)
  5. **Example Queries** - Sample prompts to try
- **GOTCHA**: Emphasize baseURL should NOT include `/chat/completions`
- **GOTCHA**: Explain that API key is not currently validated but field is required
- **VALIDATE**: Manual review for clarity and completeness

### VALIDATE: Type Checking

- **EXECUTE**: `uv run mypy app/`
- **EXPECT**: Success: no issues found
- **FIX**: Address any type errors before proceeding

### VALIDATE: Linting

- **EXECUTE**: `uv run ruff check .`
- **EXPECT**: All passed or only acceptable warnings
- **FIX**: Run `uv run ruff format .` if needed

### VALIDATE: Unit Tests

- **EXECUTE**: `uv run pytest app/openai_compat/tests/ -v`
- **EXPECT**: All tests pass
- **FIX**: Debug failing tests, update implementation

### VALIDATE: Integration Tests

- **EXECUTE**: `uv run pytest app/ -v -m integration`
- **EXPECT**: All integration tests pass including new OpenAI endpoint tests
- **FIX**: Debug integration failures

### VALIDATE: Manual Streaming Test

- **EXECUTE**: Create test script `test_streaming.py`:
  ```python
  import httpx
  import asyncio

  async def test_stream():
      async with httpx.AsyncClient() as client:
          request = {
              "model": "claude-sonnet-4-0",
              "messages": [{"role": "user", "content": "Count to 3"}],
              "stream": True
          }
          async with client.stream("POST", "http://localhost:8123/v1/chat/completions", json=request, timeout=30.0) as response:
              async for line in response.aiter_lines():
                  if line.startswith("data: "):
                      print(line)

  asyncio.run(test_stream())
  ```
- **EXECUTE**: Start server `uv run uvicorn app.main:app --reload --port 8123` then run test script
- **EXPECT**: See SSE chunks printed, ending with `data: [DONE]`
- **FIX**: Debug streaming issues if chunks malformed

### VALIDATE: CORS Configuration

- **EXECUTE**: Test CORS with curl:
  ```bash
  curl -X OPTIONS http://localhost:8123/v1/chat/completions \
    -H "Origin: app://obsidian.md" \
    -H "Access-Control-Request-Method: POST" \
    -v
  ```
- **EXPECT**: Response includes `Access-Control-Allow-Origin: app://obsidian.md`
- **FIX**: Check middleware.py CORS configuration if headers missing

---

## TESTING STRATEGY

All tests follow pytest patterns established in the codebase with strict type checking and comprehensive coverage.

### Unit Tests

**Scope**: Individual components in isolation

**Coverage Requirements**:
- Models: Field validation, type coercion, edge cases
- Converters: All message formats, content normalization
- Streaming: Chunk building, SSE formatting, state tracking

**Fixtures** (in `app/openai_compat/tests/conftest.py`):
- `sample_openai_request` - Valid ChatCompletionRequest
- `sample_messages` - Various message combinations
- `mock_agent_run` - Mocked agent.iter() responses

### Integration Tests

**Scope**: End-to-end endpoint workflows with real agent

**Coverage Requirements**:
- Streaming mode full flow
- Non-streaming mode full flow
- Message history handling
- Error cases (validation, agent failures)
- CORS header verification

**Test Markers**:
- Use `@pytest.mark.integration` for database/agent tests
- Use `@pytest.mark.asyncio` for async tests

### Edge Cases

**Must Test**:
1. Empty messages array → 400 error
2. Array content format → normalized to string
3. Very long message history → proper conversion
4. Agent execution failure → graceful error response
5. Client disconnect during streaming → cleanup
6. Invalid message roles → validation error
7. Mixed content types in history → proper handling

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
# Type checking (strict mode)
uv run mypy app/

# Pyright (additional type safety)
uv run pyright app/

# Linting
uv run ruff check .

# Format check
uv run ruff format --check .
```

**Expected**: All pass with no errors

### Level 2: Unit Tests

```bash
# All unit tests
uv run pytest app/openai_compat/tests/ -v

# With coverage
uv run pytest app/openai_compat/tests/ --cov=app/openai_compat --cov-report=term-missing

# Specific test file
uv run pytest app/openai_compat/tests/test_models.py -v
```

**Expected**: 100% pass rate, >80% coverage

### Level 3: Integration Tests

```bash
# All tests including integration
uv run pytest app/ -v

# Only integration tests
uv run pytest app/ -v -m integration

# Specific integration test
uv run pytest app/openai_compat/tests/test_routes.py::test_chat_completions_streaming -v
```

**Expected**: All integration tests pass

---

## ACCEPTANCE CRITERIA

- [x] `/v1/chat/completions` endpoint implemented with POST method
- [x] Streaming mode (stream=true) returns SSE formatted chunks
- [x] Non-streaming mode (stream=false) returns complete JSON response
- [x] Message history properly converted from OpenAI to Pydantic AI format
- [x] vault_agent system prompt from app/core/agents/base.py is used (not overridden)
- [x] Content normalization handles both string and array formats
- [x] StreamChunkBuilder correctly formats OpenAI chunks
- [x] First chunk includes role: "assistant", subsequent chunks do not
- [x] Final chunk includes usage statistics and finish_reason: "stop"
- [x] SSE termination signal "data: [DONE]" sent
- [x] CORS configured for app://obsidian.md and capacitor://localhost
- [x] All validation commands pass with zero errors
- [x] Unit test coverage >80% for openai_compat module
- [x] Integration tests verify end-to-end workflows
- [x] Type checking passes (MyPy + Pyright strict mode)
- [x] Logging follows structured event naming pattern
- [x] Error handling includes proper logging with exc_info=True
- [x] User setup guide created in .agents/reference/
- [x] No regressions in existing /agent/chat endpoint
- [x] Code follows VSA patterns (feature slice in app/openai_compat/)

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order
- [ ] Each task validation passed immediately after implementation
- [ ] All validation commands executed successfully (Levels 1-5)
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors (MyPy + Pyright + Ruff)
- [ ] Manual testing with curl confirms streaming and non-streaming work
- [ ] CORS headers verified for Obsidian origins
- [ ] Obsidian Copilot setup guide complete and clear
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability
- [ ] Research reports references validated

---

## NOTES

### Design Decisions

1. **VSA Structure**: Created `app/openai_compat/` feature slice following VSA patterns. This keeps all OpenAI compatibility logic isolated and colocated with tests.

2. **System Prompt Preservation**: The implementation MUST use `vault_agent` from `app/core/agents/base.py` directly. Do NOT create a new agent or override the system prompt. The OpenAI endpoint is just an API adapter.

3. **Message History Handling**: Following research findings, the last user message becomes `user_prompt` parameter to `agent.iter()`, while all previous messages are converted to Pydantic AI format and passed as `message_history`. This matches how Pydantic AI expects conversation context.

4. **Streaming vs Non-Streaming**: Two separate code paths:
   - Streaming: Uses `agent.iter()` with `node.stream()` for text deltas
   - Non-streaming: Uses `agent.run()` for complete response
   Both paths use the same message conversion logic.

5. **Error Handling Philosophy**: Streaming errors still send valid SSE (error chunk + [DONE]) to prevent client hanging. Non-streaming raises HTTPException with proper status codes.

6. **CORS Configuration**: Obsidian uses non-standard origins (`app://`, `capacitor://`) which must be explicitly allowed. The existing CORS middleware in `app/core/middleware.py` should handle this once config is updated.

### Research Report References

All implementation details are based on:

1. `.agents/report/research-report-obsidian-copilot-openai-api.md` - OpenAI format specification, message structure, endpoint paths, content normalization
2. `.agents/report/research-report-streaming-implementation.md` - Pydantic AI agent.iter() patterns, SSE formatting, FastAPI streaming, complete flow

These reports contain the exact specifications extracted from Obsidian Copilot source code and Pydantic AI documentation.
