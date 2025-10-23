"""Integration tests for the FastAPI application with logging.

Tests verify that:
- The full application stack works together
- Logging middleware integrates with endpoints
- Correlation IDs flow through the entire request
- Errors are properly logged at the application level
"""

import re
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.mark.integration
class TestApplicationLogging:
    """Integration tests for application-wide logging."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create a FastAPI test client."""
        return TestClient(app)

    def test_root_endpoint_with_logging(
        self,
        client: TestClient,
        captured_logs: StringIO,
    ) -> None:
        """Test that root endpoint generates proper logs."""
        response = client.get("/")

        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}

        # Check logs
        output = captured_logs.getvalue()
        assert "request_started" in output
        assert "root_endpoint_called" in output
        assert "request_completed" in output
        assert "correlation_id" in output

    def test_health_endpoint_with_logging(
        self,
        client: TestClient,
        captured_logs: StringIO,
    ) -> None:
        """Test that health endpoint generates proper logs."""
        response = client.get("/health")

        assert response.status_code == 200
        response_json = response.json()
        assert response_json["status"] == "healthy"
        assert "components" in response_json
        assert "agent" in response_json["components"]

        output = captured_logs.getvalue()
        assert "request_started" in output
        assert "request_completed" in output

    def test_correlation_id_in_response_headers(self, client: TestClient) -> None:
        """Test that correlation_id is returned in response headers."""
        response = client.get("/")

        assert "x-correlation-id" in response.headers
        correlation_id = response.headers["x-correlation-id"]
        assert len(correlation_id) > 0

    def test_custom_correlation_id_is_preserved(self, client: TestClient) -> None:
        """Test that custom correlation_id from request is preserved."""
        custom_correlation_id = "my-custom-correlation-123"

        response = client.get("/", headers={"x-correlation-id": custom_correlation_id})

        assert response.headers["x-correlation-id"] == custom_correlation_id

    def test_error_endpoint_logs_exception(
        self,
        client: TestClient,
        captured_logs: StringIO,
    ) -> None:
        """Test that error endpoint logs exceptions properly."""
        # The test client raises the exception by default, so we need to catch it
        # In a real scenario, FastAPI would handle it and return a 500 response
        try:
            response = client.get("/test-error", follow_redirects=False)
            # If no exception, check the response
            assert response.status_code == 500
        except ValueError:
            # Exception was raised (expected in test mode)
            pass

        output = captured_logs.getvalue()
        assert "request_started" in output
        assert "test_error_endpoint_called" in output
        assert "request_failed" in output
        assert "ValueError" in output
        assert "This is a test error for logging demonstration" in output

    def test_multiple_requests_have_different_correlation_ids(
        self,
        client: TestClient,
    ) -> None:
        """Test that each request gets a unique correlation_id."""
        response1 = client.get("/")
        response2 = client.get("/")

        correlation_id1 = response1.headers["x-correlation-id"]
        correlation_id2 = response2.headers["x-correlation-id"]

        assert correlation_id1 != correlation_id2

    def test_request_duration_is_logged(
        self,
        client: TestClient,
        captured_logs: StringIO,
    ) -> None:
        """Test that request duration is logged in milliseconds."""
        client.get("/")

        output = captured_logs.getvalue()
        assert "duration_ms" in output

        # Extract duration value (should be a positive number)
        duration_match = re.search(r"duration_ms[=:]?\s*([0-9.]+)", output)
        assert duration_match is not None
        duration = float(duration_match.group(1))
        assert duration > 0


@pytest.mark.integration
@pytest.mark.slow
class TestApplicationLifecycle:
    """Integration tests for application startup and shutdown."""

    def test_application_startup_logs(self, captured_logs: StringIO) -> None:
        """Test that application startup generates logs."""
        # Use the app instance from the module level
        with TestClient(app):
            pass  # Triggers startup and shutdown

        output = captured_logs.getvalue()
        assert "application_starting" in output

    def test_application_shutdown_logs(self, captured_logs: StringIO) -> None:
        """Test that application shutdown generates logs."""
        # Use the app instance from the module level
        with TestClient(app):
            pass  # Triggers startup and shutdown

        output = captured_logs.getvalue()
        assert "application_shutdown" in output
