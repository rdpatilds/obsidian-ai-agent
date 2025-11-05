"""StreamChunkBuilder and SSE formatting utilities for OpenAI-compatible streaming.

This module provides utilities for building and formatting Server-Sent Events (SSE)
in OpenAI's streaming response format. The chunk structure follows the OpenAI Chat
Completions API streaming specification.

Chunk Sequence:
1. First chunk: Includes role: "assistant" in delta
2. Content chunks: Include content deltas only
3. Final chunk: Empty delta with finish_reason and usage statistics
4. Termination: "data: [DONE]\\n\\n" signal
"""

import json
import time
import uuid
from typing import Any


class StreamChunkBuilder:
    """Builder for OpenAI-compatible streaming response chunks.

    This class maintains state for a streaming response and builds properly
    formatted chunks according to the OpenAI API specification.

    The first chunk must include the role ("assistant"), subsequent chunks
    contain only content deltas, and the final chunk includes usage statistics.
    """

    def __init__(self, model: str) -> None:
        """Initialize the chunk builder.

        Args:
            model: Model name to include in chunks.
        """
        # Generate unique completion ID in OpenAI format: chatcmpl-{29 hex chars}
        self.completion_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        self.created = int(time.time())
        self.model = model
        self.role_chunk_sent = False

    def build_role_chunk(self) -> dict[str, Any]:
        """Build the initial empty chunk with role only (OpenAI SSE spec).

        According to OpenAI's SSE specification, the first chunk MUST include
        the role with empty content. This ensures the client knows the assistant
        is responding before any actual content is streamed.

        Returns:
            First chunk dictionary with role and empty content.

        Example:
            {
                "id": "chatcmpl-...",
                "object": "chat.completion.chunk",
                "created": 1736083200,
                "model": "claude-sonnet-4-0",
                "choices": [{
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None
                }]
            }
        """
        return {
            "id": self.completion_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": ""},
                    "finish_reason": None,
                }
            ],
        }

    def build_content_chunk(self, content: str) -> dict[str, Any]:
        """Build a content chunk with streaming text delta.

        Content chunks include ONLY the content delta, no role.
        The role is sent once in the initial chunk via build_role_chunk().

        Args:
            content: Text content delta to include in the chunk.

        Returns:
            Chunk dictionary ready for JSON serialization.

        Example:
            {
                "id": "chatcmpl-...",
                "object": "chat.completion.chunk",
                "created": 1736083200,
                "model": "claude-sonnet-4-0",
                "choices": [{
                    "index": 0,
                    "delta": {"content": "Hello"},
                    "finish_reason": None
                }]
            }
        """
        return {
            "id": self.completion_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": content},
                    "finish_reason": None,
                }
            ],
        }

    def build_final_chunk(self, prompt_tokens: int, completion_tokens: int) -> dict[str, Any]:
        """Build the final chunk with usage statistics and finish reason.

        The final chunk has an empty delta, finish_reason: "stop", and
        includes token usage statistics.

        Args:
            prompt_tokens: Number of tokens in the prompt.
            completion_tokens: Number of tokens in the completion.

        Returns:
            Final chunk dictionary with usage statistics.

        Example:
            {
                "id": "chatcmpl-...",
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": 100,
                    "total_tokens": 115
                }
            }
        """
        return {
            "id": self.completion_id,
            "object": "chat.completion.chunk",
            "created": self.created,
            "model": self.model,
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    @staticmethod
    def format_sse(chunk: dict[str, Any]) -> str:
        """Format a chunk as Server-Sent Event (SSE).

        SSE format requires the data to be prefixed with "data: " and
        terminated with double newline.

        Args:
            chunk: Chunk dictionary to format.

        Returns:
            SSE-formatted string.

        Example:
            >>> chunk = {"id": "chatcmpl-123", "choices": [...]}
            >>> StreamChunkBuilder.format_sse(chunk)
            'data: {"id":"chatcmpl-123","choices":[...]}\n\n'
        """
        return f"data: {json.dumps(chunk)}\n\n"
