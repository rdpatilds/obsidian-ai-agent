"""Unit tests for FastAPI middleware.

Tests verify that:
- LoggingMiddleware generates correlation IDs
- Request/response logging works correctly
- Context is properly bound and cleared
- Exceptions are logged with full context
"""

from io import StringIO
from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog
from fastapi import Request, Response

from src.shared.logging import get_logger
from src.shared.middleware import LoggingMiddleware


@pytest.mark.unit
class TestLoggingMiddleware:
    """Test suite for LoggingMiddleware."""

    @pytest.fixture
    def mock_request(self) -> Request:
        """Create a mock FastAPI Request."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }
        return Request(scope)

    @pytest.fixture
    def mock_response(self) -> Response:
        """Create a mock FastAPI Response."""
        return Response(content="test response", status_code=200)

    @pytest.fixture
    def middleware(self) -> LoggingMiddleware:
        """Create a LoggingMiddleware instance."""
        app = MagicMock()
        return LoggingMiddleware(app)

    async def test_middleware_generates_correlation_id(
        self,
        middleware: LoggingMiddleware,
        mock_request: Request,
        mock_response: Response,
        captured_logs: StringIO,
    ) -> None:
        """Test that middleware generates a correlation_id for requests."""
        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(mock_request, call_next)

        # Check that correlation_id was added to response headers
        assert "x-correlation-id" in response.headers
        correlation_id = response.headers["x-correlation-id"]
        assert len(correlation_id) > 0

        # Check that correlation_id appears in logs
        output = captured_logs.getvalue()
        assert correlation_id in output

    async def test_middleware_uses_existing_correlation_id(
        self,
        middleware: LoggingMiddleware,
        mock_response: Response,
        captured_logs: StringIO,
    ) -> None:
        """Test that middleware uses correlation_id from request header if present."""
        # Create request with correlation_id header
        existing_correlation_id = "existing-correlation-123"
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [(b"x-correlation-id", existing_correlation_id.encode())],
            "client": ("127.0.0.1", 8000),
        }
        request = Request(scope)

        call_next = AsyncMock(return_value=mock_response)

        response = await middleware.dispatch(request, call_next)

        # Should use the existing correlation_id
        assert response.headers["x-correlation-id"] == existing_correlation_id

        # Check that existing correlation_id appears in logs
        output = captured_logs.getvalue()
        assert existing_correlation_id in output

    async def test_middleware_logs_request_started(
        self,
        middleware: LoggingMiddleware,
        mock_request: Request,
        mock_response: Response,
        captured_logs: StringIO,
    ) -> None:
        """Test that middleware logs request_started event."""
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        output = captured_logs.getvalue()
        assert "request_started" in output
        assert "GET" in output
        assert "/test" in output

    async def test_middleware_logs_request_completed(
        self,
        middleware: LoggingMiddleware,
        mock_request: Request,
        mock_response: Response,
        captured_logs: StringIO,
    ) -> None:
        """Test that middleware logs request_completed with duration."""
        call_next = AsyncMock(return_value=mock_response)

        await middleware.dispatch(mock_request, call_next)

        output = captured_logs.getvalue()
        assert "request_completed" in output
        assert "status_code" in output
        assert "200" in output
        assert "duration_ms" in output

    async def test_middleware_logs_exceptions(
        self,
        middleware: LoggingMiddleware,
        mock_request: Request,
        captured_logs: StringIO,
    ) -> None:
        """Test that middleware logs exceptions with full context."""
        # Mock call_next to raise an exception
        async def raise_error(request: Request) -> Response:  # noqa: ARG001  # Required by call_next signature
            msg = "Test error"
            raise ValueError(msg)

        call_next = AsyncMock(side_effect=raise_error)

        # Should re-raise the exception
        with pytest.raises(ValueError, match="Test error"):
            await middleware.dispatch(mock_request, call_next)

        output = captured_logs.getvalue()
        assert "request_failed" in output
        assert "ValueError" in output
        assert "Test error" in output
        assert "duration_ms" in output

    async def test_middleware_clears_context_after_request(
        self,
        middleware: LoggingMiddleware,
        mock_request: Request,
        mock_response: Response,
        clean_contextvars: None,  # noqa: ARG002  # Fixture for side effects
    ) -> None:
        """Test that middleware clears context vars after each request."""
        logger = get_logger(__name__)
        call_next = AsyncMock(return_value=mock_response)

        # Create log buffer for this test
        log_buffer = StringIO()

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(colors=False),
            ],
            logger_factory=structlog.PrintLoggerFactory(file=log_buffer),
            cache_logger_on_first_use=False,
        )

        # First request
        await middleware.dispatch(mock_request, call_next)

        # Log after middleware (context should be cleared)
        logger.info("after_request")

        output = log_buffer.getvalue()
        after_line = next(line for line in output.split("\n") if "after_request" in line)

        # correlation_id should not be in the log after middleware
        # (it was cleared by the middleware)
        assert "correlation_id" not in after_line

        # Cleanup
        structlog.reset_defaults()
