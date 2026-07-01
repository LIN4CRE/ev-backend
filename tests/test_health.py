"""Tests for health and admin configuration endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    """Verify the public health endpoint returns a healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "service" in payload
    assert "environment" in payload


def test_admin_config_requires_key() -> None:
    """Verify the admin endpoint rejects requests without authentication."""
    response = client.get("/api/v1/admin/config")
    assert response.status_code == 401


def test_admin_config_accepts_valid_key() -> None:
    """Verify the admin endpoint returns a redacted summary for valid keys."""
    response = client.get(
        "/api/v1/admin/config",
        headers={"X-Admin-Api-Key": "change-me-in-production!!!"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "openai_configured" in payload
    assert "home_assistant_configured" in payload
    assert "admin_api_key" not in payload
