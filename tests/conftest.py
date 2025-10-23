"""Shared pytest fixtures and configuration.

This conftest.py is at the root of the tests directory and provides
fixtures available to all tests.
"""

import logging
from collections.abc import Generator
from io import StringIO
from pathlib import Path

import httpx
import pytest
import structlog

from src.agent.schemas import AgentDependencies
from src.shared.config import Settings


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Provide test settings for the entire test session.

    This fixture creates a Settings instance with test-specific values
    that override production settings.
    """
    return Settings(
        environment="development",
        host="127.0.0.1",
        port=8999,  # Use different port for tests
        openai_compatible_api_key="test-api-key-12345",
    )


@pytest.fixture
def captured_logs() -> Generator[StringIO, None, None]:
    """Capture log output for assertions in tests.

    This fixture captures all log output to a StringIO buffer
    which can be inspected in tests to verify logging behavior.

    Usage:
        def test_logging(captured_logs):
            logger.info("test_message", key="value")
            output = captured_logs.getvalue()
            assert "test_message" in output
            assert "key" in output
    """
    # Reset any cached loggers from previous tests or app imports
    structlog.reset_defaults()

    # Create a string buffer to capture logs
    log_buffer = StringIO()

    # Configure structlog to write to the buffer
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=log_buffer),
        cache_logger_on_first_use=False,  # Important for tests
    )

    yield log_buffer

    # Cleanup: reset structlog configuration
    structlog.reset_defaults()


@pytest.fixture
def clean_contextvars() -> Generator[None, None, None]:
    """Clean contextvars before and after each test.

    This ensures that context from one test doesn't leak into another.
    """
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


@pytest.fixture
def temp_vault(tmp_path: Path) -> Path:
    """Create a temporary vault directory for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture.

    Returns:
        Path to the temporary vault directory.
    """
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()
    return vault_path


@pytest.fixture
def sample_notes(temp_vault: Path) -> dict[str, Path]:
    """Create sample notes in the temporary vault for testing.

    Args:
        temp_vault: Temporary vault directory fixture.

    Returns:
        Dictionary mapping note names to their file paths.
    """
    notes: dict[str, Path] = {}

    # Simple note without frontmatter
    simple_note = temp_vault / "test.md"
    simple_note.write_text("# Test Note\n\nThis is a simple test note without frontmatter.\n")
    notes["simple"] = simple_note

    # Note with frontmatter
    with_frontmatter = temp_vault / "with_frontmatter.md"
    with_frontmatter.write_text(
        "---\n"
        "title: Note with Frontmatter\n"
        "tags:\n"
        "  - test\n"
        "  - python\n"
        "created: 2025-01-01\n"
        "---\n"
        "\n"
        "# Note with Frontmatter\n"
        "\n"
        "This note has YAML frontmatter metadata.\n"
    )
    notes["with_frontmatter"] = with_frontmatter

    # Note in subdirectory
    folder = temp_vault / "folder"
    folder.mkdir()
    nested_note = folder / "nested.md"
    nested_note.write_text("# Nested Note\n\nThis note is in a subdirectory.\n")
    notes["nested"] = nested_note

    return notes


@pytest.fixture
async def vault_dependencies(temp_vault: Path) -> AgentDependencies:
    """Create AgentDependencies with temporary vault for testing.

    Args:
        temp_vault: Temporary vault directory fixture.

    Returns:
        AgentDependencies configured for testing.
    """
    async with httpx.AsyncClient() as client:
        return AgentDependencies(
            http_client=client,
            openai_api_key="test-api-key",
            vault_path=str(temp_vault),
        )
