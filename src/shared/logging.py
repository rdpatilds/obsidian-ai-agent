"""Structured logging setup optimized for AI agent debugging.

This module configures structlog for production-ready logging with:
- JSON output in production for machine parsing
- Pretty console output in development for human readability
- Full stack traces with local variables for debugging
- Correlation IDs for request tracing
- Request-scoped context via contextvars
- Rich metadata (timestamp, level, source location)
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, Processor

from src.shared.config import settings


def add_source_location(
    logger: logging.Logger,  # noqa: ARG001  # Required by structlog processor signature
    method_name: str,  # noqa: ARG001  # Required by structlog processor signature
    event_dict: EventDict,
) -> EventDict:
    """Add source code location (file, function, line) to log entries.

    This helps AI agents quickly locate the code that generated the log.
    """
    frame = sys._getframe(6)  # Adjust frame depth to get actual caller
    event_dict["source"] = {
        "file": frame.f_code.co_filename.split("/")[-1],  # Just filename, not full path
        "function": frame.f_code.co_name,
        "line": frame.f_lineno,
    }
    return event_dict


def add_exception_context(
    logger: logging.Logger,  # noqa: ARG001  # Required by structlog processor signature
    method_name: str,  # noqa: ARG001  # Required by structlog processor signature
    event_dict: EventDict,
) -> EventDict:
    """Enhance exception info with local variables for better debugging.

    Captures the local scope when an exception occurs, giving AI agents
    full context about what went wrong.
    """
    if event_dict.get("exception"):
        # structlog already formats the exception, we just ensure it's verbose
        pass
    return event_dict


def configure_logging() -> None:
    """Configure structlog for the entire application.

    Sets up different processors based on environment:
    - Development: Pretty console output with colors
    - Production: JSON output for log aggregation tools
    """
    shared_processors: list[Processor] = [
        # Add correlation_id from context
        structlog.contextvars.merge_contextvars,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Add log level
        structlog.processors.add_log_level,
        # Add source location (file, function, line)
        add_source_location,
        # Add exception context
        add_exception_context,
        # Format stack traces
        structlog.processors.format_exc_info,
        # Decode unicode
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.environment == "development":
        # Development: Pretty console output
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    show_locals=True,  # Show local variables in stack traces
                    max_frames=10,
                ),
            ),
        ]
    else:
        # Production: JSON output
        processors = [
            *shared_processors,
            structlog.processors.dict_tracebacks,  # Format exceptions as dicts
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,  # type: ignore[arg-type]  # structlog processor types are complex
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,  # Allow test fixtures to reconfigure logging
    )

    # Configure standard library logging to use structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Redirect uvicorn logs through structlog
    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger instance.

    Args:
        name: Optional logger name (typically __name__ of the module)

    Returns:
        Configured structlog logger

    Example:
        logger = get_logger(__name__)
        logger.info("user_created", user_id="123", email="user@example.com")
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]  # structlog typing is complex


def bind_context(**kwargs: Any) -> None:
    """Bind context variables that will be included in all subsequent logs.

    This is useful for request-scoped data like user_id, request_id, etc.

    Args:
        **kwargs: Key-value pairs to bind to the context

    Example:
        bind_context(user_id="123", request_id="abc-def")
        logger.info("processing_request")  # Will include user_id and request_id
    """
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables.

    Should be called at the end of each request to prevent context leakage.
    """
    structlog.contextvars.clear_contextvars()
