"""FastAPI middleware for automatic request logging and correlation tracking."""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.shared.logging import bind_context, clear_context, get_logger


logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that automatically logs all requests and responses.

    Features:
    - Generates correlation_id for each request
    - Logs request start with method, path, client IP
    - Logs response with status code, duration
    - Binds correlation_id to context for all logs in the request
    - Handles exceptions and logs them with full context
    """

    async def dispatch(  # type: ignore[override]  # BaseHTTPMiddleware typing is overly strict
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        """Process the request and add logging."""
        # Generate correlation ID (check header first, then generate)
        correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())

        # Bind correlation_id to context so all logs include it
        bind_context(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        # Log request start
        start_time = time.time()
        logger.info(
            "request_started",
            query_params=dict(request.query_params),
            path_params=request.path_params,
        )

        try:
            # Process the request
            response = await call_next(request)  # type: ignore[misc]  # Starlette typing issue

            # Calculate duration
            duration = time.time() - start_time

            # Log successful response
            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration * 1000, 2),
            )

            # Add correlation_id to response headers
            response.headers["x-correlation-id"] = correlation_id

        except Exception as exc:
            # Calculate duration
            duration = time.time() - start_time

            # Log exception with full context
            logger.exception(
                "request_failed",
                exc_type=type(exc).__name__,
                exc_message=str(exc),
                duration_ms=round(duration * 1000, 2),
            )

            # Re-raise the exception to let FastAPI handle it
            raise

        else:
            return response  # type: ignore[no-any-return]  # Response type is correct but mypy struggles
        finally:
            # Always clear context to prevent leakage between requests
            clear_context()
