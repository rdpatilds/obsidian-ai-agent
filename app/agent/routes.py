"""Test endpoints for agent interaction."""

from fastapi import APIRouter, HTTPException, status

from app.agent.models import ChatRequest, ChatResponse
from app.core.agents import AgentDeps, vault_agent
from app.core.config import get_settings
from app.core.logging import get_logger
from app.shared.vault.vault_manager import VaultManager

logger = get_logger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Test endpoint for agent interaction.

    Args:
        request: User message to send to agent.

    Returns:
        Agent response with usage statistics.

    Raises:
        HTTPException: 500 if agent execution fails.
    """
    logger.info("agent.chat.started", message_length=len(request.message))

    try:
        settings = get_settings()
        vault_manager = VaultManager(settings.obsidian_vault_path)
        result = await vault_agent.run(
            request.message, deps=AgentDeps(vault_manager=vault_manager, settings=settings)
        )

        logger.info(
            "agent.chat.completed",
            response_length=len(result.output),
            total_tokens=result.usage().total_tokens,
        )

        return ChatResponse(
            response=result.output,
            usage={
                "total_tokens": result.usage().total_tokens,
                "request_tokens": result.usage().input_tokens,
                "response_tokens": result.usage().output_tokens,
            },
        )

    except Exception as e:
        logger.error(
            "agent.chat.failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {e!s}",
        ) from e
