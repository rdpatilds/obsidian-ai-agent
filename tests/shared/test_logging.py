"""Unit tests for the structured logging module.

Tests verify that:
- Logger instances are properly configured
- Structured logging outputs correct fields
- Context binding works correctly
- Exception logging captures full stack traces
- Different log levels work as expected
"""

import logging
from io import StringIO

import pytest
import structlog

from src.shared.logging import bind_context, clear_context, configure_logging, get_logger


@pytest.mark.unit
class TestLoggingConfiguration:
    """Test suite for logging configuration."""

    def test_configure_logging_sets_up_structlog(self) -> None:
        """Test that configure_logging properly initializes structlog."""
        configure_logging()

        # Verify structlog is configured
        logger = structlog.get_logger()
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "exception")

    def test_get_logger_returns_bound_logger(self) -> None:
        """Test that get_logger returns a properly configured logger."""
        configure_logging()
        logger = get_logger("test_module")

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "bind")

    def test_get_logger_with_no_name(self) -> None:
        """Test that get_logger works without a module name."""
        configure_logging()
        logger = get_logger()

        assert logger is not None


@pytest.mark.unit
class TestStructuredLogging:
    """Test suite for structured logging functionality."""

    def test_logger_info_with_structured_data(self, captured_logs: StringIO) -> None:
        """Test that info logs include structured key-value pairs."""
        logger = get_logger(__name__)

        logger.info("test_event", user_id="123", action="login")

        output = captured_logs.getvalue()
        assert "test_event" in output
        assert "user_id" in output
        assert "123" in output
        assert "action" in output
        assert "login" in output

    def test_logger_error_with_structured_data(self, captured_logs: StringIO) -> None:
        """Test that error logs include structured data."""
        logger = get_logger(__name__)

        logger.error("operation_failed", error_code="E001", reason="timeout")

        output = captured_logs.getvalue()
        assert "operation_failed" in output
        assert "error_code" in output
        assert "E001" in output
        assert "reason" in output
        assert "timeout" in output

    def test_logger_debug_messages(self, captured_logs: StringIO) -> None:
        """Test that debug-level logs work correctly."""
        logger = get_logger(__name__)

        logger.debug("debug_event", detail="verbose information")

        output = captured_logs.getvalue()
        assert "debug_event" in output
        assert "detail" in output

    def test_logger_warning_messages(self, captured_logs: StringIO) -> None:
        """Test that warning-level logs work correctly."""
        logger = get_logger(__name__)

        logger.warning("deprecated_usage", feature="old_api", replacement="new_api")

        output = captured_logs.getvalue()
        assert "deprecated_usage" in output
        assert "feature" in output
        assert "old_api" in output


@pytest.mark.unit
class TestExceptionLogging:
    """Test suite for exception logging with stack traces."""

    def test_logger_exception_captures_traceback(self, captured_logs: StringIO) -> None:
        """Test that exception logging includes full stack trace."""
        logger = get_logger(__name__)

        def _raise_test_error() -> None:
            """Helper to raise test error."""
            msg = "Test error"
            raise ValueError(msg)

        try:
            _raise_test_error()
        except ValueError:
            logger.exception("test_exception", context="error handling test")

        output = captured_logs.getvalue()
        assert "test_exception" in output
        assert "ValueError" in output
        assert "Test error" in output
        assert "Traceback" in output

    def test_logger_exception_with_context(self, captured_logs: StringIO) -> None:
        """Test that exception logs include additional context."""
        logger = get_logger(__name__)

        try:
            value = "not_a_number"
            int(value)
        except ValueError:
            logger.exception(
                "conversion_failed",
                input_value=value,
                expected_type="int",
            )

        output = captured_logs.getvalue()
        assert "conversion_failed" in output
        assert "input_value" in output
        assert "not_a_number" in output
        assert "expected_type" in output
        assert "int" in output


@pytest.mark.unit
class TestContextBinding:
    """Test suite for context variable binding."""

    def test_bind_context_adds_to_all_logs(
        self,
        captured_logs: StringIO,
        clean_contextvars: None,  # noqa: ARG002  # Fixture for side effects
    ) -> None:
        """Test that bound context appears in all subsequent logs."""
        logger = get_logger(__name__)

        # Bind context
        bind_context(request_id="abc-123", user_id="user-456")

        # Log multiple messages
        logger.info("first_message")
        logger.info("second_message")

        output = captured_logs.getvalue()
        # Both messages should include the bound context
        assert output.count("request_id") >= 2
        assert output.count("abc-123") >= 2
        assert output.count("user_id") >= 2
        assert output.count("user-456") >= 2

    def test_clear_context_removes_bindings(
        self,
        captured_logs: StringIO,
        clean_contextvars: None,  # noqa: ARG002  # Fixture for side effects
    ) -> None:
        """Test that clear_context removes all bound variables."""
        logger = get_logger(__name__)

        # Bind context
        bind_context(request_id="abc-123")
        logger.info("with_context")

        # Clear context
        clear_context()
        logger.info("without_context")

        output = captured_logs.getvalue()
        lines = output.split("\n")

        # Find the two log lines
        with_context_line = next(line for line in lines if "with_context" in line)
        without_context_line = next(line for line in lines if "without_context" in line)

        # First should have request_id, second should not
        assert "request_id" in with_context_line
        assert "request_id" not in without_context_line

    def test_context_isolation_between_tests(
        self,
        captured_logs: StringIO,
        clean_contextvars: None,  # noqa: ARG002  # Fixture for side effects
    ) -> None:
        """Test that context doesn't leak between tests."""
        logger = get_logger(__name__)

        # This test should start with clean context (no request_id)
        logger.info("isolated_message")

        output = captured_logs.getvalue()
        assert "isolated_message" in output
        # Should not have request_id from previous test
        assert "abc-123" not in output


@pytest.mark.unit
class TestLogLevels:
    """Test suite for different log levels."""

    def test_multiple_log_levels(self, captured_logs: StringIO) -> None:
        """Test that all log levels work correctly."""
        logger = get_logger(__name__)

        logger.debug("debug_message", level="debug")
        logger.info("info_message", level="info")
        logger.warning("warning_message", level="warning")
        logger.error("error_message", level="error")

        output = captured_logs.getvalue()

        assert "debug_message" in output
        assert "info_message" in output
        assert "warning_message" in output
        assert "error_message" in output

    def test_log_level_filtering(self) -> None:
        """Test that log level filtering works (logs below threshold are filtered)."""
        # Create a logger with INFO level (filters out DEBUG)
        log_buffer = StringIO()
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.dev.ConsoleRenderer(colors=False),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
            logger_factory=structlog.PrintLoggerFactory(file=log_buffer),
            cache_logger_on_first_use=False,
        )

        logger = structlog.get_logger()
        logger.debug("should_not_appear")
        logger.info("should_appear")

        output = log_buffer.getvalue()
        assert "should_not_appear" not in output
        assert "should_appear" in output

        # Cleanup
        structlog.reset_defaults()
