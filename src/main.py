"""FastAPI application with structured logging."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.openai.endpoints import router as openai_router
from src.shared.config import get_settings, log_exported_api_keys
from src.shared.logging import configure_logging, get_logger
from src.shared.middleware import LoggingMiddleware


# Configure logging before anything else
configure_logging()
logger = get_logger(__name__)

# Log exported API keys with proper formatting (after structlog is configured)
log_exported_api_keys()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001  # Required by FastAPI lifespan signature
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    settings = get_settings()
    logger.info("application_starting", environment=settings.environment)

    # Log CORS configuration
    if settings.cors_enabled:
        logger.info("cors_middleware_enabled", origins=settings.cors_origins_list)

    # Initialize agent (triggers tool registration)
    from src.agent.agent import get_agent  # noqa: PLC0415

    _ = get_agent(settings)  # Initialize but don't store (singleton pattern)
    logger.info("agent_initialized", model=settings.model_name)

    yield
    # Shutdown
    logger.info("application_shutdown")


app = FastAPI(lifespan=lifespan)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Add CORS middleware if enabled (required for Obsidian Copilot)
settings = get_settings()
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

# Mount OpenAI router
app.include_router(openai_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    logger.info("root_endpoint_called", extra_context="This is a demo log")
    return {"message": "Hello World"}


@app.get("/health")
async def health() -> dict[str, str | dict[str, bool]]:
    """Health check endpoint with agent status."""
    from src.agent.agent import _agent  # noqa: PLC0415

    logger.debug("health_check_called")

    return {
        "status": "healthy",
        "components": {
            "agent": _agent is not None,
        },
    }


@app.get("/test-error")
async def test_error() -> dict[str, str]:
    """Test endpoint that raises an error to demonstrate exception logging."""
    logger.info("test_error_endpoint_called", about_to_raise="ValueError")
    msg = "This is a test error for logging demonstration"
    raise ValueError(msg)
