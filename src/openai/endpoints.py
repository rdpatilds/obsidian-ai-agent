"""OpenAI-compatible API endpoints.

This module provides FastAPI route handlers for:
- POST /v1/chat/completions (streaming and non-streaming)
- API key authentication
- OpenAI-compatible error responses
"""

import json
import time
import uuid
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse

from src.agent.schemas import AgentDependencies, AgentRequest
from src.agent.service import run_agent, stream_agent
from src.openai.converter import convert_openai_to_pydantic, convert_pydantic_to_openai
from src.openai.schemas import (
    ChatCompletionChunk,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChunkChoice,
    DeltaMessage,
)
from src.shared.config import Settings, get_settings
from src.shared.logging import bind_context, get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/v1", tags=["openai"])


async def verify_api_key(
    authorization: str | None = Header(None),
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> None:
    """Verify API key from Authorization header.

    Args:
        authorization: Authorization header value (Bearer token).
        settings: Application settings.

    Raises:
        HTTPException: If API key is missing or invalid.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Missing Authorization header",
                    "type": "invalid_request_error",
                }
            },
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid Authorization format. Use 'Bearer <key>'",
                    "type": "invalid_request_error",
                }
            },
        )

    api_key = authorization.replace("Bearer ", "")
    if api_key != settings.openai_compatible_api_key:
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Invalid API key", "type": "invalid_api_key"}},
        )


@router.post("/chat/completions", response_model=None)
async def chat_completions(
    request: ChatCompletionRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
    _: None = Depends(verify_api_key),
) -> ChatCompletionResponse | StreamingResponse:
    """OpenAI-compatible chat completions endpoint.

    Args:
        request: Chat completion request in OpenAI format.
        settings: Application settings.

    Returns:
        Chat completion response (streaming or non-streaming).

    Raises:
        HTTPException: On authentication or processing errors.
    """
    request_id = str(uuid.uuid4())
    bind_context(correlation_id=request_id)

    logger.info(
        "openai_request_received",
        request_id=request_id,
        model=request.model,
        message_count=len(request.messages),
        stream=request.stream,
    )

    try:
        # Convert OpenAI format to Pydantic AI format
        user_prompt, conversation_history = convert_openai_to_pydantic(request.messages)

        # Create agent request
        agent_request = AgentRequest(
            prompt=user_prompt,
            message_history=conversation_history,
            request_id=request_id,
        )

        # Build model settings from request parameters
        # Note: Anthropic models don't allow both temperature and top_p to be set
        # If both are provided, prefer temperature (more commonly used)
        model_settings = {}

        # Determine if we're using an Anthropic model
        is_anthropic = request.model.startswith("anthropic:")

        if request.temperature is not None:
            model_settings["temperature"] = request.temperature

        # Only add top_p if temperature is not set (for Anthropic compatibility)
        # or if not using Anthropic
        if request.top_p is not None and (not is_anthropic or "temperature" not in model_settings):
            model_settings["top_p"] = request.top_p

        if request.max_tokens is not None:
            model_settings["max_tokens"] = request.max_tokens

        # Create dependencies
        async with httpx.AsyncClient() as http_client:
            deps = AgentDependencies(
                http_client=http_client,
                openai_api_key=settings.openai_api_key,
                vault_path=settings.obsidian_vault_path,
            )

            if request.stream:
                # Streaming response
                async def stream_response() -> AsyncIterator[str]:
                    try:
                        # Send initial chunk with role
                        initial_chunk = ChatCompletionChunk(
                            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
                            created=int(time.time()),
                            model=request.model,
                            choices=[
                                ChunkChoice(
                                    index=0,
                                    delta=DeltaMessage(role="assistant", content=""),
                                    finish_reason=None,
                                )
                            ],
                        )
                        yield f"data: {initial_chunk.model_dump_json()}\n\n"

                        # Stream content with model settings
                        async for chunk in stream_agent(agent_request, deps, model_settings):
                            chunk_data = ChatCompletionChunk(
                                id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
                                created=int(time.time()),
                                model=request.model,
                                choices=[
                                    ChunkChoice(
                                        index=0,
                                        delta=DeltaMessage(content=chunk),
                                        finish_reason=None,
                                    )
                                ],
                            )
                            yield f"data: {chunk_data.model_dump_json()}\n\n"

                        # Send final chunk
                        final_chunk = ChatCompletionChunk(
                            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
                            created=int(time.time()),
                            model=request.model,
                            choices=[
                                ChunkChoice(
                                    index=0,
                                    delta=DeltaMessage(),
                                    finish_reason="stop",
                                )
                            ],
                        )
                        yield f"data: {final_chunk.model_dump_json()}\n\n"
                        yield "data: [DONE]\n\n"

                        logger.info("openai_stream_completed", request_id=request_id)
                    except Exception as e:
                        logger.exception("openai_stream_failed", request_id=request_id)
                        error_data = {
                            "error": {"message": str(e), "type": "server_error"}
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"

                return StreamingResponse(
                    stream_response(),
                    media_type="text/event-stream",
                    headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
                )
            # Non-streaming response
            agent_response = await run_agent(agent_request, deps, model_settings)
            openai_response = convert_pydantic_to_openai(
                agent_response, request.model
            )

            logger.info("openai_request_completed", request_id=request_id)
            return openai_response

    except ValueError as e:
        logger.exception("openai_request_validation_failed", request_id=request_id)
        raise HTTPException(
            status_code=400,
            detail={"error": {"message": str(e), "type": "invalid_request_error"}},
        ) from e
    except Exception as e:
        logger.exception("openai_request_failed", request_id=request_id)
        raise HTTPException(
            status_code=500,
            detail={"error": {"message": "Internal server error", "type": "server_error"}},
        ) from e
