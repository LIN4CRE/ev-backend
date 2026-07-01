"""Tests for request logging middleware behavior."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_request_logging_middleware_sets_request_id_header() -> None:
    """Verify responses include a request correlation ID."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id")


def test_request_logging_middleware_preserves_supplied_request_id() -> None:
    """Verify a caller-supplied request ID is echoed in the response."""
    response = client.get("/api/v1/health", headers={"X-Request-Id": "req-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id") == "req-123"
